"use client";

import type { TokenStats } from "@/lib/api";

interface Props { stats: TokenStats | null; }

function Ring({ prompt, completion }: { prompt: number; completion: number }) {
  const total = prompt + completion || 1;
  const r = 34, circ = 2 * Math.PI * r;
  const pDash = ((prompt / total) * circ).toFixed(1);
  const cDash = ((completion / total) * circ).toFixed(1);
  const offset = (circ * 0.25).toFixed(1);
  const cOffset = (circ * 0.25 - (prompt / total) * circ).toFixed(1);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
      <svg width="90" height="90" viewBox="0 0 90 90">
        <circle cx="45" cy="45" r={r} fill="none" stroke="rgba(99,102,241,0.1)" strokeWidth="9" />
        <circle cx="45" cy="45" r={r} fill="none" stroke="#8b5cf6" strokeWidth="9"
          strokeDasharray={`${pDash} ${(circ - +pDash).toFixed(1)}`}
          strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dasharray .5s ease" }} />
        <circle cx="45" cy="45" r={r} fill="none" stroke="#06b6d4" strokeWidth="9"
          strokeDasharray={`${cDash} ${(circ - +cDash).toFixed(1)}`}
          strokeDashoffset={cOffset} strokeLinecap="round"
          style={{ transition: "stroke-dasharray .5s ease" }} />
        <text x="45" y="42" textAnchor="middle" fontSize="9" fill="#4a5568">total</text>
        <text x="45" y="56" textAnchor="middle" fontSize="11" fontWeight="700" fill="#f0f4ff">
          {(prompt + completion).toLocaleString()}
        </text>
      </svg>
      <div style={{ display: "flex", gap: 12, fontSize: 11 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 5, color: "#a78bfa" }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#8b5cf6", display: "inline-block" }} />
          Prompt ({((prompt / total) * 100).toFixed(0)}%)
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 5, color: "#22d3ee" }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#06b6d4", display: "inline-block" }} />
          Completion
        </span>
      </div>
    </div>
  );
}

function Card({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="glass" style={{
      padding: "10px 12px", display: "flex", flexDirection: "column", gap: 3,
      borderColor: `${color}28`,
    }}>
      <p style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-muted)" }}>
        {label}
      </p>
      <p style={{ fontSize: 20, fontWeight: 800, color }}>{value}</p>
      {sub && <p style={{ fontSize: 9, color: "var(--text-muted)" }}>{sub}</p>}
    </div>
  );
}

export default function TokenStats({ stats }: Props) {
  if (!stats) return (
    <div className="glass" style={{ padding: "14px", textAlign: "center" }}>
      <p style={{ fontSize: 11, color: "var(--text-muted)" }}>Run a query to start tracking.</p>
    </div>
  );

  const g = stats.global_stats.global;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>Token Usage & Cost</p>
        <span className="badge badge-purple" style={{ fontSize: 9 }}>{stats.global_stats.model}</span>
      </div>

      <div className="glass" style={{ padding: "14px", display: "flex", justifyContent: "center" }}>
        <Ring prompt={g.prompt_tokens} completion={g.completion_tokens} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
        <Card label="Total Tokens" value={g.total_tokens.toLocaleString()} color="#8b5cf6" />
        <Card label="API Calls"    value={g.call_count}                    color="#06b6d4" />
        <Card label="Est. Cost"    value={`$${g.estimated_cost_usd.toFixed(5)}`} sub="Free tier" color="#22c55e" />
        <Card label="Sessions"     value={stats.global_stats.active_sessions} color="#f472b6" />
      </div>

      <div style={{
        borderRadius: 10, padding: "8px 10px", fontSize: 10, lineHeight: 1.6,
        background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.14)",
        color: "var(--text-muted)",
      }}>
        <strong style={{ color: "#a78bfa" }}>Pricing:</strong>{" "}
        ${stats.global_stats.pricing.input_per_1m_tokens_usd}/M in ·{" "}
        ${stats.global_stats.pricing.output_per_1m_tokens_usd}/M out
      </div>
    </div>
  );
}
