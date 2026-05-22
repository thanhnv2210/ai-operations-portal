import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { StatusDistributionData } from '@/types/dashboard'

// ─── Standard grouping ────────────────────────────────────────────────────────

const STD_FAILED  = ['FAILED', 'DECLINED', 'FRAUD', 'AML']
const STD_SUCCESS = ['SUCCESS', 'COMPLETED', 'CONFIRMED', 'REFUNDED']
const STD_PENDING = ['PENDING', 'IN_PROGRESS', 'SUBMITTED', 'ON_HOLD', 'RESERVED', 'ACCEPTED', 'VALIDATED']

type StdGroup = 'failed' | 'success' | 'pending' | 'other'

function classifyStd(status: string): StdGroup {
  const s = status.toUpperCase()
  if (STD_FAILED.some(p => s.includes(p)))  return 'failed'
  if (STD_SUCCESS.some(p => s.includes(p))) return 'success'
  if (STD_PENDING.some(p => s.includes(p))) return 'pending'
  return 'other'
}

const STD_GROUPS: Record<StdGroup, GroupMeta> = {
  failed:  { label: 'Failed',  bar: 'bg-red-500',   badge: 'bg-red-500/15 text-red-400 ring-red-500/20',      card: 'border-red-500/20 bg-red-500/5' },
  success: { label: 'Success', bar: 'bg-green-500', badge: 'bg-green-500/15 text-green-400 ring-green-500/20', card: 'border-green-500/20 bg-green-500/5' },
  pending: { label: 'Pending', bar: 'bg-amber-500', badge: 'bg-amber-500/15 text-amber-400 ring-amber-500/20', card: 'border-amber-500/20 bg-amber-500/5' },
  other:   { label: 'Other',   bar: 'bg-zinc-500',  badge: 'bg-subtle text-muted-foreground ring-border',       card: 'border-border bg-subtle/40' },
}

const STD_ORDER: StdGroup[] = ['failed', 'success', 'pending', 'other']

// ─── KPMG Report grouping ─────────────────────────────────────────────────────
// Source: KPMG Audit — Report Reference Tables (Table 1)
// Groups derived from which report each status appears in:
//   Active Hold   = Daily ✓ + Hold (group 1) ✓ + Accum ✓   → funds at risk
//   Resolved      = Daily ✓ + Hold (group 2) ✓ + Accum ✗   → terminal success
//   Terminal Fail = Daily ✓ + Hold ✗          + Accum ✗   → failed, no ongoing obligation
//   SOF / Internal= Daily ✗ + Hold ✓          + Accum ✓   → internal SOF states

type KpmgGroup = 'hold' | 'resolved' | 'terminal' | 'sof'

const KPMG_HOLD_STATUSES = new Set([
  'PAYMENT_RESERVED',
  'PAYMENT_REFUND_REQUIRED',
  'PAYMENT_REFUND_REQUIRED_BY_HUB',
  'TRANSACTION_TIMEOUT',
  'TRANSACTION_SUBMITTED',
  'TRANSACTION_REJECTED',
  'TRANSACTION_ON_HOLD',
  'TRANSACTION_DECLINED',
  'TRANSACTION_CANCELLED',
  'TRANSACTION_REVERSED',
  'REFUND_FAILED',
  'PROXY_PAYMENT_RESERVED',
  'PROXY_PAYMENT_REFUND_REQUIRED',
  'PROXY_PAYMENT_ERROR',
  'SOF_PAY_REFUNDED',
  'TRANSACTION_HOLD',
  'TRANSACTION_AVAILABLE',
])

const KPMG_RESOLVED_STATUSES = new Set([
  'TRANSACTION_COMPLETED',
  'TRANSACTION_PAID',
  'REFUNDED',
  'REFUNDED_BY_HUB',
])

const KPMG_TERMINAL_STATUSES = new Set([
  'PAYMENT_TIMEOUT',
  'PAYMENT_ERROR',
  'PROXY_PAYMENT_TIMEOUT',
  'SOF_PAY_REFUND_FAILED',
])

