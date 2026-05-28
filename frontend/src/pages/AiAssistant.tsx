import { useEffect, useRef, useState } from 'react'
import { Bot, ChevronDown, ChevronUp, Database, History, Loader2, Send, Sparkles, Trash2, TriangleAlert, X, Zap } from 'lucide-react'
import { MAX_CONTEXT_DAYS, MAX_MESSAGE_LEN, useChat, useInsights } from '@/hooks/useAi'
import { SQL_SUGGESTED, friendlyError, useTextToSql } from '@/hooks/useTextToSql'
import { useQueryHistory } from '@/hooks/useQueryHistory'
import { QueryHistoryPanel } from '@/components/QueryHistoryPanel'
import { toSgtIso } from '@/lib/sgt'

const defaultFrom = toSgtIso(new Date(Date.now() - 7 * 86_400_000))
const defaultTo   = toSgtIso(new Date())

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
  const [sqlInput, setSqlInput] = useState('')
  const [sqlExpanded, setSqlExpanded] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [fromDate, setFromDate] = useState(defaultFrom)
  const [toDate, setToDate]     = useState(defaultTo)
  const [activeTab, setActiveTab] = useState<'chat' | 'insights' | 'query'>('chat')

  const { messages, streaming, send, cancel, clear } = useChat()
  const { data: insights, loading: insightsLoading, error: insightsError, generate } = useInsights()
  const { status, sql, explanation, error: sqlError, streaming: sqlStreaming, ask, reset, cancel: cancelSql } = useTextToSql()
  const { entries: historyEntries, add: addHistory, toggleFavorite, remove: removeHistory, clear: clearHistory } = useQueryHistory()

  const bottomRef = useRef<HTMLDivElement>(null)
  const prevStreamingRef = useRef(false)

  // Save to history when a query completes successfully
  useEffect(() => {
    if (prevStreamingRef.current && !sqlStreaming && sql && !sqlError) {
      addHistory(sqlInput, sql)
    }
    prevStreamingRef.current = sqlStreaming
  }, [sqlStreaming, sql, sqlError, sqlInput, addHistory])

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
        {(() => {
          const days = Math.round((new Date(toDate).getTime() - new Date(fromDate).getTime()) / 86_400_000)
          const over = days > MAX_CONTEXT_DAYS
          return (
            <div className="rounded-xl border border-border bg-card px-4 py-3 space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-widest text-faint">Context period</span>
                <input type="datetime-local" value={fromDate} onChange={e => setFromDate(e.target.value)}
                  className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
                <span className="text-faint">→</span>
                <input type="datetime-local" value={toDate} onChange={e => setToDate(e.target.value)}
                  className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
                <span className={`text-xs ${over ? 'text-amber-400' : 'text-muted-foreground'}`}>
                  {days} day{days !== 1 ? 's' : ''}
                </span>
              </div>
              {over && (
                <p className="text-xs text-amber-400">
                  Range exceeds {MAX_CONTEXT_DAYS} days — the backend will automatically cap it to protect the production database.
                </p>
              )}
            </div>
          )
        })()}

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-border">
          {([
            { id: 'chat',     label: 'Chat',        Icon: Bot },
            { id: 'insights', label: 'Insights',    Icon: Sparkles },
            { id: 'query',    label: 'Text-to-SQL', Icon: Database },
          ] as const).map(({ id, label, Icon }) => (
            <button key={id} onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}>
              <Icon size={14} />
              {label}
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
            <div className="space-y-1">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value.slice(0, MAX_MESSAGE_LEN))}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                  placeholder="Ask about failures, trends, anomalies…"
                  disabled={streaming}
                  className="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-sm text-foreground placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
                />
                {streaming ? (
                  <button
                    onClick={cancel}
                    title="Cancel"
                    className="flex items-center gap-1.5 rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-subtle transition-colors"
                  >
                    <X size={15} /> Cancel
                  </button>
                ) : (
                  <button onClick={handleSend} disabled={!input.trim()}
                    className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40 transition-opacity">
                    <Send size={15} />
                  </button>
                )}
                {messages.length > 0 && !streaming && (
                  <button onClick={clear} title="Clear chat"
                    className="rounded-xl border border-border p-2.5 text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors">
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
              <div className="flex justify-end">
                <span className={`text-xs tabular-nums ${input.length >= MAX_MESSAGE_LEN ? 'text-red-400' : 'text-faint'}`}>
                  {input.length} / {MAX_MESSAGE_LEN}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ── TEXT-TO-SQL ── */}
        {activeTab === 'query' && (
          <div className="flex flex-col gap-4">
            {/* Description + history toggle */}
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm text-muted-foreground">
                Ask any question in plain English — the AI generates a PostgreSQL query, executes it, and explains the results.
              </p>
              <button
                onClick={() => setShowHistory(v => !v)}
                className={`flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  showHistory
                    ? 'border-primary/40 bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:text-foreground hover:bg-subtle'
                }`}
              >
                <History size={13} />
                History
                {historyEntries.length > 0 && (
                  <span className={`rounded-full px-1.5 py-0.5 text-xs font-semibold ${
                    showHistory ? 'bg-primary/20 text-primary' : 'bg-subtle text-faint'
                  }`}>
                    {historyEntries.length}
                  </span>
                )}
              </button>
            </div>

            {/* History panel */}
            {showHistory && (
              <QueryHistoryPanel
                entries={historyEntries}
                onSelect={entry => { setSqlInput(entry.question); ask(entry.question); setShowHistory(false) }}
                onToggleFavorite={toggleFavorite}
                onRemove={removeHistory}
                onClear={clearHistory}
              />
            )}

            {/* Example chips */}
            {!sql && !sqlStreaming && !sqlError && (
              <div className="flex flex-wrap gap-2">
                {SQL_SUGGESTED.map(q => (
                  <button key={q} onClick={() => { setSqlInput(q); ask(q) }}
                    className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors">
                    {q}
                  </button>
                ))}
              </div>
            )}

            {/* Input row */}
            <div className="flex gap-2">
              <input
                value={sqlInput}
                onChange={e => setSqlInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && !sqlStreaming && sqlInput.trim() && ask(sqlInput.trim())}
                placeholder="e.g. How many transactions failed today?"
                disabled={sqlStreaming}
                className="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-sm text-foreground placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
              />
              {sqlStreaming ? (
                <button onClick={cancelSql}
                  className="flex items-center gap-1.5 rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-subtle transition-colors">
                  <X size={15} /> Cancel
                </button>
              ) : (
                <button onClick={() => sqlInput.trim() && ask(sqlInput.trim())} disabled={!sqlInput.trim()}
                  className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40 transition-opacity">
                  <Send size={15} />
                </button>
              )}
              {(sql || sqlError || explanation) && !sqlStreaming && (
                <button onClick={() => { reset(); setSqlInput(''); setSqlExpanded(false) }}
                  title="Clear" className="rounded-xl border border-border p-2.5 text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors">
                  <Trash2 size={15} />
                </button>
              )}
            </div>

            {/* Status indicator */}
            {sqlStreaming && status && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 size={14} className="animate-spin text-primary" />
                {status}
              </div>
            )}

            {/* Error */}
            {sqlError && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
                <p className="text-sm font-medium text-red-400">{friendlyError(sqlError.code, sqlError.message)}</p>
                {sqlError.code === 'sql_validation_rejected' && (
                  <p className="mt-1 text-xs text-red-400/70">{sqlError.message}</p>
                )}
              </div>
            )}

            {/* Generated SQL */}
            {sql && (
              <div className="rounded-xl border border-border bg-card overflow-hidden">
                <button
                  onClick={() => setSqlExpanded(v => !v)}
                  className="flex w-full items-center justify-between px-4 py-2.5 text-xs font-semibold uppercase tracking-widest text-faint hover:bg-subtle transition-colors">
                  <span className="flex items-center gap-1.5">
                    <Database size={12} /> Generated SQL
                  </span>
                  {sqlExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </button>
                {sqlExpanded && (
                  <pre className="overflow-x-auto px-4 pb-4 text-xs text-green-400 leading-relaxed whitespace-pre-wrap font-mono">
                    {sql}
                  </pre>
                )}
              </div>
            )}

            {/* Streaming explanation */}
            {(explanation || (sqlStreaming && sql)) && (
              <div className="rounded-xl border border-border bg-card p-5">
                <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                  {explanation}
                  {sqlStreaming && explanation && <span className="ml-1 inline-block h-3 w-0.5 animate-pulse bg-current" />}
                </p>
              </div>
            )}
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
