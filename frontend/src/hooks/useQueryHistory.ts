import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'aiops:query-history'
const MAX_ENTRIES = 50

export interface QueryHistoryEntry {
  id: string
  timestamp: string
  question: string
  sql: string
  isFavorite: boolean
}

function load(): QueryHistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
  } catch {
    return []
  }
}

function save(entries: QueryHistoryEntry[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
}

export function useQueryHistory() {
  const [entries, setEntries] = useState<QueryHistoryEntry[]>(load)

  // Sync across tabs
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY) setEntries(load())
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const add = useCallback((question: string, sql: string) => {
    setEntries(prev => {
      const entry: QueryHistoryEntry = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        question,
        sql,
        isFavorite: false,
      }
      // Deduplicate: remove previous identical question (keep latest)
      const deduped = prev.filter(e => e.question !== question)
      const next = [entry, ...deduped].slice(0, MAX_ENTRIES)
      save(next)
      return next
    })
  }, [])

  const toggleFavorite = useCallback((id: string) => {
    setEntries(prev => {
      const next = prev.map(e => e.id === id ? { ...e, isFavorite: !e.isFavorite } : e)
      save(next)
      return next
    })
  }, [])

  const remove = useCallback((id: string) => {
    setEntries(prev => {
      const next = prev.filter(e => e.id !== id)
      save(next)
      return next
    })
  }, [])

  const clear = useCallback(() => {
    setEntries(prev => {
      // Keep favorites when clearing
      const next = prev.filter(e => e.isFavorite)
      save(next)
      return next
    })
  }, [])

  return { entries, add, toggleFavorite, remove, clear }
}
