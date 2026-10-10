import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Send, Loader2, CheckCircle2, XCircle, Clock,
  Zap, Search, BrainCircuit, ScanText, ChevronDown, ChevronUp,
  Sparkles, AlertTriangle, RefreshCw,
} from 'lucide-react'

// ─── constants ──────────────────────────────────────────────────────────────

const API_BASE = ''  // proxied by Vite in dev; set to http://localhost:8000 for prod

const COMPLEXITY_COLOR = {
  simple:   '#00d8a0',
  moderate: '#f0a040',
  complex:  '#f05060',
}

const TYPE_ICON = {
  retrieval: Search,
  general:   BrainCircuit,
}

const STATUS_META = {
  idle:    { label: 'Idle',     color: '#7a8099', Icon: Clock },
  running: { label: 'Running',  color: '#6c63ff', Icon: Loader2 },
  done:    { label: 'Done',     color: '#00d8a0', Icon: CheckCircle2 },
  error:   { label: 'Error',    color: '#f05060', Icon: XCircle },
}

// ─── tiny helpers ────────────────────────────────────────────────────────────

function initials(name = '') {
  return name.replace('_', ' ').split(' ').map(w => w[0]?.toUpperCase() ?? '').join('').slice(0, 2) || '?'
}

function hue(name = '') {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff
  return Math.abs(h) % 360
}

// ─── AgentCard ───────────────────────────────────────────────────────────────

