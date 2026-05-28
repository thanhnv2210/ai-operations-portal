import { useEffect, useState } from 'react'
import { API_BASE } from '@/lib/api'
import type { AuditEntry, RefItem, TransactionDetail, TransactionFilters, TransactionPage } from '@/types/transactions'

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

function toParams(f: TransactionFilters): string {
  const p = new URLSearchParams({
    from_date: f.from_date,
    to_date: f.to_date,
    sort_order: f.sort_order,
    page: String(f.page),
    page_size: String(f.page_size),
  })
  f.status.forEach(s => p.append('status', s))
  if (f.hub_id != null) p.set('hub_id', String(f.hub_id))
  if (f.service_id != null) p.set('service_id', String(f.service_id))
  if (f.error_code) p.set('error_code', f.error_code)
  if (f.payment_reference_id) p.set('payment_reference_id', f.payment_reference_id)
  return p.toString()
}

export function useTransactions(filters: TransactionFilters) {
  const [data, setData] = useState<TransactionPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchJson<TransactionPage>(`${API_BASE}/api/v1/transactions?${toParams(filters)}`)
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [
    filters.from_date, filters.to_date, filters.page, filters.page_size,
    filters.status.join(','), filters.hub_id, filters.service_id,
    filters.error_code, filters.payment_reference_id, filters.sort_order,
  ])

  return { data, loading, error }
}

export function useReference(hubId?: number) {
  const [hubs, setHubs] = useState<RefItem[]>([])
  const [services, setServices] = useState<RefItem[]>([])
  const [statuses, setStatuses] = useState<string[]>([])

  useEffect(() => {
    fetchJson<RefItem[]>(`${API_BASE}/api/v1/transactions/reference/hubs`).then(setHubs).catch(() => {})
    fetchJson<string[]>(`${API_BASE}/api/v1/transactions/reference/statuses`).then(setStatuses).catch(() => {})
  }, [])

  useEffect(() => {
    const url = hubId != null
      ? `${API_BASE}/api/v1/transactions/reference/services?hub_id=${hubId}`
      : `${API_BASE}/api/v1/transactions/reference/services`
    fetchJson<RefItem[]>(url).then(setServices).catch(() => {})
  }, [hubId])

  return { hubs, services, statuses }
}

const POPULAR_KEY = 'tx_status_hits'
const MAX_POPULAR = 5

function getHits(): Record<string, number> {
  try { return JSON.parse(localStorage.getItem(POPULAR_KEY) || '{}') }
  catch { return {} }
}

export function getPopularStatuses(): string[] {
  return Object.entries(getHits())
    .sort((a, b) => b[1] - a[1])
    .slice(0, MAX_POPULAR)
    .map(([s]) => s)
}

export function recordStatusHits(statuses: string[]) {
  const hits = getHits()
  for (const s of statuses) hits[s] = (hits[s] || 0) + 1
  localStorage.setItem(POPULAR_KEY, JSON.stringify(hits))
}

export function useStatusCounts(from_date: string, to_date: string, hub_id?: number, service_id?: number) {
  const [counts, setCounts] = useState<Map<string, number>>(new Map())

  useEffect(() => {
    const p = new URLSearchParams({ from_date, to_date })
    if (hub_id != null) p.set('hub_id', String(hub_id))
    if (service_id != null) p.set('service_id', String(service_id))
    fetchJson<{ statuses: { status: string; count: number }[] }>(
      `${API_BASE}/api/v1/dashboard/status-distribution?${p}`
    )
      .then(d => setCounts(new Map(d.statuses.map(s => [s.status, s.count]))))
      .catch(() => {})
  }, [from_date, to_date, hub_id, service_id])

  return counts
}

export function useTransactionDetail(id: number | null) {
  const [detail, setDetail] = useState<TransactionDetail | null>(null)
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id === null) { setDetail(null); setAudit([]); return }
    setLoading(true)
    Promise.all([
      fetchJson<TransactionDetail>(`${API_BASE}/api/v1/transactions/${id}`),
      fetchJson<AuditEntry[]>(`${API_BASE}/api/v1/transactions/${id}/audit`),
    ]).then(([d, a]) => {
      setDetail(d)
      setAudit(a)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [id])

  return { detail, audit, loading }
}
