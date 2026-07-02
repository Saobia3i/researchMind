import logging
import asyncio
import re
from urllib.parse import urlparse
from typing import TypedDict, List, NotRequired
from langgraph.graph import StateGraph, START, END
from app.core.llm import client
from app.tools.web_search import search_web
from app.tools.kb_search import search_knowledge_base

logger = logging.getLogger(__name__)

GRADING_MODEL = "llama-3.1-8b-instant"
MAX_GRADING_CONCURRENCY = 8


# 1. State Definition
class EvidenceChunk(TypedDict):
    sub_topic: str
    source_type: str
    title: str
    text: str
    url: str
    source_id: str
    quality: str
    quality_score: int


class EvidenceAudit(TypedDict):
    sub_topic: str
    retrieved_chunks: int
    kept_chunks: int
    evidence_sufficient: bool
    evidence_status: str


class AgentState(TypedDict):
    query: str
    plan: str
    research_notes: str
    final_report: str
    steps: List[str]
    evidence_chunks: NotRequired[List[EvidenceChunk]]
    filtered_evidence: NotRequired[List[EvidenceChunk]]
    evidence_audit: NotRequired[List[EvidenceAudit]]


def _extract_topics(plan: str, fallback_query: str) -> list[str]:
    topics = [
        re.sub(r"^\s*(?:[-*]|\d+[.)]?)\s*", "", line).strip()
        for line in plan.split("\n")
        if line.strip() and not line.strip().lower().startswith("plan:")
    ][:3]
    return topics or [fallback_query]


def _source_quality(url: str, title: str) -> tuple[str, int]:
    combined = f"{url} {title}".lower()
    domain = urlparse(url).netloc.lower()

    official_markers = (
        ".gov",
        ".edu",
        ".org",
        "docs.",
        "developer.",
        "learn.",
        "standards.",
        "ietf.org",
        "w3.org",
        "iso.org",
        "github.com",
    )
    low_quality_markers = (
        "best ",
        "top ",
        "buyer",
        "buyers",
        "alternative",
        "alternatives",
        "listicle",
        "sponsored",
        "pricing",
        "comparison",
    )

    if any(marker in domain or marker in combined for marker in official_markers):
        return "primary_or_official", 2
    if any(marker in combined for marker in low_quality_markers):
        return "marketing_or_listicle", 0
    return "general", 1


def _parse_web_results(sub_topic: str, web_results: str) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    pattern = re.compile(
        r"\[(?P<idx>\d+)\]\s+Title:\s*(?P<title>.*?)\n\s*Snippet:\s*(?P<snippet>.*?)\n\s*URL:\s*(?P<url>\S+)",
        re.DOTALL,
    )
    for match in pattern.finditer(web_results):
        title = match.group("title").strip()
        snippet = match.group("snippet").strip()
        url = match.group("url").strip()
        quality, score = _source_quality(url, title)
        chunks.append(
            {
                "sub_topic": sub_topic,
                "source_type": "web",
                "title": title,
                "text": snippet,
                "url": url,
                "source_id": f"web:{match.group('idx')}",
                "quality": quality,
                "quality_score": score,
            }
        )
    return chunks


def _parse_kb_results(sub_topic: str, kb_results: str) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    pattern = re.compile(
        r"Result \[(?P<idx>\d+)\] \(Document: (?P<doc>.*?), Similarity: (?P<score>.*?)\):\n(?P<text>.*?)(?=\n\nResult \[\d+\]|\Z)",
        re.DOTALL,
    )
    for match in pattern.finditer(kb_results):
        doc_id = match.group("doc").strip()
        quality, score = _source_quality("", doc_id)
        chunks.append(
            {
                "sub_topic": sub_topic,
                "source_type": "knowledge_base",
                "title": doc_id,
                "text": match.group("text").strip(),
                "url": "",
                "source_id": f"kb:{doc_id}:{match.group('idx')}",
                "quality": quality,
                "quality_score": score,
            }
        )
    return chunks


def _fallback_relevance_grade(sub_topic: str, text: str) -> bool:
    topic_terms = {
        term
        for term in re.findall(r"[a-zA-Z0-9]{4,}", sub_topic.lower())
        if term not in {"about", "with", "from", "that", "this", "into", "using"}
    }
    text_terms = set(re.findall(r"[a-zA-Z0-9]{4,}", text.lower()))
    return bool(topic_terms & text_terms)


