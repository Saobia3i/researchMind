# ResearchMind

ResearchMind is a full-stack AI research system that explores a more reliable way to answer complex questions: multiple research workflows, tool-using agents, retrieval, claim verification, disagreement mapping, and cost-aware model routing.

The goal is not to build another chatbot that simply returns sources. The goal is to make the research process inspectable: what evidence was retrieved, which model produced which opinion, which claims were verified, where confidence is weak, and how much the run costs.

## Why This Project Exists

Modern AI search tools can already produce answers with citations. That does not fully solve the trust problem.

A source link alone does not tell the user:

- whether a specific claim is actually supported by the source
- whether different models disagree
- whether the answer came from shallow retrieval or a structured workflow
- whether a claim is strong, partial, weak, or unsupported
- how many model calls were made
- how much the run cost
- whether missing API keys or failed retrieval affected the final answer

ResearchMind focuses on those missing layers: verification, transparency, model disagreement, evidence tracing, and cost awareness.

## Core Features

### 1. Quick Research

A fast structured-output mode for lightweight research questions.

It returns:

- title
- summary
- key points
- confidence score
- suggested follow-up questions

This mode is useful when a full agent workflow would be unnecessary.

### 2. ReAct Agent

A tool-using reasoning loop that follows a Thought -> Action -> Observation pattern.

Registered tools:

- `web_search`: searches the web through DuckDuckGo/DDGS
- `kb_search`: searches the Pinecone knowledge base
- `calculate`: safely evaluates basic arithmetic

The UI shows the agent trace so the user can inspect each step instead of only seeing the final answer.

### 3. Team Research

A LangGraph workflow that models a simple research team:

```text
Planner -> Researcher -> Writer
```

The planner breaks the query into sub-topics, the researcher gathers evidence, and the writer synthesizes a final report.

### 4. Deep Consensus

The newest and most important mode.

Deep Consensus is a cost-aware research workflow that:

1. retrieves web and knowledge-base evidence
2. compacts evidence into stage-specific token budgets
3. asks available model providers for independent opinions
4. compresses model opinions before verification and synthesis
5. extracts important claims
6. verifies claims against retrieved evidence
7. builds a model disagreement map
8. creates an evidence graph
9. synthesizes a final answer
10. reports skipped providers, weak retrieval, budget usage, and token savings

Default provider strategy:

- Gemini: free-tier/quota-friendly provider
- OpenRouter: optional model gateway, included in Deep Consensus when `OPENROUTER_API_KEY` is configured
- Groq: fast model provider, also useful for free-tier experimentation
- OpenAI: optional adapter, not used by default
- Perplexity: optional adapter, not used by default because the API is paid

If only one provider runs, the app does not pretend that true multi-model consensus happened. It marks the disagreement map as a single-model audit and shows reliability notes in the UI.

## What Makes It Different

ResearchMind does not compete with Gemini Search or ChatGPT on "showing sources." The differentiator is the audit layer around the answer.

It shows:

- model opinions
- claim-level verification
- support labels: strong, partial, weak, unsupported
- evidence references per claim
- disagreement status
- reliability notes
- skipped provider reasons
- token and cost tracking
- stage-level prompt budgets
- evidence deduplication and prompt compaction
- early-stop provider routing when strong agreement is reached
- session-level memory
- retrieval limitations

That makes the project closer to a research workflow system than a simple AI chat interface.

## Architecture

```text
Frontend: Next.js + React + TypeScript
    |
    | REST API
    v
Backend: FastAPI
    |
    |-- Quick Research
    |-- ReAct Agent
    |-- LangGraph Team Research
    |-- Deep Consensus Workflow
    |
    |-- Provider Router
    |      |-- Gemini
    |      |-- OpenRouter
    |      |-- Groq
    |      |-- OpenAI optional
    |      |-- Perplexity optional
    |
    |-- Tools
    |      |-- Web Search
    |      |-- KB Search
    |      |-- Calculator
    |
    |-- RAG
    |      |-- Pinecone
    |
    |-- Memory and Cost Tracking
```

## Tech Stack

Backend:

- Python
- FastAPI
- Pydantic
- LangGraph
- Groq SDK
- Gemini REST API through `httpx`
- OpenRouter chat completions API through `httpx`
- Pinecone
- DDGS / DuckDuckGo search
- Uvicorn

Frontend:

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS

AI engineering concepts:

