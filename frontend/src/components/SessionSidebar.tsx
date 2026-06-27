"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { TokenStats } from "@/lib/api";
import TokenStatsComponent from "./TokenStats";

interface Props {
  sessionId: string | null;
  onNewSession: (id: string) => void;
  onClearSession: () => void;
  onClose?: () => void;
}

export default function SessionSidebar({ sessionId, onNewSession, onClearSession, onClose }: Props) {
  const [stats, setStats]       = useState<TokenStats | null>(null);
  const [creating, setCreating] = useState(false);

  const refreshStats = async () => {
    try { setStats(await api.getGlobalStats()); } catch { /* ignore */ }
  };

  useEffect(() => {
    refreshStats();
    const t = setInterval(refreshStats, 8000);
    return () => clearInterval(t);
  }, [sessionId]);

  const handleNew = async () => {
    setCreating(true);
    try {
      const res = await api.createSession();
      onNewSession(res.session_id);
      await refreshStats();
    } finally { setCreating(false); }
  };

  const handleClear = async () => {
    if (!sessionId) return;
    try { await api.deleteSession(sessionId); onClearSession(); await refreshStats(); } catch {}
  };

  const STACK = ["LLaMA 3.3 70B", "Groq", "LangGraph", "Pinecone", "FastAPI", "Next.js"];

  return (
    <div style={{
      width: "var(--sidebar-width)",
      height: "100%", overflowY: "auto",
      display: "flex", flexDirection: "column", gap: 14,
      padding: "20px 16px",
      background: "rgba(12,16,32,0.98)",
      borderRight: "1px solid rgba(99,102,241,0.18)",
    }}>

      {/* Header row with close btn */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>Session</p>
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2, lineHeight: 1.4 }}>
            Memory-aware context
          </p>
        </div>
        {/* Close button — only visible on mobile via page.tsx (onClose) */}
        {onClose && (
          <button
            onClick={onClose}
            className="mobile-menu-btn btn-icon"
            aria-label="Close sidebar"
            style={{ flexShrink: 0 }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        )}
      </div>

      {/* Session box */}
      <div style={{
        borderRadius: 12, padding: "12px 13px",
        background: "rgba(10,14,26,0.7)",
        border: "1px solid rgba(99,102,241,0.15)",
        display: "flex", flexDirection: "column", gap: 8,
      }}>
        {sessionId ? (
          <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span className="badge badge-green">Active</span>
              <button onClick={handleClear} style={{
                background: "none", border: "none", cursor: "pointer",
                fontSize: 11, color: "#f87171", fontFamily: "inherit",
              }}>Clear ✕</button>
            </div>
            <code style={{
              display: "block", fontSize: 9, wordBreak: "break-all",
              color: "var(--text-muted)", lineHeight: 1.5,
            }}>{sessionId}</code>
          </>
        ) : (
          <p style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5 }}>
            No active session. Create one to enable conversation memory.
          </p>
        )}
      </div>

      {/* New session button */}
      <button
        id="new-session-btn"
        onClick={handleNew}
        disabled={creating}
        className="btn-primary"
        style={{ width: "100%", fontSize: 13, padding: "11px", gap: 7 }}
      >
        {creating
          ? <span className="spinner" style={{ width: 14, height: 14 }} />
          : <span>＋</span>}
        {sessionId ? "New Session" : "Create Session"}
      </button>

      {/* Divider */}
      <div style={{ borderTop: "1px solid rgba(99,102,241,0.12)" }} />

      {/* Token stats */}
      <TokenStatsComponent stats={stats} />

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Tech stack */}
      <div style={{ paddingTop: 8, borderTop: "1px solid rgba(99,102,241,0.1)" }}>
        <p style={{
          fontSize: 9, fontWeight: 700, textTransform: "uppercase",
          letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 7,
        }}>Tech Stack</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
          {STACK.map((t) => (
            <span key={t} className="badge badge-purple" style={{
              fontSize: 9, padding: "3px 7px", textTransform: "none", fontWeight: 500,
            }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
