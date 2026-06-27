import logging
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from app.core.llm import client
from app.tools.web_search import search_web
from app.tools.kb_search import search_knowledge_base

logger = logging.getLogger(__name__)


# 1. State Definition
class AgentState(TypedDict):
    query: str
    plan: str
    research_notes: str
    final_report: str
    steps: List[str]


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


# 5. Graph Orchestration
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("planner", planner_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)

# Define Edges
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

# Compile Graph
compiled_graph = workflow.compile()
