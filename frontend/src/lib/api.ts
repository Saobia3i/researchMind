/**
 * api.ts — Typed API client for ResearchMind backend
 * All calls go to http://localhost:8000/api/v1
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface ResearchResponse {
  query: string;
  session_id: string | null;
  title: string;
  summary: string;
  key_points: string[];
  confidence: number;
  suggested_followups: string[];
}

export interface AgentStep {
  step: number;
  thought: string;
  action: string | null;
  action_input: string | null;
  observation: string | null;
}

export interface AgentResponse {
  query: string;
  session_id: string | null;
  steps: AgentStep[];
  final_answer: string;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

export interface TeamResearchResponse {
  query: string;
  session_id: string | null;
  plan: string;
  research_notes: string;
  final_report: string;
  steps: string[];
}

export interface ConsensusResearchResponse {
  query: string;
  mode: "deep_consensus";
  session_id: string | null;
  final_answer: string;
  model_opinions: Array<{
    provider: string;
    model: string;
    content: string;
    confidence: number | null;
    skipped: boolean;
    reason: string | null;
    estimated_cost_usd: number;
    tokens: number;
  }>;
  claim_checks: Array<{
    claim: string;
    support: string;
    confidence: number;
    reason: string;
    evidence_refs?: string[];
  }>;
  disagreement_map: Array<{
    claim: string;
    stances: Record<string, string>;
    verifier_support: string;
    confidence: number;
    status: string;
  }>;
  evidence_graph: {
    question: string;
    sub_questions: string[];
    evidence_sources: Array<{ url: string }>;
    claims: string[];
    model_opinion_count: number;
    verified_claim_count: number;
  };
  cost_report: {
    limit_usd: number;
    spent_usd: number;
    remaining_usd: number;
    events: Array<Record<string, unknown>>;
  };
  reliability_notes: string[];
  optimization_report: Array<{
    stage: string;
    original_tokens: number;
    final_tokens: number;
    budget_tokens: number;
    saved_tokens: number;
    lines_kept: number;
    lines_dropped: number;
    notes: string[];
  }>;
  skipped_providers: Array<{
    provider: string;
    model: string;
    stage: string;
    reason: string;
  }>;
}

export interface SessionHistory {
  session_id: string;
  messages: Array<{ role: string; content: string; ts: number }>;
  message_count: number;
}

export interface TokenStats {
  global_stats: {
    global: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      estimated_cost_usd: number;
      call_count: number;
    };
    active_sessions: number;
    model: string;
    pricing: { input_per_1m_tokens_usd: number; output_per_1m_tokens_usd: number };
  };
  session_id?: string;
  session_stats?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    call_count: number;
  };
}

export interface IngestResponse {
  doc_id: string;
  chunks_ingested: number;
  status: string;
}

export interface SearchMatch {
  id: string;
  score: number;
  text: string;
  metadata: Record<string, unknown>;
}

// ── API Functions ──────────────────────────────────────────────────────────

export const api = {
  // Sessions
  createSession: () =>
    apiFetch<{ session_id: string; message: string }>("/api/v1/memory/session", {
      method: "POST",
    }),

  getSessionHistory: (sessionId: string) =>
    apiFetch<SessionHistory>(`/api/v1/memory/session/${sessionId}`),

  deleteSession: (sessionId: string) =>
    apiFetch<{ session_id: string; deleted: boolean }>(
      `/api/v1/memory/session/${sessionId}`,
      { method: "DELETE" }
    ),

  // Stats
  getGlobalStats: () => apiFetch<TokenStats>("/api/v1/memory/stats"),
  getSessionStats: (sessionId: string) =>
    apiFetch<TokenStats>(`/api/v1/memory/stats/${sessionId}`),

  // Research
  research: (query: string, sessionId?: string) =>
    apiFetch<ResearchResponse>("/api/v1/research", {
      method: "POST",
      body: JSON.stringify({ query, session_id: sessionId ?? null }),
    }),

  // Agent Chat (ReAct)
  agentChat: (query: string, sessionId?: string) =>
    apiFetch<AgentResponse>("/api/v1/agent/chat", {
      method: "POST",
      body: JSON.stringify({ query, session_id: sessionId ?? null }),
    }),

  // Team Research (LangGraph)
  teamResearch: (query: string, sessionId?: string) =>
    apiFetch<TeamResearchResponse>("/api/v1/agent/team_research", {
      method: "POST",
      body: JSON.stringify({ query, session_id: sessionId ?? null }),
    }),

  consensusResearch: (query: string, sessionId?: string, budgetUsd?: number) =>
    apiFetch<ConsensusResearchResponse>("/api/v1/agent/consensus_research", {
      method: "POST",
      body: JSON.stringify({
        query,
        session_id: sessionId ?? null,
        budget_usd: budgetUsd ?? null,
      }),
    }),

  // RAG
  ingest: (text: string, doc_id: string, metadata?: Record<string, unknown>) =>
    apiFetch<IngestResponse>("/api/v1/rag/ingest", {
      method: "POST",
      body: JSON.stringify({ text, doc_id, metadata }),
    }),

  kbSearch: (query: string, top_k = 5) =>
    apiFetch<{ matches: SearchMatch[] }>("/api/v1/rag/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k }),
    }),

  // Health
  health: () => apiFetch<{ status: string; version: string }>("/health"),
};
