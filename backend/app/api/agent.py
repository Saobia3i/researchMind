from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.agents.react import run_react_agent
from app.agents.team import compiled_graph
from app.memory.session_store import session_store
from app.core.token_tracker import token_tracker

router = APIRouter()


class AgentRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="The research query or question for the agent to resolve.",
    )
    session_id: str | None = Field(
        None,
        description=(
            "Optional session ID for multi-turn conversation memory. "
            "Create one via POST /api/v1/memory/session first."
        ),
    )


class AgentStep(BaseModel):
    step: int
    thought: str
    action: str | None = None
    action_input: str | None = None
    observation: str | None = None


class AgentResponse(BaseModel):
    query: str
    session_id: str | None
    steps: list[AgentStep]
    final_answer: str
    usage: dict


@router.post("/agent/chat", response_model=AgentResponse)
def agent_chat(request: AgentRequest):
    """
    Executes the step-by-step ReAct reasoning agent loop.

    - If `session_id` is provided, the agent will receive the prior conversation
      history as context, enabling multi-turn conversations.
    - Token usage is tracked per-session and globally.
    """
    # Load conversation history if session_id given
    history: list[dict] = []
    if request.session_id:
        if not session_store.exists(request.session_id):
            # Auto-create the session instead of failing — better DX
            session_store.create_session(request.session_id)
        else:
            try:
                history = session_store.get_history(request.session_id)
            except KeyError:
                history = []

    try:
        result = run_react_agent(query=request.query, history=history)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent reasoning execution failed: {str(e)}",
        )

    # Persist interaction to session store
    if request.session_id:
        session_store.append_message(request.session_id, "user", request.query)
        session_store.append_message(
            request.session_id, "assistant", result["final_answer"]
        )

    # Track token usage
    usage = result.get("usage", {})
    token_tracker.record(
        session_id=request.session_id,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
    )

    return AgentResponse(
        query=result["query"],
        session_id=request.session_id,
        steps=[AgentStep(**s) for s in result["steps"]],
        final_answer=result["final_answer"],
        usage=usage,
    )


class TeamResearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="The complex research query for the multi-agent team.",
    )
    session_id: str | None = Field(
        None,
        description="Optional session ID to save this research run to memory.",
    )


class TeamResearchResponse(BaseModel):
    query: str
    session_id: str | None
    plan: str
    research_notes: str
    final_report: str
    steps: list[str]


@router.post("/agent/team_research", response_model=TeamResearchResponse)
def team_research(request: TeamResearchRequest):
    """
    Runs the multi-agent LangGraph workflow: Planner → Researcher → Writer.

    Returns the generated plan, research notes, final report (Markdown),
    and the execution step sequence. Saves the report to session memory
    if a session_id is provided.
    """
    if request.session_id and not session_store.exists(request.session_id):
        session_store.create_session(request.session_id)

    try:
        initial_state = {
            "query": request.query,
            "plan": "",
            "research_notes": "",
            "final_report": "",
            "steps": [],
        }
        result = compiled_graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent team research execution failed: {str(e)}",
        )

    # Save the generated report to session memory
    if request.session_id:
        session_store.append_message(
            request.session_id, "user", request.query
        )
        session_store.append_message(
            request.session_id,
            "assistant",
            f"[Team Research Report]\n\n{result['final_report']}",
        )

    return TeamResearchResponse(
        query=request.query,
        session_id=request.session_id,
        plan=result["plan"],
        research_notes=result["research_notes"],
        final_report=result["final_report"],
        steps=result["steps"],
    )