- ReAct tool calling
- multi-agent orchestration
- model-provider abstraction
- retrieval augmented generation
- claim verification
- disagreement mapping
- structured output parsing
- cost-aware routing
- session memory
- token tracking

## Project Structure

```text
researchMind/
  backend/
    app/
      agents/
        react.py
        team.py
        consensus.py
      api/
        agent.py
        memory.py
        rag.py
        research.py
      core/
        config.py
        llm.py
        model_providers.py
        structured.py
        token_tracker.py
      memory/
        session_store.py
      rag/
        pinecone_client.py
        service.py
        text_splitter.py
      tools/
        web_search.py
        kb_search.py
        calculator.py
    requirements.txt
  frontend/
    src/
      app/
      components/
      lib/
    package.json
```

## Environment Variables

Create `backend/.env`.

Minimum recommended setup:

```env
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key
GROQ_API_KEY=your_groq_key

PINECONE_API_KEY=
PINECONE_INDEX_NAME=researchmind-index

DEFAULT_BUDGET_USD=1.00
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_INPUT_PER_1M_USD=0.0
OPENROUTER_OUTPUT_PER_1M_USD=0.0
```

Optional paid/credit-based providers:

```env
OPENAI_API_KEY=
PERPLEXITY_API_KEY=
```

Notes:

- Deep Consensus defaults to the free-friendly provider set: Gemini, OpenRouter, and Groq.
- OpenRouter pricing depends on the selected model. The default config assumes a free OpenRouter model. If you switch to a paid model, update `OPENROUTER_INPUT_PER_1M_USD` and `OPENROUTER_OUTPUT_PER_1M_USD`.
- Perplexity is intentionally not used by default because its API is paid.
- OpenAI is implemented as an optional adapter but is not part of the default free-friendly workflow.
- Pinecone can be left empty during local testing; KB search will report that it is unavailable.

## How To Run Locally

### 1. Install Backend Dependencies

From the project root:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you are creating a new virtual environment, Python 3.11+ is recommended:

```powershell
python -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Start Backend

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

### 3. Start Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Main API Endpoints

```text
GET  /health
POST /api/v1/research
POST /api/v1/agent/chat
POST /api/v1/agent/team_research
POST /api/v1/agent/consensus_research
POST /api/v1/rag/ingest
POST /api/v1/rag/search
POST /api/v1/memory/session
GET  /api/v1/memory/stats
```

## Deep Consensus Output

The `/api/v1/agent/consensus_research` endpoint returns:

- final answer
- model opinions
- claim checks
- disagreement map
- evidence graph
- cost report
- optimization report
- skipped providers
- reliability notes

Example conceptual output:

```text
Claim: "The proposed solution is production-ready."
Verifier support: partial
Confidence: 0.52
Reason: Architecture is production-inspired, but deployment, persistence, evals, and monitoring are not fully implemented.
Status: needs_review
```

This is deliberately conservative. The system should not overstate confidence when evidence is weak.

## Current Limitations

This is a portfolio-grade research system, not a finished production platform.

Known limitations:

- in-memory session store should be replaced with Redis for production
- Pinecone setup is optional and must be configured separately
- web search quality depends on DDGS results
- claim extraction is currently heuristic
- full evaluation suite is not implemented yet
- no production authentication or user billing layer
- no persistent database for audit history
- Gemini, OpenRouter, and Groq free-tier usage may be quota-limited

## Future Improvements

- Redis-backed memory
- persistent research runs in PostgreSQL
- model evaluation harness
- claim extraction using structured model output
- source quality scoring
- source contradiction detection
- reranking for retrieved evidence
- budget presets: Fast, Balanced, Deep
- semantic prompt compression using a cheap model
- cached retrieval and cached provider opinions
- report export to Markdown/PDF
- deployment with Docker

## Portfolio Value

This project demonstrates practical AI engineering beyond calling a model API:

- designing agent workflows
- building model-provider abstraction
- implementing RAG endpoints
- exposing agent traces
- adding cost-aware execution controls
- implementing stage-level token budgets and prompt compaction
- building claim-level verification
- handling missing provider keys gracefully
- surfacing reliability limitations to the user
- integrating a full-stack AI workflow into a usable UI

## Honest Positioning

ResearchMind should be described as:

> A cost-aware, multi-workflow AI research system with claim verification, model disagreement mapping, evidence tracing, and agent transparency.

It should not be described as:

> A fully production-ready autonomous research platform.

That distinction matters.
