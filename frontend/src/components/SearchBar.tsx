"use client";

import { useState } from "react";

const MODES = [
  { id: "research", label: "Quick Research", icon: "🔍", desc: "Structured LLM" },
  { id: "agent",    label: "ReAct Agent",    icon: "🤖", desc: "Tool reasoning" },
  { id: "team",     label: "Team Research",  icon: "🧠", desc: "Multi-agent" },
];

interface Props {
  onSearch: (query: string, mode: string) => void;
  loading: boolean;
}

export default function SearchBar({ onSearch, loading }: Props) {
  const [query, setQuery] = useState("");
  const [mode, setMode]   = useState("research");

  const submit = () => {
    if (!query.trim() || loading) return;
    onSearch(query.trim(), mode);
    setQuery("");
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", width: "100%" }}>

      {/* Mode tabs — horizontally scrollable on mobile */}
      <div className="mode-tabs">
        {MODES.map((m) => {
          const active = mode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              style={{
                flex: "0 0 auto",
                minWidth: 120,
                display: "flex", flexDirection: "column", alignItems: "center", gap: "2px",
                padding: "10px 10px",
                borderRadius: "10px",
                border: active ? "1px solid rgba(139,92,246,0.4)" : "1px solid transparent",
                background: active
                  ? "linear-gradient(135deg,rgba(139,92,246,0.22),rgba(99,102,241,0.18))"
                  : "transparent",
                color: active ? "#c4b5fd" : "#6b7280",
                cursor: "pointer",
                transition: "all 0.18s",
                fontFamily: "inherit",
              }}
            >
              <span style={{ fontSize: "18px" }}>{m.icon}</span>
              <span style={{ fontSize: "12px", fontWeight: 700 }}>{m.label}</span>
              <span style={{ fontSize: "10px", opacity: 0.65 }}>{m.desc}</span>
            </button>
          );
        })}
      </div>

      {/* Search row — stacks on very small screens via CSS .search-row */}
      <div className="search-row">
        <div style={{ flex: 1, position: "relative" }}>
          <textarea
            id="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask ResearchMind anything… (↵ to send)"
            rows={2}
            disabled={loading}
            className="input-field"
            style={{ resize: "none", lineHeight: 1.6, paddingRight: "60px" }}
          />
          <span style={{
            position: "absolute", bottom: "10px", right: "12px",
            fontSize: "11px", color: "var(--text-muted)", pointerEvents: "none",
          }}>↵</span>
        </div>

        <button
          id="search-submit-btn"
          onClick={submit}
          disabled={loading || !query.trim()}
          className="btn-primary"
          style={{ alignSelf: "stretch", minWidth: "88px", gap: "7px", padding: "0 20px" }}
        >
          {loading
            ? <span className="spinner" style={{ width: 16, height: 16 }} />
            : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
          }
          {loading ? "…" : "Search"}
        </button>
      </div>
    </div>
  );
}
