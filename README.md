# 🧠 ResearchMind: Multi-Agent AI Research Assistant
> A Production-Ready AI Engineering Portfolio Project showcasing Multi-Agent Orchestration, ReAct Tool-Calling, Vector Database RAG, and Cost-Attribution Systems.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 16](https://img.shields.io/badge/Next.js-16_Turbopack-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-State_Orchestration-6366f1)](https://github.com/langchain-ai/langgraph)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB_RAG-00b383)](https://pinecone.io)
[![Groq LLaMA-3.3-70B](https://img.shields.io/badge/Groq-LLaMA--3.3--70B-f97316)](https://groq.com)

---

## 1. 🎯 WHY (The Problem & Motivation)

### The Problem with Naive LLM Queries
When using standard LLM chat interfaces (like vanilla ChatGPT or raw API calls) for complex research:
1. **Hallucinations & Knowledge Cutoffs**: LLMs generate plausible-sounding but outdated or completely fabricated facts because they cannot query real-time sources out-of-the-box.
2. **Lack of Structure & Auditability**: Responses are walls of text with no clear separation of research planning, source references, or confidence scoring.
3. **No Execution Control**: The user has to trust the final output without being able to verify the step-by-step reasoning or tool executions the model took.
4. **Uncontrolled API Costs**: Naive loops can quickly consume tokens, yet production AI systems require strict per-session cost tracking and token budgets.

### The Solution: ResearchMind
ResearchMind solves these challenges by combining **structured JSON generation**, a **ReAct (Reasoning + Acting) Agent**, and a **LangGraph Multi-Agent Collaboration Team**. It provides:
- Fully auditable reasoning traces showing every thought, tool action, and tool output.
- Real-time information retrieval combining DuckDuckGo Web Search and Pinecone Vector RAG.
- Abstraction layers for memory and session cost tracking that simulate commercial, multi-tenant AI products.

---

## 2. 💡 WHAT (The Core Capabilities)

ResearchMind serves as a multi-mode research gateway offering three distinct pipelines depending on the complexity of the query:

### 🔍 Mode A: Quick Research (Structured Output)
Provides immediate, structured overviews. Rather than generating free-form Markdown, it leverages Groq's JSON mode to force LLaMA-3.3-70B to output a strictly typed schema containing:
* **Title** & **Comprehensive Summary**
* **Key Bullet Points**
* **Confidence Level (0.0 to 1.0)** based on context completeness
* **Suggested Follow-up Queries**

### 🤖 Mode B: ReAct Agent (Autonomous Tool-Use)
Runs a classic Reasoning and Acting loop (`Thought → Action → Observation → Thought`) to solve composite, multi-step queries:
* **Autonomy**: Automatically decides which tool to call based on the query.
* **Tools**: Accesses `web_search` (DuckDuckGo API), `calculate` (safe mathematical execution), and `kb_search` (Pinecone semantic search).
* **Auditability**: Renders a complete interactive timeline of the agent's internal reasoning loop, allowing recruiters to inspect every tool call and observation.

### 🧠 Mode C: Team Research (LangGraph Orchestration)
A multi-agent network that models an academic research team by executing an acyclic state machine:
```
  [START] ──► Planner Agent ──► Researcher Agent ──► Writer Agent ──► [END]
```
1. **Planner Agent**: Deconstructs the research query into 3 distinct, targeted sub-queries.
2. **Researcher Agent**: Executes parallel asynchronous search tasks (Web + Pinecone RAG) for each sub-topic, synthesizing comprehensive research notes with source URLs.
3. **Writer Agent**: Combines the plan and research notes into a formal, academic-style Markdown report complete with inline markdown citations and references.

---

## 3. ⚙️ HOW (System Design & Tech Stack)

### System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          NEXT.JS 16 FRONTEND                           │
│     (Interactive Dashboard, Donut Charts, Timelines, Mobile Drawer)    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTPS / REST (Port 3000 -> 8000)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                          FASTAPI BACKEND ROUTER                        │
│   (Session Manager, Token Tracker, CORS Middleware, Route Handlers)    │
└───────┬──────────────────────────┬──────────────────────────────┬──────┘
        │                          │                              │
┌───────▼─────────────┐    ┌───────▼─────────────┐        ┌───────▼──────┐
│  RE-ACT ENGINE      │    │  LANGGRAPH ENGINE   │        │ PINECONE RAG │
│  - Tool Registry    │    │  - Plan Node        │        │ - Ingest API │
│  - Reasoning Loop   │    │  - Research Node    │        │ - KNN Search │
│  - Trace Generator  │    │  - Writer Node      │        │ - Embeddings │
└───────┬─────────────┘    └───────┬─────────────┘        └───────┬──────┘
        │                          │                              │
        └─────────────────┬────────┴──────────────────────────────┘
                          │ Groq Chat Completions API
                   ┌──────▼─────────────┐
                   │  LLaMA-3.3-70B     │
                   │  (Host: Groq Cloud)│
                   └────────────────────┘
```

### 🧠 AI Engineering Stack Choice
* **LLM**: `llama-3.3-70b-versatile` via **Groq Cloud API** — Chosen for sub-second responses and near-perfect JSON schema adherence, making it optimal for interactive agent loops.
* **Agent Orchestration**: **LangGraph** — Used instead of basic LangChain because LangGraph models agent behaviors as native State Graphs, enabling cyclic graph patterns and precise control over agent state transitions.
* **Vector DB**: **Pinecone** — Used to implement the RAG pipeline. Utilizes Pinecone's serverless Inference API (`multilingual-e5-large`, 1024-dimensional embeddings) to bypass paid embedding API costs.

---

## 🛠️ Production Design Patterns

### 1. Redis-Compatible Session Memory (`app/memory/session_store.py`)
In production AI applications, maintaining conversational context (memory) requires a scalable cache. 
- ResearchMind uses a thread-safe, in-memory key-value dictionary with **automatic TTL eviction** (1-hour lifespan).
- **Interface Abstraction**: Implements standard `.get()`, `.append_message()`, and `.clear_session()` signatures. This mimics `redis-py` exactly, allowing the backend to be swapped to a Redis cluster in production by altering only the connection initialization.

### 2. Token & Cost Tracker (`app/core/token_tracker.py`)
AI engineers must monitor resource consumption to avoid runaway loops and calculate margins.
- Aggregates input (prompt) and output (completion) tokens.
- Computes real-time costs based on LLaMA-3.3-70B pricing ($0.59/M input, $0.79/M output).
- Returns stats via `/api/v1/memory/stats/{session_id}` for rendering in the frontend token analytics dashboard.

---

## 🚀 Installation & Local Run

### Prerequisites
- Python 3.11+ (Windows users: use `py`)
- Node.js 18+

### 1. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Mac/Linux

pip install -r requirements.txt
cp .env.example .env
# Edit .env and paste your GROQ_API_KEY and PINECONE_API_KEY
```

Run Backend:
```bash
uvicorn app.main:app --reload --port 8000
```
Verify interactive docs at **http://localhost:8000/docs**

### 2. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```
Open **http://localhost:3000** in your browser.

---

## 💼 Portfolio Highlights for Recruiters
This project demonstrates several key proficiencies required of a professional **AI/LLM Engineer**:
* **Structured Output Generation**: Bypasses the fragility of prompt-engineered instructions by enforcing JSON schema constraints natively at the model API level.
* **Asynchronous Multi-Agent State Orchestration**: Implements state management, graph cycles, and parallel tool executions using LangGraph.
* **Production-Ready Abstractions**: Implements session tracking and token cost modeling rather than just calling wrapper libraries.
* **Robust UI Integration**: Renders raw markdown, timeline reasoning traces, and token analytics beautifully in a fully responsive layout.
