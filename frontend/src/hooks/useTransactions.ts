import { useEffect, useState } from 'react'
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
    fetchJson<TransactionPage>(`/api/v1/transactions?${toParams(filters)}`)
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

  useEffect(() => {
    fetchJson<RefItem[]>('/api/v1/transactions/reference/hubs').then(setHubs).catch(() => {})
  }, [])

  useEffect(() => {
    const url = hubId != null
      ? `/api/v1/transactions/reference/services?hub_id=${hubId}`
      : '/api/v1/transactions/reference/services'
    fetchJson<RefItem[]>(url).then(setServices).catch(() => {})
  }, [hubId])

  return { hubs, services }
}

export function useTransactionDetail(id: number | null) {
  const [detail, setDetail] = useState<TransactionDetail | null>(null)
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id === null) { setDetail(null); setAudit([]); return }
    setLoading(true)
    Promise.all([
      fetchJson<TransactionDetail>(`/api/v1/transactions/${id}`),
      fetchJson<AuditEntry[]>(`/api/v1/transactions/${id}/audit`),
    ]).then(([d, a]) => {
      setDetail(d)
      setAudit(a)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [id])

  return { detail, audit, loading }
}
