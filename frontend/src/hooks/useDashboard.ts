import { useEffect, useState } from 'react'
import { dashboardLimiter } from '@/lib/concurrency'
import type {
  DashboardFilters,
  HubBreakdownData,
  OverviewData,
  ProcessingTimeData,
  StatusDistributionData,
  VolumeTrendData,
} from '@/types/dashboard'

const BASE = '/api/v1/dashboard'

function toParams(filters: DashboardFilters): string {
  const p = new URLSearchParams({ from_date: filters.from_date, to_date: filters.to_date })
  if (filters.hub_id != null) p.set('hub_id', String(filters.hub_id))
  if (filters.service_id != null) p.set('service_id', String(filters.service_id))
  return p.toString()
}

async function fetchJson<T>(url: string, signal: AbortSignal): Promise<T> {
  return dashboardLimiter(async () => {
    const res = await fetch(url, { signal })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    return res.json() as Promise<T>
  })
}

export interface DashboardData {
  overview: OverviewData | null
  volumeTrend: VolumeTrendData | null
  statusDistribution: StatusDistributionData | null
  processingTime: ProcessingTimeData | null
  hubBreakdown: HubBreakdownData | null
  // Per-section loading flags — each becomes false as its request resolves
  loadingOverview: boolean
  loadingVolume: boolean
  loadingStatus: boolean
  loadingProcessing: boolean
  loadingHub: boolean
  errors: Partial<Record<'overview' | 'volume' | 'status' | 'processing' | 'hub', string>>
}

const INITIAL: DashboardData = {
  overview: null, volumeTrend: null, statusDistribution: null,
  processingTime: null, hubBreakdown: null,
  loadingOverview: true, loadingVolume: true, loadingStatus: true,
  loadingProcessing: true, loadingHub: true,
  errors: {},
}

export function useDashboard(filters: DashboardFilters): DashboardData {
  const [data, setData] = useState<DashboardData>(INITIAL)

  useEffect(() => {
    // Reset to loading state on filter change
    setData(INITIAL)

    const controller = new AbortController()
    const { signal } = controller
    const qs = toParams(filters)

    const patch = (slice: Partial<DashboardData>) =>
      setData(prev => ({ ...prev, ...slice }))

    fetchJson<OverviewData>(`${BASE}/overview?${qs}`, signal)
      .then(overview => patch({ overview, loadingOverview: false }))
      .catch(err => { if (!signal.aborted) patch({ loadingOverview: false, errors: { overview: String(err) } }) })

    fetchJson<VolumeTrendData>(`${BASE}/volume-trend?${qs}&interval=day`, signal)
      .then(volumeTrend => patch({ volumeTrend, loadingVolume: false }))
      .catch(err => { if (!signal.aborted) patch({ loadingVolume: false, errors: { volume: String(err) } }) })

    fetchJson<StatusDistributionData>(`${BASE}/status-distribution?${qs}`, signal)
      .then(statusDistribution => patch({ statusDistribution, loadingStatus: false }))
      .catch(err => { if (!signal.aborted) patch({ loadingStatus: false, errors: { status: String(err) } }) })

    fetchJson<ProcessingTimeData>(`${BASE}/processing-time?${qs}`, signal)
      .then(processingTime => patch({ processingTime, loadingProcessing: false }))
      .catch(err => { if (!signal.aborted) patch({ loadingProcessing: false, errors: { processing: String(err) } }) })

    fetchJson<HubBreakdownData>(`${BASE}/hub-breakdown?${qs}`, signal)
      .then(hubBreakdown => patch({ hubBreakdown, loadingHub: false }))
      .catch(err => { if (!signal.aborted) patch({ loadingHub: false, errors: { hub: String(err) } }) })

    return () => controller.abort()
  }, [filters.from_date, filters.to_date, filters.hub_id, filters.service_id])

  return data
}
