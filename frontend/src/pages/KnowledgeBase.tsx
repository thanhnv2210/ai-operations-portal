import { useState } from 'react'
import { BookOpen, ChevronDown, ChevronUp, Loader2, Search } from 'lucide-react'
import { API_BASE } from '@/lib/api'

interface SourceChunk {
  chunk_text: string
  section_title: string
  source_file: string
  vector_score: number
  rrf_score: number
}

interface QueryResponse {
  answer: string
  sources: SourceChunk[]
}

const EXAMPLE_QUESTIONS = [
  'What columns carry PII in remittance.transaction?',
  'What tables contain transaction data?',
  'How does the PayNow SOF flow work?',
  'What is the difference between remittance_amount and recipient_amount?',
  'What schemas are in ml_db?',
  'How do you find all status changes for a transaction?',
]

const NO_CONTEXT_ANSWER = 'Not enough relevant context found in the knowledge base to answer this question.'

export function KnowledgeBase() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set())

  async function ask(question: string) {
    if (!question.trim() || loading) return
    setLoading(true)
    setResult(null)
    setError(null)
    setExpandedSources(new Set())

    try {
      const res = await fetch(`${API_BASE}/api/v1/rag/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(detail.detail ?? res.statusText)
      }
      setResult(await res.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  function toggleSource(index: number) {
    setExpandedSources(prev => {
      const next = new Set(prev)
      next.has(index) ? next.delete(index) : next.add(index)
      return next
    })
  }

  const noContext = result?.answer === NO_CONTEXT_ANSWER

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-4xl space-y-5">
        <div className="flex items-center gap-3">
          <BookOpen size={24} className="text-primary" />
          <div>
            <h1 className="text-2xl font-bold text-foreground">Knowledge Base</h1>
            <p className="text-sm text-muted-foreground">
              Ask questions about the database schema and architecture. Answers are grounded in the ingested docs with source citations.
            </p>
          </div>
        </div>

        {/* Example questions */}
        {!result && !loading && (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-widest text-faint">Example questions</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS.map(q => (
                <button
                  key={q}
                  onClick={() => { setInput(q); ask(q) }}
                  className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input row */}
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && ask(input)}
            placeholder="Ask about the schema, tables, columns, relationships…"
            disabled={loading}
            className="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-sm text-foreground placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
          />
          <button
            onClick={() => ask(input)}
            disabled={!input.trim() || loading}
            className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40 transition-opacity"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
            {loading ? 'Searching…' : 'Ask'}
          </button>
          {result && !loading && (
            <button
              onClick={() => { setResult(null); setError(null); setInput('') }}
              className="rounded-xl border border-border px-3 py-2.5 text-sm text-muted-foreground hover:bg-subtle transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Answer */}
        {result && (
          <div className="space-y-4">
            <div className={`rounded-xl border p-5 ${noContext ? 'border-amber-500/30 bg-amber-500/10' : 'border-border bg-card'}`}>
              <p className={`text-sm leading-relaxed whitespace-pre-wrap ${noContext ? 'text-amber-400' : 'text-foreground'}`}>
                {result.answer}
              </p>
            </div>

            {/* Source cards */}
            {result.sources.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-widest text-faint">
                  {result.sources.length} source{result.sources.length !== 1 ? 's' : ''} retrieved
                </p>
                {result.sources.map((src, i) => (
                  <div key={i} className="rounded-xl border border-border bg-card overflow-hidden">
                    <button
                      onClick={() => toggleSource(i)}
                      className="flex w-full items-center justify-between px-4 py-3 hover:bg-subtle transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">
                          {i + 1}
                        </span>
                        <div className="min-w-0 text-left">
                          <p className="truncate text-sm font-medium text-foreground">{src.section_title}</p>
                          <p className="text-xs text-faint">{src.source_file}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 ml-3">
                        <span className="text-xs tabular-nums text-muted-foreground">
                          {(src.vector_score * 100).toFixed(0)}% match
                        </span>
                        {expandedSources.has(i) ? <ChevronUp size={13} className="text-faint" /> : <ChevronDown size={13} className="text-faint" />}
                      </div>
                    </button>
                    {expandedSources.has(i) && (
                      <div className="border-t border-border px-4 pb-4 pt-3">
                        <pre className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap font-mono">
                          {src.chunk_text}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
