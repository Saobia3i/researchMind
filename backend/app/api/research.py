from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.core.structured import call_llm_structured
from app.memory.session_store import session_store
from app.core.token_tracker import token_tracker

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The research topic or question.")
    session_id: str | None = Field(
        None,
        description=(
            "Optional session ID to save this interaction to memory. "
            "Create one via POST /api/v1/memory/session."
        ),
    )


class ResearchResponse(BaseModel):
    query: str
    session_id: str | None
    title: str
    summary: str
    key_points: list[str]
    confidence: float
    suggested_followups: list[str]


@router.post("/research", response_model=ResearchResponse)
def research_query(request: ResearchRequest):
    """
    Runs a structured LLM query to research the given topic.
    Returns a structured response: title, summary, key points, confidence score,
    and follow-up suggestions.

    Optionally accepts a session_id to persist interactions to conversation memory.
    """
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
            "suggested_followups": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "title",
            "summary",
            "key_points",
            "confidence",
            "suggested_followups",
        ],
    }

    messages = [
        {"role": "user", "content": f"Research this topic: {request.query}"}
    ]

    try:
        result = call_llm_structured(
            messages=messages,
            system="You are an expert research assistant. Analyze the given topic thoroughly.",
            output_schema=schema,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM call failed: {str(e)}",
        )

    # Persist to session memory if session_id provided
    if request.session_id:
        if not session_store.exists(request.session_id):
            session_store.create_session(request.session_id)
        session_store.append_message(request.session_id, "user", request.query)
        session_store.append_message(
            request.session_id,
            "assistant",
            f"{result.get('title', '')}: {result.get('summary', '')}",
        )
        # Estimate token usage (structured call doesn't expose usage object,
        # so we approximate based on character count — ~4 chars per token)
        approx_prompt = len(request.query) // 4
        approx_completion = len(str(result)) // 4
        token_tracker.record(
            session_id=request.session_id,
            prompt_tokens=approx_prompt,
            completion_tokens=approx_completion,
        )

    return ResearchResponse(
        query=request.query,
        session_id=request.session_id,
        **result,
    )