const KPMG_SOF_STATUSES = new Set([
  'SOF_PAY_REFUND_REQUIRED',
  'SOF_PAY_REFUNDED_FAILED',
])

function classifyKpmg(status: string): KpmgGroup {
  if (KPMG_HOLD_STATUSES.has(status))     return 'hold'
  if (KPMG_RESOLVED_STATUSES.has(status)) return 'resolved'
  if (KPMG_TERMINAL_STATUSES.has(status)) return 'terminal'
  if (KPMG_SOF_STATUSES.has(status))      return 'sof'
  // Fallback: use name-based heuristics for unknown statuses
  const s = status.toUpperCase()
  if (s.includes('REFUND') || s.includes('HOLD') || s.includes('RESERVED') || s.includes('TIMEOUT') || s.includes('SUBMITTED')) return 'hold'
  if (s.includes('COMPLETED') || s.includes('PAID') || s.includes('REFUNDED')) return 'resolved'
  if (s.includes('FAILED') || s.includes('ERROR') || s.includes('DECLINED')) return 'terminal'
  return 'sof'
}

const KPMG_GROUPS: Record<KpmgGroup, GroupMeta> = {
  hold:     { label: 'Active Hold',      bar: 'bg-orange-500', badge: 'bg-orange-500/15 text-orange-400 ring-orange-500/20', card: 'border-orange-500/20 bg-orange-500/5' },
  resolved: { label: 'Resolved',         bar: 'bg-green-500',  badge: 'bg-green-500/15 text-green-400 ring-green-500/20',    card: 'border-green-500/20 bg-green-500/5' },
  terminal: { label: 'Terminal Failure', bar: 'bg-red-500',    badge: 'bg-red-500/15 text-red-400 ring-red-500/20',          card: 'border-red-500/20 bg-red-500/5' },
  sof:      { label: 'SOF / Internal',   bar: 'bg-blue-500',   badge: 'bg-blue-500/15 text-blue-400 ring-blue-500/20',       card: 'border-blue-500/20 bg-blue-500/5' },
}

const KPMG_ORDER: KpmgGroup[] = ['hold', 'resolved', 'terminal', 'sof']

// ─── Shared types ─────────────────────────────────────────────────────────────

interface GroupMeta {
  label: string
  bar:   string
  badge: string
  card:  string
}

type ViewMode = 'standard' | 'kpmg'
const INITIAL_VISIBLE = 10

// ─── Component ────────────────────────────────────────────────────────────────

interface Props {
  data: StatusDistributionData
}

