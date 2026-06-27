# 🧠 ResearchMind — Multi-Agent AI Research Assistant

> A portfolio project demonstrating production-level AI engineering skills:  
> multi-agent orchestration, RAG pipelines, ReAct reasoning, session memory, and token cost tracking.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-6366f1)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-f97316)](https://groq.com)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-00b383)](https://pinecone.io)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ResearchMind System                       │
│                                                              │
│  ┌──────────────┐   ┌──────────────────────────────────┐   │
│  │  Next.js 16  │   │         FastAPI Backend            │   │
│  │  Frontend    │◄──►  /api/v1/research  (structured)   │   │
│  │  (Port 3000) │   │  /api/v1/agent/chat  (ReAct)      │   │
│  └──────────────┘   │  /api/v1/agent/team_research       │   │
│                     │  /api/v1/rag/ingest + search       │   │
│                     │  /api/v1/memory/*  (sessions)      │   │
│                     └──────────┬───────────────────────┘   │
│                                │                             │
│              ┌─────────────────┼─────────────────┐          │
│              ▼                 ▼                  ▼          │
│        ┌──────────┐    ┌─────────────┐   ┌──────────────┐  │
│        │   Groq   │    │  LangGraph  │   │   Pinecone   │  │
│        │LLaMA 3.3 │    │Multi-Agent  │   │  Vector DB   │  │
│        │  70B API │    │  Pipeline   │   │  (RAG/KNN)   │  │
│        └──────────┘    └─────────────┘   └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

### 🔍 Phase 1 — Structured Research Endpoint
- POST `/api/v1/research` — Returns structured JSON: title, summary, key points, confidence score, follow-ups
- Powered by Groq's LLaMA 3.3 70B with forced JSON output via `response_format`

### 🗄️ Phase 2 — RAG Pipeline (Pinecone)
- Document ingestion with sentence-level chunking
- Semantic search via Pinecone Inference embeddings
- POST `/api/v1/rag/ingest` and POST `/api/v1/rag/search`

### 🤖 Phase 3 — ReAct Agent
- Full ReAct (Reason + Act) loop with tool calling
- Tools: `web_search` (DuckDuckGo), `calculate` (safe eval), `kb_search` (Pinecone RAG)
- Exposes full step-by-step reasoning trace in response

### 🧠 Phase 4 — LangGraph Multi-Agent Team
- **Planner** → **Researcher** → **Writer** pipeline
- Researcher runs parallel web + KB searches per sub-topic
- Writer synthesizes a full Markdown research report with citations

### 💾 Phase 5 — Session Memory & Token Tracking
- Thread-safe in-memory session store (Redis-compatible interface, trivial to swap)
- Per-session conversation history for multi-turn context
- Token usage tracking with cost estimation (Groq pricing model)
- REST endpoints for session management and stats

### 🎨 Frontend (Next.js 16 + TypeScript)
- Dark glassmorphism UI
- 3 research modes: Quick / ReAct Agent / Team Research
- Agent step trace visualizer (timeline with expandable panels)
- Live token usage donut chart
- Session sidebar with create/clear controls

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (`py` command on Windows)
- Node.js 18+
- [Groq API key](https://console.groq.com/keys) (free)
- [Pinecone API key](https://app.pinecone.io/) (free tier, for RAG features)

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Start the server
uvicorn app.main:app --reload --port 8000
```

API docs available at: **http://localhost:8000/docs**

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: **http://localhost:3000**

---

## 📁 Project Structure

```
researchMind/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   │   ├── research.py   # Structured research endpoint
│   │   │   ├── rag.py        # RAG ingest + search
│   │   │   ├── agent.py      # ReAct + Team Research endpoints
│   │   │   └── memory.py     # Session management + token stats
│   │   ├── agents/
│   │   │   ├── react.py      # ReAct reasoning loop
│   │   │   └── team.py       # LangGraph multi-agent pipeline
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic settings
│   │   │   ├── llm.py        # Groq client wrapper
│   │   │   ├── structured.py # JSON-forced LLM calls
│   │   │   └── token_tracker.py  # Token usage + cost tracking
│   │   ├── memory/
│   │   │   └── session_store.py  # Redis-compatible session store
│   │   ├── rag/
│   │   │   ├── pinecone_client.py
│   │   │   ├── service.py    # Ingest + search logic
│   │   │   └── text_splitter.py
│   │   ├── tools/
│   │   │   ├── web_search.py
│   │   │   ├── calculator.py
│   │   │   └── kb_search.py
│   │   └── main.py           # FastAPI app + CORS
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx
    │   │   └── globals.css
    │   ├── components/
    │   │   ├── SearchBar.tsx
    │   │   ├── ResultCard.tsx
    │   │   ├── AgentTrace.tsx
    │   │   ├── TokenStats.tsx
    │   │   └── SessionSidebar.tsx
    │   └── lib/
    │       └── api.ts
    └── .env.local.example
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | LLaMA 3.3 70B via [Groq](https://groq.com) (free tier) |
| Agent Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Vector DB | [Pinecone](https://pinecone.io) (free tier) |
| Backend Framework | [FastAPI](https://fastapi.tiangolo.com) |
| Web Search | [DuckDuckGo Search](https://pypi.org/project/duckduckgo-search/) |
| Frontend | [Next.js 16](https://nextjs.org) + TypeScript |
| Styling | Vanilla CSS (glassmorphism design system) |

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | From [console.groq.com](https://console.groq.com/keys) |
| `APP_ENV` | ❌ | `development` or `production` (default: development) |
| `PINECONE_API_KEY` | ✅ for RAG | From [app.pinecone.io](https://app.pinecone.io) |

---

## 👤 Author

**[Your Name]** — 4th Year CSE Student  
Built as an AI Engineering portfolio project.

- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [your-profile](https://linkedin.com/in/your-profile)