def _grade_single_evidence(sub_topic: str, chunk_text: str) -> bool:
    if client is None:
        logger.warning("[Evidence Grader] GROQ_API_KEY is not configured; using lexical fallback.")
        return _fallback_relevance_grade(sub_topic, chunk_text)

    prompt = f"""
Sub-topic: {sub_topic}
Evidence excerpt: {chunk_text[:2500]}

Does this evidence excerpt directly support or provide information relevant to the sub-topic?
Answer with ONLY one word: "relevant" or "irrelevant".
"""
    try:
        response = client.chat.completions.create(
            model=GRADING_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=4,
        )
        verdict = response.choices[0].message.content.strip().lower()
        return verdict.startswith("relevant")
    except Exception as e:
        logger.error(f"Evidence grading failed; using lexical fallback. Error: {e}")
        return _fallback_relevance_grade(sub_topic, chunk_text)


async def _grade_evidence_concurrently(chunks: list[EvidenceChunk]) -> list[bool]:
    semaphore = asyncio.Semaphore(MAX_GRADING_CONCURRENCY)

    async def grade(chunk: EvidenceChunk) -> bool:
        async with semaphore:
            return await asyncio.to_thread(
                _grade_single_evidence,
                chunk["sub_topic"],
                chunk["text"],
            )

    return await asyncio.gather(*(grade(chunk) for chunk in chunks))


def _format_filtered_notes(
    topics: list[str],
    filtered_chunks: list[EvidenceChunk],
    evidence_audit: list[EvidenceAudit],
) -> str:
    notes: list[str] = []
    chunks_by_topic = {
        topic: [chunk for chunk in filtered_chunks if chunk["sub_topic"] == topic]
        for topic in topics
    }
    audit_by_topic = {audit["sub_topic"]: audit for audit in evidence_audit}

    for topic in topics:
        audit = audit_by_topic[topic]
        notes.append(f"### Findings for: {topic}")
        notes.append(
            f"Evidence status: {audit['evidence_status']} "
            f"({audit['kept_chunks']} of {audit['retrieved_chunks']} retrieved chunks kept)."
        )

        if not audit["evidence_sufficient"]:
            notes.append("Insufficient relevant evidence found for this sub-topic.")
            continue

        for idx, chunk in enumerate(chunks_by_topic[topic], start=1):
            source = chunk["title"]
            if chunk["url"]:
                source = f"[{source}]({chunk['url']})"
            notes.append(
                f"{idx}. Source: {source}\n"
                f"   Source type: {chunk['source_type']}; quality: {chunk['quality']}\n"
                f"   Evidence: {chunk['text']}"
            )

    return "\n\n---\n\n".join(notes)


# 2. Planner Node
def planner_node(state: AgentState) -> dict:
    query = state["query"]
    logger.info(f"[Planner] Creating research plan for query: '{query}'")

    prompt = f"""
You are the Lead Planner of a multi-agent AI research team.
Your task is to take the user's research query and draft a structured research plan.
This plan must outline 2 to 3 specific sub-topics or search queries that need to be investigated to thoroughly answer the question.

User Query: "{query}"

Output the sub-topics as a clean, bulleted list. Keep each sub-topic descriptive but concise. Do not add conversational intro/outro text.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        plan_content = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Planner node failed: {e}")
        plan_content = f"1. Research general details about: {query}\n2. Search relevant applications and developments."

    logger.info(f"[Planner] Generated Plan:\n{plan_content}")

    return {
        "plan": plan_content,
        "steps": state.get("steps", []) + ["planner"],
    }


# 3. Researcher Node
def researcher_node(state: AgentState) -> dict:
    query = state["query"]
    plan = state["plan"]
    logger.info("[Researcher] Gathering information based on the plan...")

    # Extract bullet points/lines from the plan to act as research topics
    topics = [
        line.strip("-*•123456789. ")
        for line in plan.split("\n")
        if line.strip() and not line.strip().lower().startswith("plan:")
    ][:3]  # Limit to top 3 topics to control token usage and speed

    if not topics:
        topics = [query]

    compiled_notes = []

    for i, topic in enumerate(topics):
        logger.info(f"[Researcher] Researching topic {i+1}/{len(topics)}: '{topic}'")

        # 1. Run Web Search
        web_results = search_web(topic, max_results=3)

        # 2. Run KB Search (Pinecone RAG)
        kb_results = search_knowledge_base(topic, top_k=2)

        # 3. Use LLM to summarize findings for this specific topic
        summary_prompt = f"""
