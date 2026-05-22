import { useState } from 'react'
import { Search } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { TransactionDrawer } from '@/components/TransactionDrawer'
import { useTransactions } from '@/hooks/useTransactions'
import type { TransactionFilters } from '@/types/transactions'

function toIso(d: Date) {
  return d.toISOString().slice(0, 16)
}

const defaultFilters: TransactionFilters = {
  from_date: toIso(new Date(Date.now() - 90 * 86_400_000)),
  to_date: toIso(new Date()),
  status: [],
  page: 1,
  page_size: 20,
}

const COMMON_STATUSES = [
  'TRANSACTION_COMPLETED', 'TRANSACTION_ON_HOLD', 'TRANSACTION_FAILED',
  'REFUNDED', 'REFUNDED_BY_HUB', 'PAYMENT_VALIDATED', 'PAYMENT_RESERVED_FAILED',
  'FRAUD_CHECK_FAILED',
]

function fmt(v: number | null | undefined, currency?: string | null) {
  if (v == null) return '—'
  return currency ? `${v.toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}` : String(v)
}

function fmtDate(d: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleString('en-SG', { dateStyle: 'short', timeStyle: 'short' })
}

export function TransactionExplorer() {
  const [filters, setFilters] = useState<TransactionFilters>(defaultFilters)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [refInput, setRefInput] = useState('')
  const [errInput, setErrInput] = useState('')

  const { data, loading, error } = useTransactions(filters)

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
          {/* Date range */}
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-widest text-faint w-16">Period</span>
            <input
              type="datetime-local" value={filters.from_date}
              onChange={e => setFilters(f => ({ ...f, from_date: e.target.value, page: 1 }))}
              className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <span className="text-faint">→</span>
            <input
              type="datetime-local" value={filters.to_date}
              onChange={e => setFilters(f => ({ ...f, to_date: e.target.value, page: 1 }))}
              className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Status toggles */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-widest text-faint w-16">Status</span>
            {COMMON_STATUSES.map(s => (
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
            ))}
            {filters.status.length > 0 && (
              <button onClick={() => setFilters(f => ({ ...f, status: [], page: 1 }))} className="text-xs text-muted-foreground hover:text-foreground">
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
                  <th className="px-4 py-2.5 font-medium">Created</th>
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
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{fmtDate(tx.created_date)}</td>
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
