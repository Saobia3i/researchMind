import re
from dataclasses import dataclass, field


@dataclass
class OptimizationReport:
    stage: str
    original_tokens: int
    final_tokens: int
    budget_tokens: int
    lines_kept: int
    lines_dropped: int
    notes: list[str] = field(default_factory=list)

    @property
    def saved_tokens(self) -> int:
        return max(0, self.original_tokens - self.final_tokens)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "original_tokens": self.original_tokens,
            "final_tokens": self.final_tokens,
            "budget_tokens": self.budget_tokens,
            "saved_tokens": self.saved_tokens,
            "lines_kept": self.lines_kept,
            "lines_dropped": self.lines_dropped,
            "notes": self.notes,
        }


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_to_token_budget(text: str, budget_tokens: int) -> str:
    if estimate_tokens(text) <= budget_tokens:
        return text.strip()
    return text[: budget_tokens * 4].rstrip()


def compact_evidence(
    text: str,
    *,
    budget_tokens: int,
    stage: str,
) -> tuple[str, OptimizationReport]:
    """
    Keeps the highest-signal retrieval lines under a token budget.

    Priority is intentionally simple and inspectable:
    URLs, titles, snippets, similarity scores, and error/reliability lines are kept first.
    """
    original_tokens = estimate_tokens(text)
    seen = set()
    scored_lines: list[tuple[int, int, str]] = []

    for index, raw_line in enumerate(text.splitlines()):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        key = line.lower()[:220]
        if key in seen:
            continue
        seen.add(key)
        scored_lines.append((_score_evidence_line(line), index, line))

    scored_lines.sort(key=lambda item: (-item[0], item[1]))

    kept: list[str] = []
    used_tokens = 0
    for _, _, line in scored_lines:
        line_tokens = estimate_tokens(line) + 1
        if kept and used_tokens + line_tokens > budget_tokens:
            continue
        if line_tokens > budget_tokens:
            line = trim_to_token_budget(line, budget_tokens)
            line_tokens = estimate_tokens(line)
        kept.append(line)
        used_tokens += line_tokens
        if used_tokens >= budget_tokens:
            break

    kept.sort(key=lambda line: text.find(line[:40]) if line[:40] in text else 10**9)
    compacted = "\n".join(kept).strip()
    final_tokens = estimate_tokens(compacted) if compacted else 0
    report = OptimizationReport(
        stage=stage,
        original_tokens=original_tokens,
        final_tokens=final_tokens,
        budget_tokens=budget_tokens,
        lines_kept=len(kept),
        lines_dropped=max(0, len(scored_lines) - len(kept)),
        notes=[
            "Deduplicated evidence lines.",
            "Prioritized URLs, titles, snippets, similarity scores, and error lines.",
        ],
    )
    if original_tokens > final_tokens:
        report.notes.append("Trimmed retrieval context before sending it to model providers.")
    return compacted, report


def compact_opinion(
    provider: str,
    content: str,
    *,
    budget_tokens: int,
) -> str:
    if not content.strip():
        return f"{provider}: no opinion returned."

    high_signal_lines = []
    fallback_lines = []
    for raw_line in content.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        lowered = line.lower()
        if any(key in lowered for key in ["claim", "confidence", "uncertain", "weak", "recommend", "source", "evidence"]):
            high_signal_lines.append(line)
        else:
            fallback_lines.append(line)

    merged = "\n".join((high_signal_lines + fallback_lines)[:12])
    return f"{provider} opinion summary:\n{trim_to_token_budget(merged, budget_tokens)}"


def compact_model_opinions(
    opinions: list[dict],
    *,
    per_opinion_budget_tokens: int,
    stage: str,
) -> tuple[str, OptimizationReport]:
    original = "\n\n".join(
        f"{opinion.get('provider')} ({opinion.get('model')}):\n{opinion.get('content', '')}"
        for opinion in opinions
        if not opinion.get("skipped")
    )
    summaries = [
        compact_opinion(
            str(opinion.get("provider", "unknown")),
            str(opinion.get("content", "")),
            budget_tokens=per_opinion_budget_tokens,
        )
        for opinion in opinions
        if not opinion.get("skipped")
    ]
    compacted = "\n\n".join(summaries)
    report = OptimizationReport(
        stage=stage,
        original_tokens=estimate_tokens(original),
        final_tokens=estimate_tokens(compacted) if compacted else 0,
        budget_tokens=per_opinion_budget_tokens * max(1, len(summaries)),
        lines_kept=len(compacted.splitlines()) if compacted else 0,
        lines_dropped=0,
        notes=["Compressed model opinions to high-signal claim/confidence/uncertainty lines."],
    )
    return compacted, report


def _score_evidence_line(line: str) -> int:
    lowered = line.lower()
    score = 0
    if "http://" in lowered or "https://" in lowered:
        score += 8
    if "title:" in lowered:
        score += 7
    if "snippet:" in lowered:
        score += 6
    if "similarity:" in lowered or "score" in lowered:
        score += 5
    if "error" in lowered or "no relevant" in lowered or "not found" in lowered:
        score += 5
    if len(line) > 260:
        score -= 2
    return score