function AgentCard({ agent }) {
  const [open, setOpen] = useState(false)
  const { label, color, Icon } = STATUS_META[agent.status] ?? STATUS_META.idle
  const TypeIcon = TYPE_ICON[agent.type] ?? BrainCircuit
  const bg = `hsl(${hue(agent.name)}, 55%, 18%)`
  const border = `hsl(${hue(agent.name)}, 55%, 30%)`
  const spinning = agent.status === 'running'

  return (
    <div style={{
      background: 'var(--surface)',
      border: `1.5px solid ${agent.status === 'running' ? color : 'var(--border)'}`,
      borderRadius: 'var(--radius)',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      boxShadow: agent.status === 'running' ? `0 0 16px ${color}44` : 'var(--shadow)',
      transition: 'all .3s ease',
      minWidth: 0,
    }}>
      {/* header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {/* avatar */}
        <div style={{
          width: 40, height: 40, borderRadius: 10, flexShrink: 0,
          background: bg, border: `1.5px solid ${border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: 14, letterSpacing: '.5px',
          color: `hsl(${hue(agent.name)}, 80%, 75%)`,
        }}>
          {initials(agent.name)}
        </div>

        {/* name + role */}
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {agent.name}
          </div>
          <div style={{ color: 'var(--muted)', fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {agent.role}
          </div>
        </div>

        {/* type badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 4,
          background: 'var(--surface2)', borderRadius: 6,
          padding: '3px 8px', fontSize: 11, color: 'var(--muted)', flexShrink: 0,
        }}>
          <TypeIcon size={11} />
          {agent.type}
        </div>
      </div>

      {/* tools used badges */}
      {agent.tools_used?.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {agent.tools_used.map(t => (
            <span key={t} style={{
              background: '#6c63ff22', border: '1px solid #6c63ff44',
              color: '#a09af0', borderRadius: 5, padding: '2px 7px', fontSize: 11,
            }}>
              🔧 {t}
            </span>
          ))}
        </div>
      )}

      {/* status pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icon
          size={14}
          color={color}
          style={spinning ? { animation: 'spin 1s linear infinite' } : {}}
        />
        <span style={{ fontSize: 12, color }}>{label}</span>
      </div>

      {/* result (collapsible) */}
      {agent.result && (
        <div>
          <button
            onClick={() => setOpen(o => !o)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 4,
              color: 'var(--muted)', fontSize: 12, padding: 0,
            }}
          >
            {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {open ? 'Hide output' : 'Show output'}
          </button>
          {open && (
            <pre style={{
              marginTop: 8,
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '10px 12px',
              fontSize: 12,
              color: 'var(--text)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: 280,
              overflowY: 'auto',
              lineHeight: 1.5,
            }}>
              {agent.result}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

// ─── AgentGrid (Munderiffic board) ───────────────────────────────────────────

function AgentGrid({ agents, complexity }) {
  if (!agents.length) return null
  const ccol = COMPLEXITY_COLOR[complexity] ?? 'var(--accent)'

  return (
    <section style={{ marginTop: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <span style={{
          background: ccol + '22', border: `1px solid ${ccol}55`,
          color: ccol, borderRadius: 6, padding: '3px 10px', fontSize: 12, fontWeight: 700,
        }}>
          {complexity}
        </span>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>
          {agents.length} agent{agents.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Munderiffic-style grid: auto-fill cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
        gap: 14,
      }}>
        {agents.map(a => <AgentCard key={a.name} agent={a} />)}
      </div>
    </section>
  )
}

// ─── FinalAnswer ─────────────────────────────────────────────────────────────

function FinalAnswer({ text, errors }) {
  if (!text) return null
  return (
    <div style={{
      marginTop: 24,
      background: 'var(--surface)',
      border: '1.5px solid var(--accent)',
      borderRadius: 'var(--radius)',
      padding: '20px 24px',
      boxShadow: '0 0 20px #6c63ff33',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <Sparkles size={18} color="var(--accent)" />
        <span style={{ fontWeight: 700, fontSize: 15 }}>Final Answer</span>
      </div>
      <div style={{
        fontSize: 14, lineHeight: 1.75, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        color: 'var(--text)',
      }}>
        {text}
      </div>

      {errors?.length > 0 && (
        <div style={{
          marginTop: 16,
          background: '#f0506018',
          border: '1px solid #f0506044',
          borderRadius: 8,
          padding: '10px 14px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--danger)', fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
            <AlertTriangle size={14} /> Workflow errors
          </div>
          {errors.map((e, i) => (
            <div key={i} style={{ fontSize: 12, color: '#f08090', paddingLeft: 20 }}>• {e}</div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── PromptInput ─────────────────────────────────────────────────────────────

function PromptInput({ onSubmit, disabled }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim()) onSubmit(value.trim())
    }
  }

  const submit = () => {
    if (value.trim()) { onSubmit(value.trim()); setValue('') }
  }

  // auto-resize
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [value])

  return (
    <div style={{
      display: 'flex', gap: 10, alignItems: 'flex-end',
      background: 'var(--surface)',
      border: '1.5px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '12px 14px',
      boxShadow: 'var(--shadow)',
    }}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Describe a task for Factory OS… (Enter to run, Shift+Enter for new line)"
        disabled={disabled}
        rows={1}
        style={{
          flex: 1,
          background: 'transparent',
          border: 'none',
          outline: 'none',
          color: 'var(--text)',
          fontSize: 14,
          resize: 'none',
          lineHeight: 1.6,
          fontFamily: 'inherit',
        }}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        title="Run (Enter)"
        style={{
          background: disabled || !value.trim() ? 'var(--surface2)' : 'var(--accent)',
          border: 'none',
          borderRadius: 9,
          width: 38, height: 38,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: disabled || !value.trim() ? 'not-allowed' : 'pointer',
          transition: 'background .2s',
          flexShrink: 0,
        }}
      >
        {disabled
          ? <Loader2 size={17} color="#7a8099" style={{ animation: 'spin 1s linear infinite' }} />
          : <Send size={17} color={value.trim() ? '#fff' : '#7a8099'} />}
      </button>
    </div>
  )
}

// ─── StatusBar ───────────────────────────────────────────────────────────────

function StatusBar({ phase, agentCount }) {
  const msgs = {
    idle:      null,
    planning:  '⚙️  Planning tasks…',
    executing: `🤖  Running ${agentCount} agent${agentCount !== 1 ? 's' : ''}…`,
    reviewing: '🔍  Synthesizing results…',
    done:      '✅  Done',
    error:     '❌  Workflow failed',
  }
  const msg = msgs[phase]
  if (!msg) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      color: phase === 'done' ? 'var(--accent2)' : phase === 'error' ? 'var(--danger)' : 'var(--muted)',
      fontSize: 13, marginTop: 14,
    }}>
      {phase === 'planning' || phase === 'executing' || phase === 'reviewing'
        ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
        : null}
      {msg}
    </div>
  )
}

// ─── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [phase, setPhase] = useState('idle')           // idle | planning | executing | reviewing | done | error
  const [agents, setAgents] = useState([])
  const [complexity, setComplexity] = useState('')
  const [answer, setAnswer] = useState('')
  const [errors, setErrors] = useState([])
  const [warning, setWarning] = useState('')
  const [prompt, setPrompt] = useState('')
  const bottomRef = useRef(null)
  const abortRef = useRef(null)

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [agents, answer, phase])

  const reset = useCallback(() => {
    setPhase('idle')
    setAgents([])
    setComplexity('')
    setAnswer('')
    setErrors([])
    setWarning('')
  }, [])

  const run = useCallback(async (userPrompt) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    reset()
    setPrompt(userPrompt)
    setPhase('planning')

    try {
      const resp = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userPrompt }),
        signal: ctrl.signal,
      })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      const processEvent = (raw) => {
        // raw is one SSE block: "event: xxx\ndata: yyy"
        const lines = raw.trim().split('\n')
        let event = '', dataStr = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim()
          if (line.startsWith('data: ')) dataStr = line.slice(6).trim()
        }
        if (!event || !dataStr) return
        let data
        try { data = JSON.parse(dataStr) } catch { return }

        if (event === 'planning') {
          setPhase('planning')
        } else if (event === 'plan_ready') {
          setComplexity(data.complexity)
          setAgents((data.tasks ?? []).map(t => ({
            name: t.name,
            role: t.role,
            type: t.type,
            status: 'idle',
            result: '',
          })))
          setPhase('executing')
        } else if (event === 'warning') {
          setWarning(data.message ?? '')
        } else if (event === 'agent_start') {
          setAgents(prev => prev.map(a => a.name === data.name ? { ...a, status: 'running' } : a))
        } else if (event === 'agent_done') {
          setAgents(prev => prev.map(a => a.name === data.name
            ? { ...a, status: data.success ? 'done' : 'error', result: data.result ?? '', tools_used: data.tools_used ?? [] }
            : a))
        } else if (event === 'reviewing') {
          setPhase('reviewing')
        } else if (event === 'done') {
          setAnswer(data.answer ?? '')
          setErrors(data.errors ?? [])
          setPhase('done')
        } else if (event === 'error') {
          setErrors([data.message ?? 'Unknown error'])
          setPhase('error')
        }
      }

      // Stream reader loop
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        // SSE events are separated by double newlines
        const parts = buf.split('\n\n')
        buf = parts.pop() ?? ''
        for (const part of parts) {
          if (part.trim()) processEvent(part)
        }
      }
      // flush remainder
      if (buf.trim()) processEvent(buf)

    } catch (err) {
      if (err.name === 'AbortError') return
      setErrors([String(err)])
      setPhase('error')
    }
  }, [reset])

  const canRun = phase === 'idle' || phase === 'done' || phase === 'error'

  return (
    <>
      {/* spin keyframe */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
      `}</style>

      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '0 16px 40px',
      }}>
        {/* ── Header ── */}
        <header style={{
          width: '100%', maxWidth: 900,
          padding: '32px 0 20px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 12,
              background: 'linear-gradient(135deg, #6c63ff, #00d8a0)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Zap size={20} color="#fff" />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 20, letterSpacing: '-.3px' }}>Factory OS</div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Multi-agent AI platform</div>
            </div>
          </div>

          {(phase === 'done' || phase === 'error') && (
            <button
              onClick={reset}
              style={{
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '7px 14px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6,
                color: 'var(--muted)', fontSize: 13,
              }}
            >
              <RefreshCw size={13} /> New task
            </button>
          )}
        </header>

        {/* ── Main content ── */}
        <main style={{ width: '100%', maxWidth: 900, flex: 1 }}>

          {/* Prompt display (after submission) */}
          {prompt && (
            <div style={{
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '14px 18px',
              fontSize: 14,
              color: 'var(--text)',
              lineHeight: 1.7,
              marginBottom: 4,
            }}>
              <span style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600 }}>TASK  </span>
              {prompt}
            </div>
          )}

          {/* Status bar */}
          <StatusBar phase={phase} agentCount={agents.length} />

          {/* Warning */}
          {warning && (
            <div style={{
              marginTop: 12, display: 'flex', alignItems: 'flex-start', gap: 8,
              background: '#f0a04018', border: '1px solid #f0a04044',
              borderRadius: 8, padding: '8px 12px', fontSize: 13, color: 'var(--warn)',
            }}>
              <AlertTriangle size={14} style={{ marginTop: 2, flexShrink: 0 }} />
              {warning}
            </div>
          )}

          {/* Agent board */}
          <AgentGrid agents={agents} complexity={complexity} />

          {/* Final answer */}
          <FinalAnswer text={answer} errors={errors} />

          {/* Error state (no answer) */}
          {phase === 'error' && !answer && errors.length > 0 && (
            <div style={{
              marginTop: 20, background: '#f0506018',
              border: '1px solid #f0506044', borderRadius: 'var(--radius)',
              padding: '16px 20px',
            }}>
              <div style={{ color: 'var(--danger)', fontWeight: 700, marginBottom: 8 }}>Workflow failed</div>
              {errors.map((e, i) => <div key={i} style={{ fontSize: 13, color: '#f08090' }}>• {e}</div>)}
            </div>
          )}

          <div ref={bottomRef} />
        </main>

        {/* ── Input bar (pinned at bottom when idle, inline otherwise) ── */}
        <div style={{
          position: 'sticky',
          bottom: 0,
          width: '100%',
          maxWidth: 900,
          paddingTop: 16,
          background: 'linear-gradient(to bottom, transparent, var(--bg) 40%)',
          paddingBottom: 8,
        }}>
          <PromptInput onSubmit={run} disabled={!canRun} />
          <div style={{ textAlign: 'center', color: 'var(--muted)', fontSize: 11, marginTop: 8 }}>
            Enter to run · Shift+Enter for new line
          </div>
        </div>
      </div>
    </>
  )
}
