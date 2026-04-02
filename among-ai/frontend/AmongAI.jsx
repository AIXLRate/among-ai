import { useState, useRef, useEffect } from "react"

// ── hana al Config and 3mlt email we 5t mno al api da mmkn tdef models aw api mn LLM tany brahtk ──────────────────────────────
const GROQ_KEY = "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"
const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

const CREW = [
  { id: "llama-3.3-70b-versatile", name: "LLAMA 70B",   role: "The Brain",   color: "#FF4655", dark: "#7A1520", glow: "rgba(255,70,85,0.25)" },
  { id: "mixtral-8x7b-32768",      name: "MIXTRAL",     role: "The Expert",  color: "#2E86DE", dark: "#134070", glow: "rgba(46,134,222,0.25)" },
  { id: "gemma2-9b-it",            name: "GEMMA 2",     role: "The Analyst", color: "#FFCB2F", dark: "#7A5800", glow: "rgba(255,203,47,0.25)" },
  { id: "llama-3.1-8b-instant",    name: "LLAMA 8B",    role: "The Quick",   color: "#26D07C", dark: "#0C6035", glow: "rgba(38,208,124,0.25)" },
]

const STARS = Array.from({ length: 150 }, (_, i) => ({
  id: i,
  x: ((i * 137.508) % 100).toFixed(3),
  y: ((i * 89.334) % 100).toFixed(3),
  size: (0.4 + (i % 4) * 0.45).toFixed(1),
  delay: ((i % 8) * 0.4).toFixed(1),
  dur: (2.5 + (i % 5) * 0.6).toFixed(1),
}))

// ── da al Groq Calls ────────────────────────────────────────────────────────────────
async function groqCall(model, messages, maxTokens = 700) {
  const r = await fetch(GROQ_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${GROQ_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model, messages, max_tokens: maxTokens, temperature: 0.7 }),
  })
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    throw new Error(e?.error?.message || `Groq error ${r.status}`)
  }
  return (await r.json()).choices[0].message.content
}
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
async function runDebate(question) {
  const answers = await Promise.all(
    CREW.map(c => groqCall(c.id, [{ role: "user", content: question }]))
  )
  const judgeLines = CREW.map((c, i) => `[${i}] ${c.name}:\n${answers[i]}`).join("\n\n---\n\n")
  const judgeText = await groqCall(
    "llama-3.3-70b-versatile",
    [
      { role: "system", content: "You are a judge. Respond with valid JSON only. No markdown, no text outside JSON." },
      { role: "user", content: `Judge these AI responses to: "${question}"\n\n${judgeLines}\n\nRespond ONLY with: {"winner":0,"scores":[90,80,75,70],"reason":"one sentence"}` },
    ],
    180
  )
  let verdict = { winner: 0, scores: [85, 75, 70, 65], reason: "Best overall response." }
  try {
    const m = judgeText.match(/\{[\s\S]*?\}/)
    if (m) verdict = { ...verdict, ...JSON.parse(m[0]) }
  } catch (_) {}
  return {
    responses: CREW.map((c, i) => ({ ...c, answer: answers[i], score: verdict.scores?.[i] ?? 70 })),
    winner: Math.min(Math.max(Number(verdict.winner) || 0, 0), 3),
    reason: verdict.reason || "",
  }
}

// ── da Sub-components ────────────────────────────────────────────────────────────

function Crewmate({ color, dark, size = 40 }) {
  return (
    <svg viewBox="0 0 52 78" width={size} height={size * 1.5} style={{ display: "block", flexShrink: 0 }}>
      <rect x="38" y="26" width="13" height="24" rx="5.5" fill={dark} />
      <ellipse cx="22" cy="54" rx="21" ry="23" fill={color} />
      <ellipse cx="22" cy="20" rx="19" ry="20" fill={color} />
      <path d="M6 12 Q22 1 38 12 Q39 31 22 33 Q5 31 6 12Z" fill="#C8EDFF" opacity="0.86" />
      <path d="M11 13 Q20 6 28 10" stroke="white" strokeWidth="2" fill="none" opacity="0.45" strokeLinecap="round" />
      <rect x="6"  y="71" width="12" height="7" rx="3.5" fill={dark} />
      <rect x="24" y="71" width="12" height="7" rx="3.5" fill={dark} />
    </svg>
  )
}

