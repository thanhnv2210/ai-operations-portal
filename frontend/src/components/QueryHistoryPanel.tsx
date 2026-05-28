import { useState } from 'react'
import { ChevronDown, ChevronUp, Database, Star, Trash2 } from 'lucide-react'
import type { QueryHistoryEntry } from '@/hooks/useQueryHistory'

interface Props {
  entries: QueryHistoryEntry[]
  onSelect: (entry: QueryHistoryEntry) => void
  onToggleFavorite: (id: string) => void
  onRemove: (id: string) => void
  onClear: () => void
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60_000)
  const hours = Math.floor(diff / 3_600_000)
  const days  = Math.floor(diff / 86_400_000)
  if (mins  < 1)  return 'just now'
  if (mins  < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

export function QueryHistoryPanel({ entries, onSelect, onToggleFavorite, onRemove, onClear }: Props) {
  const [filter, setFilter] = useState<'all' | 'favorites'>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const displayed = filter === 'favorites' ? entries.filter(e => e.isFavorite) : entries
  const favoriteCount = entries.filter(e => e.isFavorite).length

  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-5 text-center">
        <Database size={28} className="mx-auto mb-2 text-faint" />
        <p className="text-sm text-muted-foreground">No queries yet.</p>
        <p className="mt-1 text-xs text-faint">Your Text-to-SQL history will appear here.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex gap-1">
          <button
            onClick={() => setFilter('all')}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              filter === 'all'
                ? 'bg-primary/15 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            All ({entries.length})
          </button>
          <button
            onClick={() => setFilter('favorites')}
            className={`flex items-center gap-1 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              filter === 'favorites'
                ? 'bg-amber-500/15 text-amber-400'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Star size={11} />
            Favorites ({favoriteCount})
          </button>
        </div>
        {entries.some(e => !e.isFavorite) && (
          <button
            onClick={onClear}
            className="text-xs text-faint hover:text-muted-foreground transition-colors"
            title="Clear non-favorites"
          >
            Clear history
          </button>
        )}
      </div>

      {/* List */}
      <div className="divide-y divide-border max-h-96 overflow-y-auto">
        {displayed.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">No favorites saved yet.</p>
        ) : (
          displayed.map(entry => (
            <div key={entry.id} className="group px-4 py-3 hover:bg-subtle transition-colors">
              <div className="flex items-start gap-2">
                {/* Question — click to re-run */}
                <button
                  onClick={() => onSelect(entry)}
                  className="flex-1 text-left text-sm text-foreground hover:text-primary transition-colors line-clamp-2"
                  title="Click to run this query again"
                >
                  {entry.question}
                </button>

                {/* Actions */}
                <div className="flex shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => onToggleFavorite(entry.id)}
                    title={entry.isFavorite ? 'Remove from favorites' : 'Save to favorites'}
                    className={`rounded p-1 transition-colors ${
                      entry.isFavorite
                        ? 'text-amber-400 hover:text-amber-300'
                        : 'text-faint hover:text-amber-400'
                    }`}
                  >
                    <Star size={13} fill={entry.isFavorite ? 'currentColor' : 'none'} />
                  </button>
                  <button
                    onClick={() => onRemove(entry.id)}
                    title="Remove"
                    className="rounded p-1 text-faint hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>

                {/* Always-visible favorite indicator */}
                {entry.isFavorite && (
                  <Star size={11} className="shrink-0 mt-0.5 text-amber-400 group-hover:hidden" fill="currentColor" />
                )}
              </div>

              {/* Timestamp + SQL toggle */}
              <div className="mt-1.5 flex items-center gap-3">
                <span className="text-xs text-faint">{formatRelative(entry.timestamp)}</span>
                <button
                  onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                  className="flex items-center gap-1 text-xs text-faint hover:text-muted-foreground transition-colors"
                >
                  <Database size={10} />
                  SQL
                  {expandedId === entry.id ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                </button>
              </div>

              {/* Expanded SQL */}
              {expandedId === entry.id && (
                <pre className="mt-2 overflow-x-auto rounded-lg bg-background px-3 py-2 text-xs text-green-400 leading-relaxed whitespace-pre-wrap font-mono">
                  {entry.sql}
                </pre>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