You are the Lead Researcher of a multi-agent AI research team.
Your task is to analyze the raw search data (web and knowledge base) for the sub-topic below, and synthesize a set of detailed, well-referenced research notes.

Sub-Topic: "{topic}"

Raw Web Search Results:
{web_results}

Raw Knowledge Base Search Results:
{kb_results}

Synthesize these findings into a detailed research notes block. Include any relevant facts, dates, figures, and specifically retain any URLs from the sources so the writer can reference them.
"""
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
            )
            topic_summary = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Researcher failed summarizing topic '{topic}': {e}")
            topic_summary = f"Topic: {topic}\nWeb findings: {web_results[:300]}...\nKB findings: {kb_results[:300]}..."

        compiled_notes.append(f"### Findings for: {topic}\n\n{topic_summary}")

    research_notes = "\n\n---\n\n".join(compiled_notes)
    logger.info(f"[Researcher] Completed notes compilation ({len(research_notes)} characters).")

    return {
        "research_notes": research_notes,
        "steps": state.get("steps", []) + ["researcher"],
    }


# 4. Writer Node
def writer_node(state: AgentState) -> dict:
    query = state["query"]
    plan = state["plan"]
    notes = state["research_notes"]
    logger.info("[Writer] Synthesizing research notes into final report...")

    write_prompt = f"""
You are the Lead Writer of a multi-agent AI research team.
Your task is to synthesize the provided research plan and compiled research notes into a detailed, comprehensive, and cohesive final report in Markdown format.

Original User Query: "{query}"

Research Plan:
{plan}

Compiled Research Notes:
{notes}

Structure your final report professionally:
- **Title**: A compelling, descriptive title.
- **Introduction**: Provide background context on the research query.
- **Detailed Findings**: Break down findings logically (use sections, headers, and bullet points). Make sure to include and embed the URLs provided in the research notes as inline markdown links (e.g., [Source Name](url)) to support your facts.
- **Conclusion**: Synthesize a comprehensive summary of the findings.

Write in a formal, informative, and academic tone. Output ONLY the final markdown report. Do not add intro comments like "Here is the report...".
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": write_prompt}],
            temperature=0.3,
        )
        report_content = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Writer node failed: {e}")
        report_content = f"# Research Report on: {query}\n\nFailed to generate report due to error: {e}"

    logger.info(f"[Writer] Final report generated successfully.")

    return {
        "final_report": report_content,
        "steps": state.get("steps", []) + ["writer"],
    }


# Grounded Team Research Nodes
def grounded_researcher_node(state: AgentState) -> dict:
    query = state["query"]
    plan = state["plan"]
    topics = _extract_topics(plan, query)
    evidence_chunks: list[EvidenceChunk] = []
    logger.info("[Grounded Researcher] Retrieving raw evidence for relevance grading...")

    for i, topic in enumerate(topics):
        logger.info(
            "[Grounded Researcher] Researching topic %s/%s: '%s'",
            i + 1,
            len(topics),
            topic,
        )
        web_results = search_web(topic, max_results=3)
        kb_results = search_knowledge_base(topic, top_k=2)
        evidence_chunks.extend(_parse_web_results(topic, web_results))
        evidence_chunks.extend(_parse_kb_results(topic, kb_results))

    logger.info(
        "[Grounded Researcher] Retrieved %s raw evidence chunks.",
        len(evidence_chunks),
    )
    return {
        "evidence_chunks": evidence_chunks,
        "steps": state.get("steps", []) + ["researcher"],
    }


