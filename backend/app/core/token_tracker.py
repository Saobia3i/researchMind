"""
token_tracker.py
----------------
Tracks Groq API token usage and estimated cost per session and globally.

In production AI engineering, cost attribution per user/session is critical.
This module provides a lightweight tracker that mirrors what you'd build on
top of a time-series DB (e.g. InfluxDB) or append to a data warehouse.

LLaMA 3.3 70B pricing on Groq (free-tier — tracked for portfolio display):
    Input:  $0.59  / 1M tokens
    Output: $0.79  / 1M tokens
    (Pricing as of mid-2025 — update COST_PER_1M_* if rates change)
"""

import threading
import time
from dataclasses import dataclass, field

# Groq LLaMA 3.3 70B pricing per 1M tokens (USD)
COST_PER_1M_INPUT = 0.59
COST_PER_1M_OUTPUT = 0.79


@dataclass
class UsageRecord:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    call_count: int = 0
    last_updated: float = field(default_factory=time.time)

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.estimated_cost_usd += _calc_cost(prompt, completion)
        self.call_count += 1
        self.last_updated = time.time()

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "call_count": self.call_count,
            "last_updated": self.last_updated,
        }


def _calc_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates estimated cost in USD for a single LLM call."""
    input_cost = (prompt_tokens / 1_000_000) * COST_PER_1M_INPUT
    output_cost = (completion_tokens / 1_000_000) * COST_PER_1M_OUTPUT
    return input_cost + output_cost


class TokenTracker:
    """
    Thread-safe token usage tracker.

    Maintains:
    - Per-session usage records
    - A global aggregate across all sessions
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: dict[str, UsageRecord] = {}
        self._global = UsageRecord()

    def record(
        self,
        session_id: str | None,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """
        Records token usage for an LLM call.

        Args:
            session_id: The session associated with this call. If None, only
                        the global stats are updated.
            prompt_tokens: Number of input/prompt tokens.
            completion_tokens: Number of output/completion tokens.
        """
        with self._lock:
            # Update global stats
            self._global.add(prompt_tokens, completion_tokens)

            # Update per-session stats
            if session_id:
                if session_id not in self._sessions:
                    self._sessions[session_id] = UsageRecord()
                self._sessions[session_id].add(prompt_tokens, completion_tokens)

    def get_session_stats(self, session_id: str) -> dict:
        """Returns usage stats for a specific session."""
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return UsageRecord().to_dict()
            return record.to_dict()

    def get_global_stats(self) -> dict:
        """Returns aggregate usage stats across all sessions."""
        with self._lock:
            return {
                "global": self._global.to_dict(),
                "active_sessions": len(self._sessions),
                "model": "llama-3.3-70b-versatile",
                "pricing": {
                    "input_per_1m_tokens_usd": COST_PER_1M_INPUT,
                    "output_per_1m_tokens_usd": COST_PER_1M_OUTPUT,
                },
            }

    def clear_session(self, session_id: str) -> None:
        """Removes per-session stats (e.g. when session is cleared)."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def record_from_groq_usage(
        self, session_id: str | None, usage_obj
    ) -> None:
        """
        Convenience method: records directly from a Groq CompletionUsage object.

        Usage:
            response = client.chat.completions.create(...)
            token_tracker.record_from_groq_usage(session_id, response.usage)
        """
        if usage_obj is None:
            return
        self.record(
            session_id=session_id,
            prompt_tokens=getattr(usage_obj, "prompt_tokens", 0),
            completion_tokens=getattr(usage_obj, "completion_tokens", 0),
        )


# Global singleton — initialise once, import everywhere
token_tracker = TokenTracker()
