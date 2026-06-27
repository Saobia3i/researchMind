"use client";

import type { ResearchResponse, AgentResponse, TeamResearchResponse } from "@/lib/api";

/* ── Inline markdown renderer (no external deps) ── */
function renderMd(text: string) {
  return text.split("\n").map((line, i) => {
    if (line.startsWith("# "))   return <h1 key={i} style={{ fontSize:"1.4em", fontWeight:800, color:"var(--text-primary)", margin:"1.2em 0 0.4em" }}>{line.slice(2)}</h1>;
    if (line.startsWith("## "))  return <h2 key={i} style={{ fontSize:"1.18em", fontWeight:700, color:"var(--text-primary)", margin:"1em 0 0.3em" }}>{line.slice(3)}</h2>;
    if (line.startsWith("### ")) return <h3 key={i} style={{ fontSize:"1.04em", fontWeight:600, color:"#c4b5fd", margin:"0.8em 0 0.2em" }}>{line.slice(4)}</h3>;
    if (line.startsWith("---"))  return <hr key={i} style={{ border:"none", borderTop:"1px solid rgba(99,102,241,0.2)", margin:"1.2em 0" }} />;
    if (/^[\-\*\•] /.test(line)) return (
      <div key={i} style={{ display:"flex", gap:8, margin:"3px 0" }}>
        <span style={{ color:"#8b5cf6", flexShrink:0, marginTop:2 }}>▸</span>
        <span style={{ fontSize:13, color:"var(--text-secondary)", lineHeight:1.7 }}>{fmt(line.slice(2))}</span>
      </div>
    );
    if (/^\d+\. /.test(line)) return (
      <div key={i} style={{ display:"flex", gap:8, margin:"3px 0" }}>
        <span style={{ color:"#6366f1", flexShrink:0, fontSize:12, marginTop:2 }}>{line.match(/^\d+/)?.[0]}.</span>
        <span style={{ fontSize:13, color:"var(--text-secondary)", lineHeight:1.7 }}>{fmt(line.replace(/^\d+\. /,""))}</span>
      </div>
    );
    if (line.trim() === "") return <div key={i} style={{ height:"0.4em" }} />;
    return <p key={i} style={{ fontSize:13, color:"var(--text-secondary)", lineHeight:1.8, margin:"0.3em 0" }}>{fmt(line)}</p>;
  });
}