def grade_evidence_node(state: AgentState) -> dict:
    query = state["query"]
    plan = state["plan"]
    topics = _extract_topics(plan, query)
    evidence_chunks = state.get("evidence_chunks", [])
    logger.info("[Evidence Grader] Grading %s evidence chunks...", len(evidence_chunks))

    relevance_results = (
        asyncio.run(_grade_evidence_concurrently(evidence_chunks))
        if evidence_chunks
        else []
    )
    filtered_evidence = [
        chunk
        for chunk, is_relevant in zip(evidence_chunks, relevance_results)
        if is_relevant
    ]
    filtered_evidence.sort(
        key=lambda chunk: (
            chunk["sub_topic"],
            -chunk["quality_score"],
            chunk["source_type"],
            chunk["title"],
        )
    )

    evidence_audit: list[EvidenceAudit] = []
    for topic in topics:
        retrieved_count = sum(1 for chunk in evidence_chunks if chunk["sub_topic"] == topic)
        kept_count = sum(1 for chunk in filtered_evidence if chunk["sub_topic"] == topic)
        evidence_audit.append(
            {
                "sub_topic": topic,
                "retrieved_chunks": retrieved_count,
                "kept_chunks": kept_count,
                "evidence_sufficient": kept_count > 0,
                "evidence_status": (
                    "relevant_evidence_found"
                    if kept_count > 0
                    else "no_relevant_evidence_found"
                ),
            }
        )

    research_notes = _format_filtered_notes(topics, filtered_evidence, evidence_audit)
    logger.info(
        "[Evidence Grader] Kept %s of %s chunks after relevance filtering.",
        len(filtered_evidence),
        len(evidence_chunks),
    )
    return {
        "filtered_evidence": filtered_evidence,
        "evidence_audit": evidence_audit,
        "research_notes": research_notes,
        "steps": state.get("steps", []) + ["grade_evidence"],
    }


def grounded_writer_node(state: AgentState) -> dict:
    query = state["query"]
    plan = state["plan"]
    notes = state["research_notes"]
    evidence_audit = state.get("evidence_audit", [])
    logger.info("[Grounded Writer] Synthesizing filtered evidence into final report...")

    write_prompt = f"""
You are the Lead Writer of a multi-agent AI research team.
Your task is to synthesize the provided research plan and compiled research notes into a detailed, cohesive final report in Markdown format.

Grounding rules:
- You must only make claims that are directly supported by the evidence provided below.
- Do not introduce tools, technologies, methods, sources, examples, future directions, or recommendations that are not present in the filtered evidence.
- If the evidence for a sub-topic is insufficient, explicitly state that insufficient relevant evidence was found for that sub-topic instead of writing filler prose.
- The conclusion must only summarize claims already supported in the body; do not add new claims, citations, technologies, or recommendations there.
- Use only URLs and source names that appear in the compiled research notes.

Original User Query: "{query}"

Research Plan:
{plan}

Evidence Audit:
{evidence_audit}

Compiled Research Notes:
{notes}

Structure your final report professionally:
- **Title**: A compelling, descriptive title.
- **Introduction**: Provide concise background context on the research query.
- **Detailed Findings**: Break down findings by sub-topic. Include URLs from the research notes as inline markdown links to support facts.
- **Conclusion**: Summarize only evidence-backed findings from the body. If evidence was insufficient for any section, mention that limitation.

Write in a formal, informative, and academic tone. Output ONLY the final markdown report. Do not add intro comments like "Here is the report...".
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": write_prompt}],
            temperature=0.1,
        )
        report_content = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Grounded writer node failed: {e}")
        report_content = f"# Research Report on: {query}\n\nFailed to generate report due to error: {e}"

    logger.info("[Grounded Writer] Final report generated successfully.")
    return {
        "final_report": report_content,
        "steps": state.get("steps", []) + ["writer"],
    }


# 5. Graph Orchestration
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("planner", planner_node)
workflow.add_node("researcher", grounded_researcher_node)
workflow.add_node("grade_evidence", grade_evidence_node)
workflow.add_node("writer", grounded_writer_node)

# Define Edges
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "researcher")
workflow.add_edge("researcher", "grade_evidence")
workflow.add_edge("grade_evidence", "writer")
workflow.add_edge("writer", END)

# Compile Graph
compiled_graph = workflow.compile()
