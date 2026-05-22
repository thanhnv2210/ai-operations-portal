import { useEffect, useRef, useState } from 'react'
import { Bot, Send, Sparkles, Trash2, TriangleAlert, Zap } from 'lucide-react'
import { useChat, useInsights } from '@/hooks/useAi'

function toIso(d: Date) { return d.toISOString().slice(0, 16) }

const defaultFrom = toIso(new Date(Date.now() - 90 * 86_400_000))
const defaultTo   = toIso(new Date())

const SUGGESTED = [
  'Summarise the current operational health',
  'Why is the failure rate elevated for TELEPIN?',
  'Which services have the highest transaction volume?',
  'Explain the most common error codes',
  'Are there any unusual patterns in the last 30 days?',
]

const HEALTH_COLORS = {
  good:     'bg-green-500/15 text-green-400 ring-green-500/20',
  warning:  'bg-amber-500/15 text-amber-400 ring-amber-500/20',
  critical: 'bg-red-500/15 text-red-400 ring-red-500/20',
}

const SEVERITY_COLORS = {
  low:    'border-l-blue-400',
  medium: 'border-l-amber-400',
  high:   'border-l-red-400',
}

export function AiAssistant() {
  const [input, setInput] = useState('')
  const [fromDate, setFromDate] = useState(defaultFrom)
  const [toDate, setToDate]     = useState(defaultTo)
  const [activeTab, setActiveTab] = useState<'chat' | 'insights'>('chat')

  const { messages, streaming, send, clear } = useChat()
  const { data: insights, loading: insightsLoading, error: insightsError, generate } = useInsights()

  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend() {
    if (!input.trim() || streaming) return
    send(input.trim(), fromDate, toDate)
    setInput('')
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-5xl space-y-5">
        <div className="flex items-center gap-3">
          <Bot size={24} className="text-primary" />
          <h1 className="text-2xl font-bold text-foreground">AI Assistant</h1>
        </div>

        {/* Date context */}
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
          <span className="text-xs font-semibold uppercase tracking-widest text-faint">Context period</span>
          <input type="datetime-local" value={fromDate} onChange={e => setFromDate(e.target.value)}
            className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
          <span className="text-faint">→</span>
          <input type="datetime-local" value={toDate} onChange={e => setToDate(e.target.value)}
            className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-border">
          {(['chat', 'insights'] as const).map(t => (
            <button key={t} onClick={() => setActiveTab(t)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors capitalize ${
                activeTab === t ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}>
              {t === 'chat' ? <Bot size={14} /> : <Sparkles size={14} />}
              {t === 'chat' ? 'Chat' : 'Insights'}
            </button>
          ))}
        </div>

        {/* ── CHAT ── */}
        {activeTab === 'chat' && (
          <div className="flex flex-col gap-4">
            {/* Message history */}
            <div className="rounded-xl border border-border bg-card min-h-80 max-h-[60vh] overflow-y-auto p-5 space-y-4">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-64 gap-4 text-muted-foreground">
                  <Bot size={40} className="text-faint" />
                  <p className="text-sm">Ask anything about your operations</p>
                  <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                    {SUGGESTED.map(q => (
                      <button key={q} onClick={() => { send(q, fromDate, toDate) }}
                        className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors">
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/20">
                      <Bot size={14} className="text-primary" />
                    </div>
                  )}
                  <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-sm'
                      : 'bg-muted text-foreground rounded-bl-sm'
                  }`}>
                    {msg.content}
                    {msg.streaming && <span className="ml-1 inline-block h-3 w-0.5 animate-pulse bg-current" />}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Input row */}
            <div className="flex gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Ask about failures, trends, anomalies…"
                disabled={streaming}
                className="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-sm text-foreground placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
              />
              <button onClick={handleSend} disabled={streaming || !input.trim()}
                className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40 transition-opacity">
                <Send size={15} />
              </button>
              {messages.length > 0 && (
                <button onClick={clear} title="Clear chat"
                  className="rounded-xl border border-border p-2.5 text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors">
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          </div>
        )}

        {/* ── INSIGHTS ── */}
        {activeTab === 'insights' && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <button onClick={() => generate(fromDate, toDate)} disabled={insightsLoading}
                className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity">
                <Zap size={15} />
                {insightsLoading ? 'Generating…' : 'Generate Insights'}
              </button>
              <p className="text-sm text-muted-foreground">AI analysis of your current operational data</p>
            </div>

            {insightsError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {insightsError}
              </div>
            )}

            {insightsLoading && (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-subtle" />)}
              </div>
            )}

            {!insightsLoading && insights && (
              <div className="space-y-4">
                {/* Summary card */}
                <div className="rounded-xl border border-border bg-card p-5">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm leading-relaxed text-foreground">{insights.summary}</p>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${HEALTH_COLORS[insights.health] ?? HEALTH_COLORS.warning}`}>
                      {insights.health.toUpperCase()}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-faint">Period: {insights.context_period}</p>
                </div>

                {/* Anomalies */}
                {insights.anomalies.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-5 space-y-3">
                    <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-faint">
                      <TriangleAlert size={13} /> Anomalies
                    </h3>
                    {insights.anomalies.map((a, i) => (
                      <div key={i} className={`border-l-2 pl-3 ${SEVERITY_COLORS[a.severity as keyof typeof SEVERITY_COLORS] ?? 'border-l-border'}`}>
                        <p className="text-sm font-medium text-foreground">{a.title}</p>
                        <p className="text-sm text-muted-foreground">{a.detail}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Recommendations */}
                {insights.recommendations.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-5 space-y-3">
                    <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-faint">
                      <Zap size={13} /> Recommendations
                    </h3>
                    {insights.recommendations.map((r, i) => (
                      <div key={i} className="flex gap-3">
                        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">{i + 1}</span>
                        <div>
                          <p className="text-sm font-medium text-foreground">{r.action}</p>
                          <p className="text-sm text-muted-foreground">{r.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
