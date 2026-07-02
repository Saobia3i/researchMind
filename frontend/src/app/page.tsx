"use client";

import { useState, useRef, useEffect } from "react";
import SearchBar from "@/components/SearchBar";
import ResultCard from "@/components/ResultCard";
import AgentTrace from "@/components/AgentTrace";
import SessionSidebar from "@/components/SessionSidebar";
import { api } from "@/lib/api";
import type { ResearchResponse, AgentResponse, TeamResearchResponse, ConsensusResearchResponse, AgentStep } from "@/lib/api";

type AnyResult = ResearchResponse | AgentResponse | TeamResearchResponse | ConsensusResearchResponse;

interface HistoryItem {
  id: number;
  query: string;
  mode: string;
  result: AnyResult | null;
  error: string | null;
  agentSteps?: AgentStep[];
  ts: Date;
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading]     = useState(false);
  const [history, setHistory]     = useState<HistoryItem[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const handleSearch = async (query: string, mode: string) => {
    setLoading(true);
    setSidebarOpen(false); // close sidebar on mobile when searching
    const id = Date.now();
    setHistory((prev) => [{ id, query, mode, result: null, error: null, ts: new Date() }, ...prev]);

    try {
      let result: AnyResult;
      let agentSteps: AgentStep[] | undefined;

      if (mode === "research") {
        result = await api.research(query, sessionId ?? undefined);
      } else if (mode === "agent") {
        const res = await api.agentChat(query, sessionId ?? undefined);
        agentSteps = res.steps;
        result = res;
      } else if (mode === "team") {
        result = await api.teamResearch(query, sessionId ?? undefined);
      } else {
        result = await api.consensusResearch(query, sessionId ?? undefined);
      }

      setHistory((prev) => prev.map((item) => item.id === id ? { ...item, result, agentSteps } : item));
    } catch (err) {
      setHistory((prev) => prev.map((item) => item.id === id ? { ...item, error: (err as Error).message } : item));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.length]);

  // Close sidebar on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setSidebarOpen(false); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div style={{ minHeight: "100vh", display: "flex", background: "var(--bg-base)", position: "relative" }}>
      <div className="bg-mesh" />

      {/* ── Mobile overlay ── */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? "open" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* ── Sidebar ── */}
      <div className={`sidebar-panel glass-strong ${sidebarOpen ? "open" : ""}`}>
        <SessionSidebar
          sessionId={sessionId}
          onNewSession={(id) => { setSessionId(id); setSidebarOpen(false); }}
          onClearSession={() => { setSessionId(null); }}
          onClose={() => setSidebarOpen(false)}
        />
      </div>

      {/* ── Main content ── */}
      <main style={{
        flex: 1, minWidth: 0, display: "flex", flexDirection: "column",
        position: "relative", zIndex: 10,
        /* On desktop, offset for sticky sidebar */
        marginLeft: 0,
      }}>

        {/* ─── Header ─── */}
        <header className="main-header">

          {/* Top row: logo + hamburger */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              {/* Hamburger (mobile only — hidden on desktop via CSS) */}
              <button
                className="btn-icon mobile-menu-btn"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open sidebar"
                style={{ flexShrink: 0 }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                  <line x1="3" y1="6"  x2="21" y2="6"/>
                  <line x1="3" y1="12" x2="21" y2="12"/>
                  <line x1="3" y1="18" x2="21" y2="18"/>
                </svg>
              </button>

              {/* Logo */}
              <div style={{ display: "flex", alignItems: "center", gap: "11px" }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 11, flexShrink: 0,
                  background: "linear-gradient(135deg,#8b5cf6,#06b6d4)",
                  boxShadow: "0 4px 18px rgba(139,92,246,0.45)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 18, fontWeight: 900, color: "white",
                }}>R</div>
                <div>
                  <h1 className="gradient-text logo-title" style={{ fontWeight: 900, lineHeight: 1 }}>
                    ResearchMind
                  </h1>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: 3 }}>
                    Multi-Agent AI Research
                  </p>
                </div>
              </div>
            </div>

            {/* Session badge (mobile) */}
            {sessionId && (
              <span className="badge badge-green mobile-menu-btn" style={{ fontSize: 9 }}>
                Session Active
              </span>
            )}
          </div>

          {/* Tech pills — hide on very small screens */}
          <div style={{
            display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "16px",
          }} className="tech-pills">
            {[
              { label: "LLaMA 3.3 70B", color: "#a78bfa" },
              { label: "LangGraph",     color: "#22d3ee" },
              { label: "Pinecone RAG",  color: "#f472b6" },
              { label: "ReAct Agent",   color: "#fbbf24" },
              { label: "Gemini + Groq",  color: "#4ade80" },
            ].map((p) => (
              <span key={p.label} style={{
                padding: "3px 10px", borderRadius: 999,
                background: `${p.color}18`, border: `1px solid ${p.color}35`,
                color: p.color, fontSize: 11, fontWeight: 600,
              }}>{p.label}</span>
            ))}
          </div>

          <SearchBar onSearch={handleSearch} loading={loading} />
        </header>

        {/* ─── Results feed ─── */}
        <div className="results-feed">
          {history.length === 0 && (
            <div style={{
              flex: 1, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              paddingTop: "60px", opacity: 0.35, userSelect: "none", textAlign: "center",
            }}>
              <div style={{ fontSize: 56, marginBottom: 14 }}>🔬</div>
              <p style={{ fontSize: 14, color: "var(--text-muted)" }}>
                Your research results will appear here
              </p>
            </div>
          )}

          {[...history].reverse().map((item) => (
            <article key={item.id} className="result-article fade-in" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>

              {/* Query bubble */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <div style={{
                  display: "inline-flex", alignItems: "center", gap: 6,
                  padding: "7px 14px", borderRadius: 999,
                  background: "rgba(139,92,246,0.12)",
                  border: "1px solid rgba(139,92,246,0.25)",
                  color: "#c4b5fd", fontSize: 13, fontWeight: 500,
                  maxWidth: "100%", overflow: "hidden",
                }}>
                  <span>❝</span>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.query}
                  </span>
                </div>
                <span style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0 }}>
                  {item.ts.toLocaleTimeString()}
                </span>
              </div>

              {/* Loading state */}
              {!item.result && !item.error && (
                <div className="glass" style={{ padding: "18px 20px", display: "flex", alignItems: "center", gap: 12 }}>
                  <span className="spinner" />
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
                      {item.mode === "team"
                        ? "Running Planner to Researcher to Writer..."
                        : item.mode === "agent"
                        ? "Running ReAct reasoning loop..."
                        : item.mode === "consensus"
                        ? "Running multi-model debate, verification, and cost control..."
                        : "Analyzing with LLaMA 3.3 70B..."}
                    </p>
                    <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>
                      {item.mode === "team" || item.mode === "consensus" ? "Usually takes 20-60s" : "Usually takes 5-15s"}
                    </p>
                  </div>
                </div>
              )}

              {/* Result */}
              {(item.result || item.error) && (
                <ResultCard mode={item.mode} data={item.result} error={item.error} />
              )}

              {/* Agent trace */}
              {item.mode === "agent" && item.agentSteps && item.agentSteps.length > 0 && (
                <AgentTrace steps={item.agentSteps} />
              )}
            </article>
          ))}
          <div ref={bottomRef} />
        </div>
      </main>
    </div>
  );
}