export function StatusDistributionChart({ data }: Props) {
  const [mode, setMode]              = useState<ViewMode>('standard')
  const [showAll, setShowAll]        = useState(false)
  const [activeGroup, setActiveGroup] = useState<string | null>(null)

  const total = data.statuses.reduce((s, r) => s + r.count, 0)
  if (total === 0) return null

  // Reset group filter when switching view mode
  function switchMode(m: ViewMode) {
    setMode(m)
    setActiveGroup(null)
    setShowAll(false)
  }

  // Enrich rows with group info
  const groups     = mode === 'kpmg' ? KPMG_GROUPS     : STD_GROUPS
  const groupOrder = mode === 'kpmg' ? KPMG_ORDER      : STD_ORDER
  const classify   = mode === 'kpmg' ? classifyKpmg    : classifyStd

  const rows = data.statuses.map(r => ({ ...r, group: classify(r.status) }))

  const groupTotals = groupOrder.reduce<Record<string, number>>(
    (acc, g) => ({ ...acc, [g]: rows.filter(r => r.group === g).reduce((s, r) => s + r.count, 0) }),
    {},
  )

  const filtered = activeGroup ? rows.filter(r => r.group === activeGroup) : rows
  const visible  = showAll ? filtered : filtered.slice(0, INITIAL_VISIBLE)
  const maxCount = filtered[0]?.count ?? 1

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-4">

      {/* Header + mode toggle */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-faint">
            Status Distribution
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {data.statuses.length} statuses · {total.toLocaleString()} total
          </p>
        </div>
        <div className="flex items-center rounded-lg border border-border bg-subtle p-0.5 text-xs shrink-0">
          <button
            onClick={() => switchMode('standard')}
            className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
              mode === 'standard'
                ? 'bg-card text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Standard
          </button>
          <button
            onClick={() => switchMode('kpmg')}
            className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
              mode === 'kpmg'
                ? 'bg-card text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            KPMG Report
          </button>
        </div>
      </div>

      {/* KPMG mode description */}
      {mode === 'kpmg' && (
        <p className="text-xs text-muted-foreground border border-border rounded-md px-3 py-2 bg-subtle/50">
          Grouped by <span className="font-medium text-foreground">KPMG audit report logic</span>:
          Active Hold = funds at risk (Hold + Accum) ·
          Resolved = terminal success ·
          Terminal Failure = failed, no ongoing obligation ·
          SOF / Internal = source-of-funds internal states
        </p>
      )}

      {/* Group summary cards */}
      <div className={`grid gap-2 ${groupOrder.length === 4 ? 'grid-cols-4' : 'grid-cols-3'}`}>
        {groupOrder.map(g => {
          const meta  = (groups as Record<string, GroupMeta>)[g]
          const count = groupTotals[g] ?? 0
          const pct   = total ? ((count / total) * 100).toFixed(1) : '0.0'
          const active = activeGroup === g
          return (
            <button
              key={g}
              onClick={() => setActiveGroup(active ? null : g)}
              className={`rounded-lg border p-3 text-left transition-all ${meta.card} ${
                active ? 'ring-2 ring-primary/40' : 'hover:opacity-80'
              }`}
            >
              <p className="text-xs text-muted-foreground truncate">{meta.label}</p>
              <p className="text-lg font-bold text-foreground">{pct}%</p>
              <p className="text-xs text-muted-foreground">{count.toLocaleString()}</p>
            </button>
          )
        })}
      </div>

      {/* Active filter label */}
      {activeGroup && (
        <p className="text-xs text-muted-foreground">
          Showing{' '}
          <span className="font-medium text-foreground">
            {(groups as Record<string, GroupMeta>)[activeGroup].label}
          </span>{' '}
          statuses only —{' '}
          <button className="underline hover:text-foreground" onClick={() => setActiveGroup(null)}>
            clear filter
          </button>
        </p>
      )}

      {/* Detailed rows */}
      <div className="space-y-1.5">
        {visible.map(row => {
          const meta = (groups as Record<string, GroupMeta>)[row.group]
          const pct  = ((row.count / total) * 100).toFixed(1)
          const barW = Math.round((row.count / maxCount) * 100)
          return (
            <div key={row.status} className="flex items-center gap-3">
              <span className={`shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 w-52 truncate ${meta.badge}`}>
                {row.status.replace(/_/g, ' ')}
              </span>
              <div className="flex-1 h-2 rounded-full bg-subtle overflow-hidden">
                <div className={`h-full rounded-full ${meta.bar} transition-all`} style={{ width: `${barW}%` }} />
              </div>
              <span className="shrink-0 w-16 text-right text-xs text-foreground font-medium tabular-nums">
                {row.count.toLocaleString()}
              </span>
              <span className="shrink-0 w-10 text-right text-xs text-muted-foreground tabular-nums">
                {pct}%
              </span>
            </div>
          )
        })}
      </div>

      {/* Show more / less */}
      {filtered.length > INITIAL_VISIBLE && (
        <button
          onClick={() => setShowAll(s => !s)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {showAll
            ? <><ChevronUp size={13} /> Show less</>
            : <><ChevronDown size={13} /> Show {filtered.length - INITIAL_VISIBLE} more statuses</>
          }
        </button>
      )}
    </div>
  )
}