function fmt(t: string): React.ReactNode {
  const parts = t.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**"))
      return <strong key={i} style={{ color:"var(--text-primary)", fontWeight:600 }}>{p.slice(2,-2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`"))
      return <code key={i} style={{ background:"rgba(139,92,246,0.12)", color:"#a78bfa", borderRadius:4, padding:"2px 6px", fontSize:"0.88em" }}>{p.slice(1,-1)}</code>;
    const lm = p.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (lm) return <a key={i} href={lm[2]} target="_blank" rel="noopener noreferrer" style={{ color:"#60a5fa" }}>{lm[1]}</a>;
    return p;
  });
}

/* ── Confidence bar ── */
function ConfBar({ v }: { v: number }) {
  const pct = Math.min(100, Math.max(0, v * 100));
  const c = pct >= 75 ? "#22c55e" : pct >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
      <div className="progress-bar" style={{ flex:1 }}>
        <div className="progress-bar-fill" style={{ width:`${pct}%`, background:c }} />
      </div>
      <span style={{ fontSize:11, fontWeight:700, color:c, minWidth:34 }}>{pct.toFixed(0)}%</span>
    </div>
  );
}

/* ── Section label ── */
const SL = ({ t }: { t: string }) => (
  <p style={{ fontSize:9, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.08em", color:"var(--text-muted)", marginBottom:6 }}>{t}</p>
);

/* ── Research card ── */
function ResearchCard({ d }: { d: ResearchResponse }) {
  return (
    <div className="gradient-border fade-in">
      <div className="glass" style={{ borderRadius:16, padding:"22px 24px", display:"flex", flexDirection:"column", gap:16 }}>
        <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:12 }}>
          <h2 style={{ fontSize:18, fontWeight:800, color:"var(--text-primary)", lineHeight:1.3 }}>{d.title}</h2>
          <span className="badge badge-purple" style={{ flexShrink:0 }}>Quick Research</span>
        </div>

        <div><SL t="Confidence" /><ConfBar v={d.confidence} /></div>
        <div>
          <SL t="Summary" />
          <p style={{ fontSize:13, color:"var(--text-secondary)", lineHeight:1.8 }}>{d.summary}</p>
        </div>
        <div>
          <SL t="Key Points" />
          <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
            {d.key_points.map((pt, i) => (
              <div key={i} style={{ display:"flex", gap:8, alignItems:"flex-start" }}>
                <span style={{ color:"#8b5cf6", flexShrink:0, marginTop:2 }}>▸</span>
                <span style={{ fontSize:13, color:"var(--text-secondary)", lineHeight:1.7 }}>{pt}</span>
              </div>
            ))}
          </div>
        </div>
        {d.suggested_followups.length > 0 && (
          <div>
            <SL t="Follow-ups" />
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {d.suggested_followups.map((f, i) => (
                <span key={i} className="badge badge-cyan" style={{ textTransform:"none", fontWeight:400, fontSize:11 }}>{f}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Agent card ── */
function AgentCard({ d }: { d: AgentResponse }) {
  return (
    <div className="glass fade-in" style={{ padding:"18px 20px", display:"flex", flexDirection:"column", gap:12 }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <span className="badge badge-purple">ReAct Agent</span>
        <span style={{ fontSize:11, color:"var(--text-muted)" }}>{d.usage.total_tokens.toLocaleString()} tokens</span>
      </div>
      <div className="prose-dark">{renderMd(d.final_answer)}</div>
    </div>
  );
}

/* ── Team card ── */
function TeamCard({ d }: { d: TeamResearchResponse }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:12 }} className="fade-in">
      <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
        {d.steps.map((s, i) => (
          <span key={i} className="badge badge-purple" style={{ textTransform:"capitalize" }}>{s}</span>
        ))}
      </div>
      <details className="glass" style={{ overflow:"hidden", borderRadius:12 }}>
        <summary style={{ padding:"11px 16px", cursor:"pointer", fontSize:13, fontWeight:600, color:"var(--text-secondary)", listStyle:"none" }}>
          📋 Research Plan
        </summary>
        <div style={{ padding:"0 16px 14px", borderTop:"1px solid rgba(99,102,241,0.12)" }} className="prose-dark">
          {renderMd(d.plan)}
        </div>
      </details>
      <div className="gradient-border">
        <div className="glass" style={{ borderRadius:16, padding:"20px 22px" }}>
          <div style={{ display:"flex", gap:6, marginBottom:14 }}>
            <span className="badge badge-green">Final Report</span>
            <span className="badge badge-pink">LangGraph</span>
          </div>
          <div className="prose-dark">{renderMd(d.final_report)}</div>
        </div>
      </div>
    </div>
  );
}

/* ── Main export ── */
interface Props {
  mode: string;
  data: ResearchResponse | AgentResponse | TeamResearchResponse | null;
  error: string | null;
}

export default function ResultCard({ mode, data, error }: Props) {
  if (error) return (
    <div className="glass fade-in" style={{
      padding:"16px 18px",
      borderColor:"rgba(239,68,68,0.3)",
      background:"rgba(239,68,68,0.06)",
      display:"flex", flexDirection:"column", gap:4,
    }}>
      <p style={{ fontSize:12, fontWeight:700, color:"#f87171" }}>⚠ Error</p>
      <p style={{ fontSize:12, color:"var(--text-secondary)" }}>{error}</p>
    </div>
  );

  if (!data) return null;
  if (mode === "research") return <ResearchCard d={data as ResearchResponse} />;
  if (mode === "agent")    return <AgentCard    d={data as AgentResponse} />;
  if (mode === "team")     return <TeamCard     d={data as TeamResearchResponse} />;
  return null;
}
