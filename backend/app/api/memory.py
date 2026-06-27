from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.memory.session_store import session_store
from app.core.token_tracker import token_tracker

router = APIRouter()


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------


class CreateSessionResponse(BaseModel):
    session_id: str
    message: str


class MessageItem(BaseModel):
    role: str
    content: str
    ts: float


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageItem]
    message_count: int


class SessionListResponse(BaseModel):
    sessions: list[dict]
    total: int


class DeleteSessionResponse(BaseModel):
    session_id: str
    deleted: bool


@router.post(
    "/memory/session",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
def create_session():
    """
    Creates a new conversation session and returns a session_id.
    Pass this session_id in subsequent /research or /agent/chat calls
    to maintain conversation context across requests.
    """
    sid = session_store.create_session()
    return CreateSessionResponse(
        session_id=sid,
        message=f"Session '{sid}' created successfully.",
    )


@router.get(
    "/memory/session/{session_id}",
    response_model=SessionHistoryResponse,
    summary="Retrieve conversation history for a session",
)
def get_session_history(session_id: str):
    """
    Returns the full message history for the given session.
    Messages are ordered oldest-first.
    """
    try:
        messages = session_store.get_history(session_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found or has expired.",
        )
    return SessionHistoryResponse(
        session_id=session_id,
        messages=[MessageItem(**m) for m in messages],
        message_count=len(messages),
    )


@router.delete(
    "/memory/session/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Clear and delete a session",
)
def delete_session(session_id: str):
    """
    Clears a session and its conversation history.
    Also removes associated token tracking data.
    """
    deleted = session_store.clear_session(session_id)
    token_tracker.clear_session(session_id)
    return DeleteSessionResponse(session_id=session_id, deleted=deleted)


@router.get(
    "/memory/sessions",
    response_model=SessionListResponse,
    summary="List all active sessions",
)
def list_sessions():
    """Lists all currently active (non-expired) sessions with metadata."""
    sessions = session_store.list_sessions()
    return SessionListResponse(sessions=sessions, total=len(sessions))


# ---------------------------------------------------------------------------
# Token usage / cost tracking endpoints
# ---------------------------------------------------------------------------


class TokenStatsResponse(BaseModel):
    global_stats: dict
    session_id: str | None = None
    session_stats: dict | None = None


@router.get(
    "/memory/stats",
    response_model=TokenStatsResponse,
    summary="Get global token usage and cost stats",
)
def get_global_token_stats():
    """
    Returns aggregate token usage and estimated cost across all sessions.
    Cost is calculated based on Groq's LLaMA 3.3 70B pricing.
    """
    return TokenStatsResponse(global_stats=token_tracker.get_global_stats())


@router.get(
    "/memory/stats/{session_id}",
    response_model=TokenStatsResponse,
    summary="Get token usage stats for a specific session",
)
def get_session_token_stats(session_id: str):
    """
    Returns token usage and estimated cost for a specific session.
    Returns zeroed stats if the session has no recorded usage.
    """
    return TokenStatsResponse(
        global_stats=token_tracker.get_global_stats(),
        session_id=session_id,
        session_stats=token_tracker.get_session_stats(session_id),
    )
