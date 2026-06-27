"""
session_store.py
----------------
Thread-safe, in-memory conversation session store with TTL-based eviction.

Architecture note: This is intentionally designed with a Redis-compatible
interface (get/set/delete/exists pattern) so it can be swapped for redis-py
in production with minimal code changes. In a real deployment you'd pass
a Redis client via dependency injection instead of using this singleton.

Redis swap guide:
    - Replace self._store with a Redis connection
    - get_history()     → r.lrange(key, 0, -1)   (after JSON decode)
    - append_message()  → r.rpush(key, json.dumps(msg)); r.expire(key, TTL)
    - clear_session()   → r.delete(key)
    - list_sessions()   → r.keys("session:*")
"""

import threading
import time
import uuid
from typing import Any

# Session TTL: 1 hour (matching typical LLM chat session lifetimes)
SESSION_TTL_SECONDS = 3600


class SessionStore:
    """
    In-memory session store with TTL eviction.

    Each session holds a list of conversation messages:
        [{"role": "user"|"assistant", "content": "...", "ts": <unix_ts>}, ...]

    Also stores arbitrary metadata per session (e.g. session creation time).
    """

    def __init__(self, ttl: int = SESSION_TTL_SECONDS):
        self._ttl = ttl
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, session_id: str | None = None) -> str:
        """
        Creates a new session. Returns the session_id.
        If session_id is not provided, generates a UUID4.
        """
        sid = session_id or str(uuid.uuid4())
        with self._lock:
            self._sessions[sid] = {
                "messages": [],
                "created_at": time.time(),
                "last_access": time.time(),
            }
        return sid

    def exists(self, session_id: str) -> bool:
        """Returns True if the session exists and has not expired."""
        with self._lock:
            self._evict_expired()
            return session_id in self._sessions

    def get_history(self, session_id: str) -> list[dict]:
        """
        Returns the message history for a session.
        Raises KeyError if session does not exist or has expired.
        """
        with self._lock:
            self._evict_expired()
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Session '{session_id}' not found or expired.")
            session["last_access"] = time.time()
            # Return a shallow copy so external mutations don't affect the store
            return list(session["messages"])

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """
        Appends a message to the session history.
        Auto-creates the session if it doesn't exist (lazy creation).
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "messages": [],
                    "created_at": time.time(),
                    "last_access": time.time(),
                }
            session = self._sessions[session_id]
            session["messages"].append(
                {"role": role, "content": content, "ts": time.time()}
            )
            session["last_access"] = time.time()

    def clear_session(self, session_id: str) -> bool:
        """
        Clears (deletes) a session. Returns True if it existed, False otherwise.
        """
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def list_sessions(self) -> list[dict]:
        """
        Lists all active (non-expired) session IDs with metadata.
        """
        with self._lock:
            self._evict_expired()
            now = time.time()
            return [
                {
                    "session_id": sid,
                    "message_count": len(data["messages"]),
                    "created_at": data["created_at"],
                    "last_access": data["last_access"],
                    "expires_in": max(
                        0, self._ttl - (now - data["last_access"])
                    ),
                }
                for sid, data in self._sessions.items()
            ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        """Removes sessions that have exceeded TTL. Must be called under lock."""
        now = time.time()
        expired = [
            sid
            for sid, data in self._sessions.items()
            if (now - data["last_access"]) > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]


# Global singleton — mirrors how you'd initialise a Redis client globally
session_store = SessionStore()