function ScoreBar({ score, color }) {
  const [w, setW] = useState(0)
  useEffect(() => { const t = setTimeout(() => setW(score), 120); return () => clearTimeout(t) }, [score])
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
      <div style={{ flex: 1, height: 3, background: "rgba(255,255,255,0.08)", borderRadius: 99, overflow: "hidden" }}>
        <div style={{ width: `${w}%`, height: "100%", background: color, transition: "width 1.3s cubic-bezier(0.4,0,0.2,1)", boxShadow: `0 0 8px ${color}` }} />
      </div>
      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", fontFamily: "monospace", minWidth: 26, textAlign: "right" }}>{score}</span>
    </div>
  )
}

function DebateLoading() {
  return (
    <div style={{ padding: "28px 0 16px", display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
      <div style={{ display: "flex", gap: 18, alignItems: "flex-end" }}>
        {CREW.map((c, i) => (
          <div key={c.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
            <div style={{ animation: `amBounce 0.65s ease-in-out ${i * 0.13}s infinite alternate` }}>
              <Crewmate color={c.color} dark={c.dark} size={34} />
            </div>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: c.color, boxShadow: `0 0 8px ${c.color}`, animation: `amBlink 0.65s ease-in-out ${i * 0.13}s infinite alternate` }} />
          </div>
        ))}
      </div>
      <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 10, letterSpacing: 3, animation: "amPulse 1.8s ease-in-out infinite" }}>
        CREW IS DEBATING...
      </div>
    </div>
  )
}

