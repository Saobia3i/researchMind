import json
import re
from typing import TypedDict

from app.core.config import settings
from app.core.model_providers import CostBudget, call_model
from app.core.token_tracker import token_tracker
from app.tools.kb_search import search_knowledge_base
from app.tools.web_search import search_web


class ConsensusResult(TypedDict):
    query: str
    mode: str
    final_answer: str
    model_opinions: list[dict]
    claim_checks: list[dict]
    disagreement_map: list[dict]
    evidence_graph: dict
    cost_report: dict
    skipped_providers: list[dict]
    reliability_notes: list[str]


def run_consensus_research(
    query: str,
    *,
    session_id: str | None = None,
    budget_usd: float | None = None,
) -> ConsensusResult:
    """
    Runs a cost-aware multi-model research workflow.

    The workflow intentionally separates model opinions from evidence checks:
    1. Gather web + KB evidence.
    2. Ask available models for independent analysis.
    3. Extract important claims.
    4. Ask a verifier to score claim support against evidence and model opinions.
    5. Synthesize a final answer with agreement/disagreement notes.
    """
    budget = CostBudget(budget_usd if budget_usd is not None else settings.default_budget_usd)

    web_evidence = search_web(query, max_results=5)
    kb_evidence = search_knowledge_base(query, top_k=4)
    evidence_bundle = f"Web evidence:\n{web_evidence}\n\nKnowledge-base evidence:\n{kb_evidence}"
    reliability_notes = _evidence_reliability_notes(web_evidence, kb_evidence)

    model_opinions = _collect_model_opinions(query, evidence_bundle, budget)
    claim_candidates = _extract_claims(model_opinions, query)
    claim_checks = _verify_claims(query, evidence_bundle, model_opinions, claim_candidates, budget)
    disagreement_map = _build_disagreement_map(model_opinions, claim_checks)
    final_answer = _synthesize_final_answer(
        query,
        evidence_bundle,
        model_opinions,
        claim_checks,
        disagreement_map,
        budget,
    )

    for event in budget.events:
        if not event.get("skipped"):
            token_tracker.record(
                session_id=session_id,
                prompt_tokens=event.get("prompt_tokens", 0),
                completion_tokens=event.get("completion_tokens", 0),
                estimated_cost_usd=event.get("estimated_cost_usd", 0.0),
                provider=event.get("provider", "unknown"),
            )

    skipped_providers = [
        {
            "provider": event["provider"],
            "model": event["model"],
            "stage": event["stage"],
            "reason": event["reason"],
        }
        for event in budget.events
        if event.get("skipped")
    ]

    return {
        "query": query,
        "mode": "deep_consensus",
        "final_answer": final_answer,
        "model_opinions": model_opinions,
        "claim_checks": claim_checks,
        "disagreement_map": disagreement_map,
        "evidence_graph": {
            "question": query,
            "sub_questions": _derive_sub_questions(query, model_opinions),
            "evidence_sources": _extract_sources(evidence_bundle),
            "claims": claim_candidates,
            "model_opinion_count": len([m for m in model_opinions if not m.get("skipped")]),
            "verified_claim_count": len(claim_checks),
            "retrieval_notes": reliability_notes,
        },
        "cost_report": budget.to_dict(),
        "skipped_providers": skipped_providers,
        "reliability_notes": reliability_notes + _workflow_reliability_notes(model_opinions),
    }


def _collect_model_opinions(query: str, evidence: str, budget: CostBudget) -> list[dict]:
    system = (
        "You are one member of a multi-model research panel. "
        "Analyze the question independently. Use the provided evidence, name weak assumptions, "
        "and propose the best answer. Keep it concise and factual."
    )
    user = f"""
Question:
{query}

Evidence:
{evidence[:7000]}

Return:
- Your answer
- Key claims
- Weak or uncertain points
- Confidence from 0 to 1
"""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    providers = ["gemini", "groq"]
    opinions = []
    for provider in providers:
        response = call_model(
            provider,  # type: ignore[arg-type]
            messages,
            max_tokens=900,
            temperature=0.2,
            budget=budget,
            stage="model_opinion",
        )
        opinions.append(
            {
                "provider": response.provider,
                "model": response.model,
                "content": response.content,
                "confidence": _confidence_from_text(response.content),
                "skipped": response.skipped,
                "reason": response.reason,
                "estimated_cost_usd": round(response.estimated_cost_usd, 6),
                "tokens": response.usage.total_tokens,
            }
        )
    return opinions


