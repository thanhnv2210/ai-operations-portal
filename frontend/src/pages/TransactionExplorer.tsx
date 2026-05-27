import { useEffect, useState } from 'react'
import { ArrowDownUp, Search, Star } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { TransactionDrawer } from '@/components/TransactionDrawer'
import { getPopularStatuses, recordStatusHits, useReference, useStatusCounts, useTransactions } from '@/hooks/useTransactions'
import { fmtSgt, toSgtIso } from '@/lib/sgt'
import type { TransactionFilters } from '@/types/transactions'

const QUICK_RANGES = [
  { label: '15m', ms: 15 * 60_000 },
  { label: '1h',  ms: 60 * 60_000 },
  { label: '1d',  ms: 24 * 60 * 60_000 },
  { label: '1w',  ms: 7  * 24 * 60 * 60_000 },
  { label: '1mo', ms: 30 * 24 * 60 * 60_000 },
]

const defaultFilters: TransactionFilters = {
  from_date: toSgtIso(new Date(Date.now() - 24 * 60 * 60_000)),
  to_date: toSgtIso(new Date()),
  status: [],
  sort_order: 'desc',
  page: 1,
  page_size: 20,
}

const STATUS_GROUPS: { label: string; statuses: string[] }[] = [
  {
    label: 'Pre-Payment',
    statuses: [
      'PAYMENT_VALIDATED', 'PAYMENT_VALIDATED_FAILED', 'PAYMENT_ACCEPTED', 'PAYMENT_PENDING',
      'PAYMENT_AML_FAIL', 'PAYMENT_RESERVED', 'PAYMENT_RESERVED_FAILED', 'PAYMENT_ERROR',
      'PROXY_PAYMENT_RESERVED', 'PROXY_PAYMENT_RESERVED_FAILED', 'PROXY_PAYMENT_ERROR',
      'FRAUD_CHECK_FAILED', 'FRAUD_CHECK_DECLINED',
    ],
  },
  {
    label: 'Timeout',
    statuses: ['PAYMENT_TIMEOUT', 'PROXY_PAYMENT_TIMEOUT', 'TRANSACTION_TIMEOUT', 'FRAUD_CHECK_TIMEOUT'],
  },
  {
    label: 'Submitted',
    statuses: [
      'REMIT_BY_TELEPIN_SUBMITTED', 'REMIT_BY_TELEPIN_FAILED', 'TRANSACTION_SUBMITTED',
      'TRANSACTION_IN_PROGRESS', 'TRANSACTION_AVAILABLE', 'TRANSACTION_ON_HOLD', 'TRANSACTION_HOLD',
      'TRANSACTION_FAILED', 'TRANSACTION_DECLINED', 'TRANSACTION_CANCELLED', 'TRANSACTION_REJECTED',
      'TRANSACTION_REJECTED_BANK', 'TRANSACTION_SENDSMS_FAILED',
    ],
  },
  {
    label: 'Refund Pending',
    statuses: [
      'PAYMENT_REFUND_REQUIRED', 'PAYMENT_REFUND_REQUIRED_BY_HUB', 'PROXY_PAYMENT_REFUND_REQUIRED',
      'REMIT_BY_TELEPIN_REFUND_REQUIRED', 'REFUND_FAILED', 'PROXY_PAYMENT_REFUND_FAILED',
    ],
  },
  {
    label: 'Monitor',
    statuses: ['TRANSACTION_REVERSED', 'REMIT_BY_TELEPIN_UNKNOWN'],
  },
  {
    label: 'Completed',
    statuses: [
      'TRANSACTION_COMPLETED', 'TRANSACTION_SUCCESS', 'TRANSACTION_CONFIRMED', 'TRANSACTION_PAID',
      'REFUNDED', 'REFUNDED_BY_HUB', 'PROXY_PAYMENT_REFUNDED',
    ],
  },
]

const _groupedSet = new Set(STATUS_GROUPS.flatMap(g => g.statuses))

function fmt(v: number | null | undefined, currency?: string | null) {
  if (v == null) return '—'
  return currency ? `${v.toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}` : String(v)
}


interface TransactionExplorerProps {
  initialStatuses?: string[]
}