function AIMessage({ data }) {
  const [expanded, setExpanded] = useState(false)
  const w = data.responses[data.winner]
  const others = data.responses.filter((_, i) => i !== data.winner)
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, animation: "amSlide 0.4s ease" }}>
      {/* Divider */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, color: "rgba(255,255,255,0.22)", fontSize: 9, letterSpacing: 2.5 }}>
        <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
        🚨 EMERGENCY MEETING CONCLUDED
        <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
      </div>

      {/* Winner Card */}
      <div style={{
        border: `1.5px solid ${w.color}`,
        borderRadius: 18, padding: "22px 20px 18px",
        background: `linear-gradient(135deg, ${w.color}10 0%, ${w.color}04 100%)`,
        boxShadow: `0 0 40px ${w.glow}, 0 4px 30px rgba(0,0,0,0.4)`,
        position: "relative",
      }}>
        <div style={{
          position: "absolute", top: -13, left: 18,
          background: w.color, color: "#080B14",
          padding: "3px 14px", borderRadius: 99,
          fontSize: 9, fontWeight: 800, letterSpacing: 2,
          fontFamily: "'Righteous', cursive",
        }}>★ BEST ANSWER</div>

        <div style={{ display: "flex", alignItems: "flex-start", gap: 14, marginBottom: 16 }}>
          <div style={{ filter: `drop-shadow(0 0 8px ${w.color}80)` }}>
            <Crewmate color={w.color} dark={w.dark} size={48} />
          </div>
          <div style={{ flex: 1, paddingTop: 2 }}>
            <div style={{ color: w.color, fontWeight: 700, fontSize: 14, letterSpacing: 1.5, marginBottom: 2 }}>{w.name}</div>
            <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 11, marginBottom: 8 }}>{w.role}</div>
            <ScoreBar score={w.score} color={w.color} />
          </div>
        </div>

        <div style={{ color: "rgba(255,255,255,0.88)", fontSize: 14.5, lineHeight: 1.78, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {w.answer}
        </div>

        {data.reason && (
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${w.color}20`, color: "rgba(255,255,255,0.3)", fontSize: 11, fontStyle: "italic", letterSpacing: 0.3 }}>
            🗳 Judge: "{data.reason}"
          </div>
        )}
      </div>

      {/* Toggle Button */}
      <button onClick={() => setExpanded(e => !e)} style={{
        background: expanded ? "rgba(255,255,255,0.04)" : "none",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 12, padding: "10px 16px",
        color: "rgba(255,255,255,0.38)", cursor: "pointer",
        fontSize: 10, letterSpacing: 1.8, transition: "all 0.2s",
        width: "100%", fontFamily: "'Nunito', sans-serif",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
      }}>
        {expanded ? "▲ HIDE" : "▼ SEE ALL"} CREW RESPONSES
        <span style={{ opacity: 0.5 }}>({others.length})</span>
      </button>

      {/* Other Responses */}
      {expanded && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {others.map(r => (
            <div key={r.id} style={{
              border: `1px solid ${r.color}30`,
              borderRadius: 14, padding: "14px 16px",
              background: `${r.color}06`,
              animation: "amSlide 0.3s ease",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <Crewmate color={r.color} dark={r.dark} size={34} />
                <div style={{ flex: 1 }}>
                  <div style={{ color: r.color, fontWeight: 700, fontSize: 12, letterSpacing: 1.2, marginBottom: 4 }}>{r.name}</div>
                  <ScoreBar score={r.score} color={r.color} />
                </div>
              </div>
              <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, lineHeight: 1.72, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {r.answer}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── da al Main App ya hoda ──────────────────────────────────────────────────────────────────
export default function AmongAI() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    const link = document.createElement("link")
    link.rel = "stylesheet"
    link.href = "https://fonts.googleapis.com/css2?family=Righteous&family=Nunito:wght@400;600;700;800&display=swap"
    document.head.appendChild(link)
    const s = document.createElement("style")
    s.textContent = `
      @keyframes amBounce { from{transform:translateY(0)} to{transform:translateY(-11px)} }
      @keyframes amBlink  { from{opacity:1} to{opacity:0.15} }
      @keyframes amPulse  { 0%,100%{opacity:.28} 50%{opacity:.9} }
      @keyframes amTwinkle{ 0%,100%{opacity:.15} 50%{opacity:.85} }
      @keyframes amSlide  { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
      @keyframes amFloat  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
      * { box-sizing: border-box; }
      ::-webkit-scrollbar { width: 4px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
    `
    document.head.appendChild(s)
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  async function send() {
    const q = input.trim()
    if (!q || loading) return
    setInput("")
    setLoading(true)
    setMessages(prev => [...prev, { type: "user", text: q }, { type: "loading" }])
    try {
      const result = await runDebate(q)
      setMessages(prev => [...prev.slice(0, -1), { type: "ai", ...result }])
    } catch (err) {
      setMessages(prev => [...prev.slice(0, -1), { type: "error", text: err.message }])
    }
    setLoading(false)
  }

  return (
    <div style={{ minHeight: "100vh", background: "#080B14", color: "#fff", fontFamily: "'Nunito', sans-serif", display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>

      {/* ── Starfield ── */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0 }}>
        {STARS.map(s => (
          <div key={s.id} style={{
            position: "absolute", left: `${s.x}%`, top: `${s.y}%`,
            width: `${s.size}px`, height: `${s.size}px`,
            borderRadius: "50%", background: "white",
            animation: `amTwinkle ${s.dur}s ease-in-out ${s.delay}s infinite`,
          }} />
        ))}
        {/* Subtle space gradient */}
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 20% 30%, rgba(46,134,222,0.04) 0%, transparent 60%), radial-gradient(ellipse at 80% 70%, rgba(255,70,85,0.04) 0%, transparent 60%)" }} />
      </div>

      {/* ── Header ── */}
      <header style={{
        position: "sticky", top: 0, zIndex: 20,
        padding: "10px 20px",
        background: "rgba(8,11,20,0.94)", backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        display: "flex", alignItems: "center", gap: 14,
      }}>
        <div style={{ display: "flex", gap: 3 }}>
          {CREW.map(c => (
            <div key={c.id} style={{ filter: `drop-shadow(0 0 4px ${c.color}60)` }}>
              <Crewmate color={c.color} dark={c.dark} size={18} />
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontFamily: "'Righteous', cursive", fontSize: 17, letterSpacing: 3, lineHeight: 1.1 }}>
            AMONG<span style={{ color: "#C5FF2A" }}>·AI</span>
          </div>
          <div style={{ fontSize: 8, color: "rgba(255,255,255,0.28)", letterSpacing: 2 }}>4 CREWMATES · 1 WINNER</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 5, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {CREW.map(c => (
            <div key={c.id} title={c.role} style={{
              fontSize: 8, padding: "2px 9px", borderRadius: 99,
              border: `1px solid ${c.color}45`, color: c.color,
              fontWeight: 700, letterSpacing: 1,
            }}>{c.name}</div>
          ))}
        </div>
      </header>

      {/* ── Messages ── */}
      <main style={{ flex: 1, overflowY: "auto", padding: "24px 20px 8px", position: "relative", zIndex: 1 }}>
        <div style={{ maxWidth: 740, margin: "0 auto" }}>

          {/* Empty state */}
          {messages.length === 0 && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "70vh", gap: 28, textAlign: "center" }}>
              <div style={{ display: "flex", gap: 12 }}>
                {CREW.map((c, i) => (
                  <div key={c.id} style={{ animation: `amFloat ${1.8 + i * 0.3}s ease-in-out ${i * 0.2}s infinite`, filter: `drop-shadow(0 0 10px ${c.color}60)` }}>
                    <Crewmate color={c.color} dark={c.dark} size={52} />
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontFamily: "'Righteous', cursive", fontSize: 38, letterSpacing: 5, lineHeight: 1, marginBottom: 8 }}>
                  AMONG<span style={{ color: "#C5FF2A" }}>·AI</span>
                </div>
                <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 13, lineHeight: 1.8, maxWidth: 320 }}>
                  Ask anything. All 4 crewmates answer.<br/>
                  The best answer wins the vote.
                </div>
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
                {["What is black hole?", "How does GPS work?", "Explain quantum computing"].map(q => (
                  <button key={q} onClick={() => { setInput(q) }} style={{
                    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)",
                    borderRadius: 10, padding: "8px 14px", color: "rgba(255,255,255,0.5)",
                    cursor: "pointer", fontSize: 12, fontFamily: "'Nunito', sans-serif",
                    transition: "all 0.2s",
                  }}>{q}</button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          <div style={{ display: "flex", flexDirection: "column", gap: 22, paddingBottom: 24 }}>
            {messages.map((msg, i) => {
              if (msg.type === "user") return (
                <div key={i} style={{ display: "flex", justifyContent: "flex-end", animation: "amSlide 0.3s ease" }}>
                  <div style={{
                    background: "rgba(197,255,42,0.08)",
                    border: "1px solid rgba(197,255,42,0.18)",
                    borderRadius: "18px 18px 4px 18px",
                    padding: "12px 18px",
                    maxWidth: "72%", fontSize: 15, lineHeight: 1.65,
                    color: "rgba(255,255,255,0.92)",
                  }}>{msg.text}</div>
                </div>
              )
              if (msg.type === "loading") return <DebateLoading key={i} />
              if (msg.type === "error") return (
                <div key={i} style={{
                  border: "1px solid rgba(255,70,85,0.3)", borderRadius: 12,
                  padding: "12px 16px", background: "rgba(255,70,85,0.06)",
                  color: "#FF6B7A", fontSize: 13, animation: "amSlide 0.3s ease",
                }}>⚠ {msg.text}</div>
              )
              if (msg.type === "ai") return <AIMessage key={i} data={msg} />
              return null
            })}
          </div>
          <div ref={bottomRef} />
        </div>
      </main>

      {/* ── Input ── */}
      <div style={{
        position: "sticky", bottom: 0, zIndex: 20,
        padding: "12px 20px 16px",
        background: "rgba(8,11,20,0.96)", backdropFilter: "blur(20px)",
        borderTop: "1px solid rgba(255,255,255,0.05)",
      }}>
        <div style={{ maxWidth: 740, margin: "0 auto" }}>
          <div style={{
            display: "flex", gap: 8, alignItems: "center",
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.09)",
            borderRadius: 16, padding: "4px 4px 4px 16px",
            transition: "border-color 0.2s",
          }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
              placeholder="Ask the crew anything..."
              disabled={loading}
              style={{
                flex: 1, background: "none", border: "none", outline: "none",
                color: "rgba(255,255,255,0.9)", fontSize: 14.5,
                fontFamily: "'Nunito', sans-serif", padding: "10px 0",
              }}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              style={{
                padding: "10px 24px", borderRadius: 12, border: "none",
                background: !loading && input.trim() ? "#C5FF2A" : "rgba(255,255,255,0.06)",
                color: !loading && input.trim() ? "#080B14" : "rgba(255,255,255,0.22)",
                fontWeight: 800, fontSize: 12, letterSpacing: 1.2,
                cursor: !loading && input.trim() ? "pointer" : "default",
                transition: "all 0.2s", fontFamily: "'Nunito', sans-serif",
                boxShadow: !loading && input.trim() ? "0 0 16px rgba(197,255,42,0.3)" : "none",
              }}
            >
              {loading ? "···" : "SEND →"}
            </button>
          </div>
          <div style={{ textAlign: "center", marginTop: 8, fontSize: 8.5, color: "rgba(255,255,255,0.16)", letterSpacing: 1.5 }}>
            POWERED BY GROQ · {CREW.map(c => c.name).join(" · ")}
          </div>
        </div>
      </div>
    </div>
  )
}
