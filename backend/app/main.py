from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import research, rag, agent, memory

app = FastAPI(
    title="ResearchMind API",
    version="0.5.0",
    description=(
        "Multi-Agent AI Research Assistant — "
        "Powered by LLaMA 3.3 70B, LangGraph, Pinecone RAG, and ReAct agents."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, prefix="/api/v1", tags=["research"])
app.include_router(rag.router, prefix="/api/v1", tags=["rag"])
app.include_router(agent.router, prefix="/api/v1", tags=["agent"])
app.include_router(memory.router, prefix="/api/v1", tags=["memory"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": "0.5.0"}