"use client";

import { useState } from "react";
import type { AgentStep } from "@/lib/api";

interface Props { steps: AgentStep[]; }

const TOOL_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  web_search: { bg: "rgba(6,182,212,0.12)",  color: "#22d3ee", border: "rgba(6,182,212,0.25)" },
  calculate:  { bg: "rgba(245,158,11,0.12)", color: "#fbbf24", border: "rgba(245,158,11,0.25)" },
  kb_search:  { bg: "rgba(139,92,246,0.12)", color: "#a78bfa", border: "rgba(139,92,246,0.25)" },
};

export default function AgentTrace({ steps }: Props) {
  const [open, setOpen] = useState<Set<number>>(new Set([0]));
  const toggle = (i: number) => setOpen((p) => { const n = new Set(p); n.has(i) ? n.delete(i) : n.add(i); return n; });

  if (!steps.length) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <p style={{
        fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em",
        color: "var(--text-muted)", marginBottom: 2,
      }}>
        Reasoning Trace — {steps.length} step{steps.length !== 1 ? "s" : ""}
      </p>

      <div style={{ position: "relative" }}>
        {/* Timeline line */}
        <div style={{
          position: "absolute", left: 19, top: 0, bottom: 0, width: 1,
          background: "linear-gradient(180deg, rgba(139,92,246,0.5), rgba(6,182,212,0.15))",
        }} />

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {steps.map((step, i) => {
            const isOpen = open.has(i);
            const isFinal = !step.action;
            const toolStyle = step.action ? TOOL_STYLE[step.action] ?? TOOL_STYLE.kb_search : null;

            return (
              <div key={i} className="fade-in" style={{ animationDelay: `${i * 0.05}s` }}>
                <button
                  onClick={() => toggle(i)}
                  style={{
                    width: "100%", textAlign: "left", background: "none", border: "none",
                    cursor: "pointer", display: "flex", alignItems: "flex-start", gap: 12,
                    fontFamily: "inherit",
                  }}
                >
                  {/* Dot */}
                  <div style={{
                    position: "relative", zIndex: 1, flexShrink: 0,
                    width: 38, height: 38, borderRadius: "50%",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 12, fontWeight: 800, color: "white",
                    background: isFinal
                      ? "linear-gradient(135deg,#22c55e,#16a34a)"
                      : "linear-gradient(135deg,#8b5cf6,#6366f1)",
                    boxShadow: isFinal ? "0 0 14px rgba(34,197,94,0.4)" : "0 0 14px rgba(139,92,246,0.4)",
                  }}>
                    {isFinal ? "✓" : step.step}
                  </div>

                  {/* Card */}
                  <div style={{
                    flex: 1, borderRadius: 12, padding: "10px 14px",
                    background: isOpen ? "rgba(20,28,50,0.92)" : "rgba(13,17,30,0.7)",
                    border: `1px solid ${isOpen ? "rgba(139,92,246,0.3)" : "rgba(99,102,241,0.12)"}`,
                    transition: "all 0.18s ease",
                  }}>
                    {/* Header row */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", flex: 1 }}>
                        {toolStyle && (
                          <span style={{
                            display: "inline-flex", alignItems: "center",
                            padding: "3px 8px", borderRadius: 5,
                            fontSize: 10, fontWeight: 700, letterSpacing: "0.05em",
                            background: toolStyle.bg, color: toolStyle.color,
                            border: `1px solid ${toolStyle.border}`,
                          }}>
                            {step.action}
                          </span>
                        )}
                        {isFinal && (
                          <span style={{
                            display: "inline-flex", alignItems: "center",
                            padding: "3px 8px", borderRadius: 5,
                            fontSize: 10, fontWeight: 700, letterSpacing: "0.05em",
                            background: "rgba(34,197,94,0.12)", color: "#4ade80",
                            border: "1px solid rgba(34,197,94,0.25)",
                          }}>Final Answer</span>
                        )}
                        <span style={{
                          fontSize: 11, color: "var(--text-secondary)",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                          maxWidth: 280,
                        }}>
                          {step.thought?.slice(0, 90)}{(step.thought?.length ?? 0) > 90 ? "…" : ""}
                        </span>
                      </div>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#4a5568" strokeWidth="2"
                        style={{ flexShrink: 0, transform: isOpen ? "rotate(180deg)" : "none", transition: "transform .2s" }}>
                        <polyline points="6 9 12 15 18 9"/>
                      </svg>
                    </div>

                    {/* Expanded */}
                    {isOpen && (
                      <div className="fade-in" style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
                        {step.thought && (
                          <div>
                            <p style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#a78bfa", marginBottom: 4 }}>Thought</p>
                            <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.7 }}>{step.thought}</p>
                          </div>
                        )}
                        {step.action_input && (
                          <div>
                            <p style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#22d3ee", marginBottom: 4 }}>Action Input</p>
                            <code style={{
                              display: "block", fontSize: 11, padding: "8px 12px", borderRadius: 8,
                              background: "rgba(6,182,212,0.08)", color: "#67e8f9",
                              border: "1px solid rgba(6,182,212,0.2)", lineHeight: 1.5,
                            }}>{step.action_input}</code>
                          </div>
                        )}
                        {step.observation && (
                          <div>
                            <p style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#fbbf24", marginBottom: 4 }}>Observation</p>
                            <p style={{
                              fontSize: 11, padding: "8px 12px", borderRadius: 8, lineHeight: 1.6,
                              background: "rgba(245,158,11,0.06)", color: "var(--text-secondary)",
                              border: "1px solid rgba(245,158,11,0.15)",
                              maxHeight: 110, overflowY: "auto",
                            }}>{step.observation}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
