import { useState } from 'react'
import { FilterBar } from '@/components/FilterBar'
import { HubBreakdownTable } from '@/components/HubBreakdownTable'
import { MetricCard } from '@/components/MetricCard'
import { StatusDistributionChart } from '@/components/StatusDistributionChart'
import { VolumeChart } from '@/components/VolumeChart'
import { useDashboard } from '@/hooks/useDashboard'
import type { DashboardFilters } from '@/types/dashboard'

function toIso(d: Date) {
  return d.toISOString().slice(0, 16)
}

const defaultFilters: DashboardFilters = {
  from_date: toIso(new Date(Date.now() - 90 * 86_400_000)),
  to_date: toIso(new Date()),
}

function fmtSeconds(s: number | null): string {
  if (s === null) return '—'
  if (s < 60) return `${s.toFixed(0)}s`
  if (s < 3600) return `${(s / 60).toFixed(1)}m`
  return `${(s / 3600).toFixed(1)}h`
}

function fmtVolume(v: number): string {
  return v.toLocaleString('en-SG', { style: 'currency', currency: 'SGD', maximumFractionDigits: 0 })
}

export function Dashboard() {
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters)
  const { overview, volumeTrend, statusDistribution, processingTime, hubBreakdown, loading, error } =
    useDashboard(filters)

  const failHighlight =
    overview && overview.failure_rate > 0.1 ? 'danger'
    : overview && overview.failure_rate > 0.05 ? 'warning'
    : 'default'

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <h1 className="text-2xl font-bold text-foreground">Operational Dashboard</h1>

        {/* Filters */}
        <FilterBar filters={filters} onChange={setFilters} />

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            Failed to load dashboard data: {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-28 animate-pulse rounded-xl bg-subtle" />
            ))}
          </div>
        )}

        {/* KPI cards */}
        {!loading && overview && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricCard
              label="Total Transactions"
              value={overview.total_transactions.toLocaleString()}
            />
            <MetricCard
              label="Failure Rate"
              value={`${(overview.failure_rate * 100).toFixed(1)}%`}
              sub={`${overview.failed_transactions} failed`}
              highlight={failHighlight}
            />
            <MetricCard
              label="Total Volume"
              value={fmtVolume(overview.total_volume)}
              sub={`avg ${fmtVolume(overview.avg_volume_per_tx)} / tx`}
            />
            <MetricCard
              label="Processing Time p50"
              value={fmtSeconds(processingTime?.p50_seconds ?? null)}
              sub={processingTime ? `p95 ${fmtSeconds(processingTime.p95_seconds)}` : undefined}
            />
          </div>
        )}

        {/* Charts row */}
        {!loading && volumeTrend && statusDistribution && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <VolumeChart data={volumeTrend} />
            <StatusDistributionChart data={statusDistribution} />
          </div>
        )}

        {/* Hub breakdown */}
        {!loading && hubBreakdown && <HubBreakdownTable data={hubBreakdown} />}
      </div>
    </div>
  )
}