def _extract_claims(model_opinions: list[dict], query: str) -> list[str]:
    text = "\n".join(m.get("content", "") for m in model_opinions if not m.get("skipped"))
    candidates: list[str] = []
    for line in re.split(r"[\n\r]+", text):
        cleaned = re.sub(r"^[-*0-9.\s]+", "", line).strip()
        if not cleaned or len(cleaned) < 35:
            continue
        if any(word in cleaned.lower() for word in ["confidence", "uncertain", "weak point"]):
            continue
        candidates.append(cleaned[:260])

    if not candidates:
        candidates = [
            f"The system should answer the user's question directly: {query}",
            "Important claims should be supported by retrieved evidence.",
            "Model disagreements should be surfaced instead of hidden.",
        ]

    deduped: list[str] = []
    seen = set()
    for claim in candidates:
        key = claim.lower()[:80]
        if key not in seen:
            deduped.append(claim)
            seen.add(key)
        if len(deduped) == 6:
            break
    return deduped


def _verify_claims(
    query: str,
    evidence: str,
    model_opinions: list[dict],
    claims: list[str],
    budget: CostBudget,
) -> list[dict]:
    verifier_context = "\n\n".join(
        f"{m['provider']} opinion:\n{m.get('content', '')[:1600]}"
        for m in model_opinions
        if not m.get("skipped")
    )
    claims_block = "\n".join(f"{i + 1}. {claim}" for i, claim in enumerate(claims))
    prompt = f"""
Question:
{query}

Evidence:
{evidence[:6500]}

Model opinions:
{verifier_context[:5000]}

Claims to check:
{claims_block}

Return ONLY valid JSON in this exact shape:
{{
  "claim_checks": [
    {{
      "claim_index": 1,
      "support": "strong|partial|weak|unsupported",
      "confidence": 0.0,
      "reason": "short reason based only on the evidence",
      "evidence_refs": ["short source title or URL if available"]
    }}
  ]
}}
"""
    response = call_model(
        "gemini",
        [{"role": "system", "content": "You are a strict claim verifier."}, {"role": "user", "content": prompt}],
        max_tokens=900,
        temperature=0.0,
        budget=budget,
        stage="claim_verifier",
    )

    if response.skipped:
        response = call_model(
            "groq",
            [{"role": "system", "content": "You are a strict claim verifier."}, {"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.0,
            budget=budget,
            stage="claim_verifier_fallback",
        )

    parsed = _parse_claim_checks(response.content, claims)
    if parsed:
        return parsed

    return [
        {
            "claim": claim,
            "support": "pending",
            "confidence": 0.0,
            "reason": response.reason or "Verifier did not return parseable structured output.",
            "evidence_refs": [],
        }
        for claim in claims
    ]


def _parse_claim_checks(text: str, claims: list[str]) -> list[dict]:
    json_checks = _parse_claim_checks_json(text, claims)
    if json_checks:
        return json_checks

    checks: list[dict] = []
    for line in text.splitlines():
        match = re.search(
            r"Claim\s+(\d+)\s*\|\s*support:\s*([^|]+)\|\s*confidence:\s*([0-9.]+)\s*\|\s*reason:\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if not match:
            continue
        idx = int(match.group(1)) - 1
        if idx < 0 or idx >= len(claims):
            continue
        checks.append(
            {
                "claim": claims[idx],
                "support": match.group(2).strip().lower(),
                "confidence": min(1.0, max(0.0, float(match.group(3)))),
                "reason": match.group(4).strip(),
                "evidence_refs": [],
            }
        )
    return checks


def _parse_claim_checks_json(text: str, claims: list[str]) -> list[dict]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return []
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    rows = payload.get("claim_checks", [])
    if not isinstance(rows, list):
        return []

    parsed: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("claim_index", 0)) - 1
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(claims):
            continue
        support = str(row.get("support", "unsupported")).lower()
        if support not in {"strong", "partial", "weak", "unsupported"}:
            support = "unsupported"
        try:
            confidence = float(row.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        evidence_refs = row.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            evidence_refs = []
        parsed.append(
            {
                "claim": claims[idx],
                "support": support,
                "confidence": min(1.0, max(0.0, confidence)),
                "reason": str(row.get("reason", "")).strip() or "No verifier reason returned.",
                "evidence_refs": [str(ref)[:180] for ref in evidence_refs[:3]],
            }
        )
    return parsed


def _build_disagreement_map(model_opinions: list[dict], claim_checks: list[dict]) -> list[dict]:
    available = [m for m in model_opinions if not m.get("skipped")]
    rows = []
    for check in claim_checks:
        claim = check["claim"]
        stance = {}
        for opinion in available:
            content = opinion.get("content", "").lower()
            words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{4,}", claim)[:6]]
            overlap = sum(1 for word in words if word in content)
            stance[opinion["provider"]] = "agrees" if overlap >= 2 else "unclear"
        unique_stances = set(stance.values())
        if len(available) < 2:
            status = "single_model"
        elif len(unique_stances) == 1 and "agrees" in unique_stances:
            status = "agreement"
        else:
            status = "needs_review"
        rows.append(
            {
                "claim": claim,
                "stances": stance,
                "verifier_support": check.get("support"),
                "confidence": check.get("confidence", 0.0),
                "status": status,
            }
        )
    return rows


def _synthesize_final_answer(
    query: str,
    evidence: str,
    model_opinions: list[dict],
    claim_checks: list[dict],
    disagreement_map: list[dict],
    budget: CostBudget,
) -> str:
    opinions = "\n\n".join(
        f"{m['provider']} ({m['model']}):\n{m.get('content', '')[:1800]}"
        for m in model_opinions
        if not m.get("skipped")
    )
    checks = "\n".join(
        f"- {c['claim']} | support={c.get('support')} | confidence={c.get('confidence')} | {c.get('reason')}"
        for c in claim_checks
    )
    disagreements = "\n".join(
        f"- {d['claim']} | status={d.get('status')} | stances={d.get('stances')}"
        for d in disagreement_map
    )
    prompt = f"""
Question:
{query}

Evidence:
{evidence[:5000]}

Model opinions:
{opinions[:6000]}

Claim verification:
{checks}

Disagreement map:
{disagreements}

Write the final answer in Markdown. Include:
1. Direct answer
2. Evidence-backed points
3. Where models disagree or evidence is weak
4. Practical recommendation
5. Confidence summary
"""
    response = call_model(
        "gemini",
        [{"role": "system", "content": "You synthesize verified multi-model research."}, {"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.2,
        budget=budget,
        stage="final_synthesis",
    )
    if response.skipped:
        response = call_model(
            "groq",
            [{"role": "system", "content": "You synthesize verified multi-model research."}, {"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.2,
            budget=budget,
            stage="final_synthesis_fallback",
        )
    if response.skipped:
        return (
            "## Deep Consensus could not run yet\n\n"
        "Add at least one Gemini or Groq API key to enable final synthesis. The workflow still prepared "
        "the evidence graph and cost plan, but no model was available within the configured budget."
        )
    return response.content


def _derive_sub_questions(query: str, model_opinions: list[dict]) -> list[str]:
    base = [
        f"What evidence directly answers: {query}?",
        "Which claims are strongly supported by sources?",
        "Where do models disagree or show uncertainty?",
    ]
    for opinion in model_opinions:
        if opinion.get("provider") == "gemini" and not opinion.get("skipped"):
            base.insert(1, "How does Gemini interpret the retrieved evidence?")
            break
    return base[:4]


def _extract_sources(text: str) -> list[dict]:
    urls = re.findall(r"https?://[^\s)]+", text)
    deduped = []
    seen = set()
    for url in urls:
        clean = url.rstrip(".,]")
        if clean in seen:
            continue
        seen.add(clean)
        deduped.append({"url": clean})
        if len(deduped) == 10:
            break
    return deduped


def _confidence_from_text(text: str) -> float | None:
    match = re.search(r"confidence[^0-9]*(0(?:\.\d+)?|1(?:\.0+)?)", text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def _evidence_reliability_notes(web_evidence: str, kb_evidence: str) -> list[str]:
    notes: list[str] = []
    if "Error executing web search" in web_evidence or "No web search results" in web_evidence:
        notes.append("Web retrieval did not return strong evidence for this run.")
    if "KB Search Error" in kb_evidence or "No relevant information" in kb_evidence:
        notes.append("Knowledge-base retrieval was unavailable or had no relevant matches.")
    if not notes:
        notes.append("Web and knowledge-base retrieval both returned evidence candidates.")
    return notes


def _workflow_reliability_notes(model_opinions: list[dict]) -> list[str]:
    available = [m for m in model_opinions if not m.get("skipped")]
    if len(available) == 0:
        return ["No LLM provider was available, so consensus and verification could not actually run."]
    if len(available) == 1:
        return ["Only one model provider ran, so the disagreement map is a single-model audit, not true cross-model consensus."]
    return ["At least two model providers ran, so cross-model agreement signals are available."]
