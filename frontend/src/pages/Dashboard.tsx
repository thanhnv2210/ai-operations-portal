import { useState } from 'react'
import { FilterBar } from '@/components/FilterBar'
import { HubBreakdownTable } from '@/components/HubBreakdownTable'
import { MetricCard } from '@/components/MetricCard'
import { StatusDistributionChart } from '@/components/StatusDistributionChart'
import { VolumeChart } from '@/components/VolumeChart'
import { useDashboard } from '@/hooks/useDashboard'
import { toSgtIso } from '@/lib/sgt'
import type { DashboardFilters } from '@/types/dashboard'

const defaultFilters: DashboardFilters = {
  from_date: toSgtIso(new Date(Date.now() - 7 * 86_400_000)),
  to_date: toSgtIso(new Date()),
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

function CardSkeleton() {
  return <div className="h-28 animate-pulse rounded-xl bg-subtle" />
}

function SectionSkeleton({ height = 'h-56' }: { height?: string }) {
  return <div className={`${height} animate-pulse rounded-xl bg-subtle`} />
}

function SectionError({ label, message }: { label: string; message: string }) {
  return (
    <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
      Failed to load {label}: {message}
    </div>
  )
}

interface DashboardProps {
  onViewTransactions?: (statuses: string[]) => void
}

export function Dashboard({ onViewTransactions }: DashboardProps) {
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters)
  const {
    overview, volumeTrend, statusDistribution, processingTime, hubBreakdown,
    loadingOverview, loadingVolume, loadingStatus, loadingProcessing, loadingHub,
    errors,
  } = useDashboard(filters)

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

        {/* KPI cards — each renders independently */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {loadingOverview ? (
            <><CardSkeleton /><CardSkeleton /><CardSkeleton /></>
          ) : errors.overview ? (
            <div className="col-span-3 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
              Overview error: {errors.overview}
            </div>
          ) : overview ? (
            <>
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
            </>
          ) : null}

          {loadingProcessing ? (
            <CardSkeleton />
          ) : errors.processing ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-400">
              {errors.processing}
            </div>
          ) : processingTime ? (
            <MetricCard
              label="Processing Time p50"
              value={fmtSeconds(processingTime.p50_seconds ?? null)}
              sub={`p95 ${fmtSeconds(processingTime.p95_seconds ?? null)}`}
            />
          ) : null}
        </div>

        {/* Volume chart */}
        {loadingVolume  ? <SectionSkeleton height="h-64" />
          : errors.volume ? <SectionError label="volume trend" message={errors.volume} />
          : volumeTrend  ? <VolumeChart data={volumeTrend} />
          : null}

        {/* Status distribution */}
        {loadingStatus  ? <SectionSkeleton height="h-72" />
          : errors.status ? <SectionError label="status distribution" message={errors.status} />
          : statusDistribution ? <StatusDistributionChart data={statusDistribution} onViewTransactions={onViewTransactions} />
          : null}

        {/* Hub breakdown */}
        {loadingHub  ? <SectionSkeleton height="h-48" />
          : errors.hub ? <SectionError label="hub breakdown" message={errors.hub} />
          : hubBreakdown ? <HubBreakdownTable data={hubBreakdown} />
          : null}
      </div>
    </div>
  )
}
