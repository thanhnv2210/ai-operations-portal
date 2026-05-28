import { useCallback, useEffect, useState } from 'react'

export interface QueryHistoryEntry {
  id: string
  timestamp: string   // ISO 8601
  question: string
  sql: string
  is_favorite: boolean
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function useQueryHistory() {
  const [entries, setEntries] = useState<QueryHistoryEntry[]>([])
  const [loading, setLoading] = useState(true)

  const fetchAll = useCallback(async () => {
    try {
      const data = await apiFetch<QueryHistoryEntry[]>('/api/v1/history')
      setEntries(data)
    } catch {
      // silently ignore — history is non-critical
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const add = useCallback(async (question: string, sql: string) => {
    try {
      const entry = await apiFetch<QueryHistoryEntry>('/api/v1/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, sql }),
      })
      // Server deduplicates and returns the new entry; refresh to reflect order
      setEntries(prev => {
        const deduped = prev.filter(e => e.question !== question)
        return [entry, ...deduped]
      })
    } catch { /* non-critical */ }
  }, [])

  const toggleFavorite = useCallback(async (id: string) => {
    try {
      const updated = await apiFetch<QueryHistoryEntry>(`/api/v1/history/${id}/favorite`, {
        method: 'PATCH',
      })
      setEntries(prev => prev.map(e => e.id === id ? updated : e))
    } catch { /* non-critical */ }
  }, [])

  const remove = useCallback(async (id: string) => {
    try {
      await apiFetch<void>(`/api/v1/history/${id}`, { method: 'DELETE' })
      setEntries(prev => prev.filter(e => e.id !== id))
    } catch { /* non-critical */ }
  }, [])

  const clear = useCallback(async () => {
    try {
      await apiFetch<void>('/api/v1/history', { method: 'DELETE' })
      setEntries(prev => prev.filter(e => e.is_favorite))
    } catch { /* non-critical */ }
  }, [])

  return { entries, loading, add, toggleFavorite, remove, clear }
}