export function TransactionExplorer({ initialStatuses }: TransactionExplorerProps) {
  const [filters, setFilters] = useState<TransactionFilters>(() =>
    initialStatuses && initialStatuses.length > 0
      ? { ...defaultFilters, status: initialStatuses }
      : defaultFilters
  )
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [refInput, setRefInput] = useState('')
  const [errInput, setErrInput] = useState('')
  const [activeQuick, setActiveQuick] = useState<string | null>('1d')
  const [popular, setPopular] = useState<string[]>(() => getPopularStatuses())

  function applyQuickRange(label: string, ms: number) {
    const now = new Date()
    setActiveQuick(label)
    setFilters(f => ({ ...f, from_date: toSgtIso(new Date(now.getTime() - ms)), to_date: toSgtIso(now), page: 1 }))
  }

  const { hubs, services, statuses } = useReference(filters.hub_id)
  const statusCounts = useStatusCounts(filters.from_date, filters.to_date, filters.hub_id, filters.service_id)
  const { data, loading, error } = useTransactions(filters)

  useEffect(() => {
    if (data && data.total > 0 && filters.status.length > 0) {
      recordStatusHits(filters.status)
      setPopular(getPopularStatuses())
    }
  }, [data])

  function applySearch() {
    setFilters(f => ({
      ...f,
      payment_reference_id: refInput || undefined,
      error_code: errInput || undefined,
      page: 1,
    }))
  }

  function toggleStatus(s: string) {
    setFilters(f => ({
      ...f,
      page: 1,
      status: f.status.includes(s) ? f.status.filter(x => x !== s) : [...f.status, s],
    }))
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <h1 className="text-2xl font-bold text-foreground">Transaction Explorer</h1>

        {/* Filter panel */}
        <div className="rounded-xl border border-border bg-card p-5 space-y-4">
          {/* Date range + quick ranges */}
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-widest text-faint w-16">Period</span>
            {/* Quick range pills */}
            <div className="flex items-center gap-1">
              {QUICK_RANGES.map(({ label, ms }) => (
                <button
                  key={label}
                  onClick={() => applyQuickRange(label, ms)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    activeQuick === label
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-subtle text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="text-faint text-xs">or</span>
            <input
              type="datetime-local" value={filters.from_date}
              onChange={e => { setActiveQuick(null); setFilters(f => ({ ...f, from_date: e.target.value, page: 1 })) }}
              className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <span className="text-faint">→</span>
            <input
              type="datetime-local" value={filters.to_date}
              onChange={e => { setActiveQuick(null); setFilters(f => ({ ...f, to_date: e.target.value, page: 1 })) }}
              className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Status filters */}
          <div className="space-y-2">
            {/* Popular pills */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1 text-xs font-semibold uppercase tracking-widest text-faint w-16">
                <Star size={10} /> Top
              </span>
              {popular.length === 0 ? (
                <span className="text-xs text-faint italic">No popular statuses yet — select statuses below to discover them</span>
              ) : (
                popular.map(s => (
                  <button
                    key={s}
                    onClick={() => toggleStatus(s)}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 transition-colors ${
                      filters.status.includes(s)
                        ? 'bg-primary text-primary-foreground ring-primary'
                        : 'bg-subtle text-muted-foreground ring-border hover:ring-primary/40'
                    }`}
                  >
                    {s.replace(/_/g, ' ')}
                  </button>
                ))
              )}
            </div>

            {/* Status dropdown + active tags */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-widest text-faint w-16">Status</span>
              <select
                value=""
                onChange={e => { if (e.target.value) toggleStatus(e.target.value) }}
                className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">Add a status filter…</option>
                {STATUS_GROUPS.map(group => {
                  const options = group.statuses.filter(s =>
                    statuses.includes(s) && !filters.status.includes(s)
                  )
                  if (options.length === 0) return null
                  return (
                    <optgroup key={group.label} label={group.label}>
                      {options.map(s => {
                        const count = statusCounts.get(s)
                        const label = count != null
                          ? `${s.replace(/_/g, ' ')} (${count.toLocaleString()})`
                          : s.replace(/_/g, ' ')
                        return <option key={s} value={s}>{label}</option>
                      })}
                    </optgroup>
                  )
                })}
                {(() => {
                  const others = statuses.filter(s =>
                    !_groupedSet.has(s) && !filters.status.includes(s)
                  )
                  if (others.length === 0) return null
                  return (
                    <optgroup label="Other">
                      {others.map(s => {
                        const count = statusCounts.get(s)
                        const label = count != null
                          ? `${s.replace(/_/g, ' ')} (${count.toLocaleString()})`
                          : s.replace(/_/g, ' ')
                        return <option key={s} value={s}>{label}</option>
                      })}
                    </optgroup>
                  )
                })()}
              </select>
              {filters.status.map(s => (
                <button
                  key={s}
                  onClick={() => toggleStatus(s)}
                  className="flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-medium text-primary ring-1 ring-primary/30 hover:bg-red-500/15 hover:text-red-400 hover:ring-red-400/30 transition-colors"
                >
                  {s.replace(/_/g, ' ')} ×
                </button>
              ))}
              {filters.status.length > 0 && (
                <button onClick={() => setFilters(f => ({ ...f, status: [], page: 1 }))} className="text-xs text-muted-foreground hover:text-foreground">
                  clear all
                </button>
              )}
            </div>
          </div>

          {/* Hub / Service filters */}
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-widest text-faint w-16">Hub</span>
            <select
              value={filters.hub_id ?? ''}
              onChange={e => {
                const val = e.target.value ? Number(e.target.value) : undefined
                setFilters(f => ({ ...f, hub_id: val, service_id: undefined, page: 1 }))
              }}
              className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="">All hubs</option>
              {hubs.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
            <span className="text-xs font-semibold uppercase tracking-widest text-faint">Service</span>
            <select
              value={filters.service_id ?? ''}
              onChange={e => {
                const val = e.target.value ? Number(e.target.value) : undefined
                setFilters(f => ({ ...f, service_id: val, page: 1 }))
              }}
              className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 max-w-xs"
            >
              <option value="">All services</option>
              {services.some(s => s.active) && (
                <optgroup label="Active">
                  {services.filter(s => s.active).map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </optgroup>
              )}
              {services.some(s => !s.active) && (
                <optgroup label="Deactivated">
                  {services.filter(s => !s.active).map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </optgroup>
              )}
            </select>
            {(filters.hub_id != null || filters.service_id != null) && (
              <button
                onClick={() => setFilters(f => ({ ...f, hub_id: undefined, service_id: undefined, page: 1 }))}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                clear
              </button>
            )}
          </div>

          {/* Search inputs */}
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-widest text-faint w-16">Search</span>
            <input
              placeholder="Payment reference..."
              value={refInput}
              onChange={e => setRefInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applySearch()}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-primary/40 w-48"
            />
            <input
              placeholder="Error code..."
              value={errInput}
              onChange={e => setErrInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applySearch()}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-primary/40 w-40"
            />
            <button
              onClick={applySearch}
              className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
            >
              <Search size={14} /> Search
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Results table */}
        <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-border">
            <p className="text-sm text-muted-foreground">
              {loading ? 'Loading…' : `${data?.total.toLocaleString() ?? 0} transactions`}
            </p>
            {data && data.pages > 1 && (
              <div className="flex items-center gap-2 text-sm">
                <button
                  disabled={filters.page <= 1}
                  onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))}
                  className="px-2 py-1 rounded border border-border text-muted-foreground disabled:opacity-30 hover:bg-subtle"
                >←</button>
                <span className="text-muted-foreground">{filters.page} / {data.pages}</span>
                <button
                  disabled={filters.page >= data.pages}
                  onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))}
                  className="px-2 py-1 rounded border border-border text-muted-foreground disabled:opacity-30 hover:bg-subtle"
                >→</button>
              </div>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-faint uppercase tracking-wide bg-muted">
                  <th className="px-4 py-2.5 font-medium">Reference</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Hub</th>
                  <th className="px-4 py-2.5 font-medium">Service</th>
                  <th className="px-4 py-2.5 font-medium text-right">Amount</th>
                  <th className="px-4 py-2.5 font-medium">Error</th>
                  <th className="px-4 py-2.5 font-medium">
                    <button
                      onClick={() => setFilters(f => ({ ...f, sort_order: f.sort_order === 'desc' ? 'asc' : 'desc', page: 1 }))}
                      className="flex items-center gap-1 hover:text-foreground transition-colors"
                    >
                      Created
                      <ArrowDownUp size={11} className={filters.sort_order === 'asc' ? 'text-primary' : 'text-faint'} />
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  [...Array(8)].map((_, i) => (
                    <tr key={i} className="border-b border-border/50">
                      {[...Array(7)].map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 animate-pulse rounded bg-subtle" />
                        </td>
                      ))}
                    </tr>
                  ))
                )}
                {!loading && data?.items.map(tx => (
                  <tr
                    key={tx.internal_transaction_id}
                    onClick={() => setSelectedId(tx.internal_transaction_id)}
                    className="border-b border-border/50 last:border-0 hover:bg-muted cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-foreground">
                      {tx.payment_reference_id ?? <span className="text-faint">#{tx.internal_transaction_id}</span>}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={tx.status} /></td>
                    <td className="px-4 py-3 text-muted-foreground">{tx.hub_name ?? '—'}</td>
                    <td className="px-4 py-3 text-muted-foreground max-w-48 truncate">{tx.service_name ?? '—'}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground">
                      {fmt(tx.remittance_amount, tx.sender_currency)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-red-400">
                      {tx.error_code ?? tx.hub_error_code ?? ''}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{fmtSgt(tx.created_date)}</td>
                  </tr>
                ))}
                {!loading && data?.items.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-sm text-muted-foreground">
                      No transactions match the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <TransactionDrawer transactionId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
