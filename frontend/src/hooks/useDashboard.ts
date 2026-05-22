import { useEffect, useState } from 'react'
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

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export interface DashboardData {
  overview: OverviewData | null
  volumeTrend: VolumeTrendData | null
  statusDistribution: StatusDistributionData | null
  processingTime: ProcessingTimeData | null
  hubBreakdown: HubBreakdownData | null
  loading: boolean
  error: string | null
}

export function useDashboard(filters: DashboardFilters): DashboardData {
  const [data, setData] = useState<DashboardData>({
    overview: null,
    volumeTrend: null,
    statusDistribution: null,
    processingTime: null,
    hubBreakdown: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    setData(prev => ({ ...prev, loading: true, error: null }))
    const qs = toParams(filters)

    Promise.all([
      fetchJson<OverviewData>(`${BASE}/overview?${qs}`),
      fetchJson<VolumeTrendData>(`${BASE}/volume-trend?${qs}&interval=day`),
      fetchJson<StatusDistributionData>(`${BASE}/status-distribution?${qs}`),
      fetchJson<ProcessingTimeData>(`${BASE}/processing-time?${qs}`),
      fetchJson<HubBreakdownData>(`${BASE}/hub-breakdown?${qs}`),
    ])
      .then(([overview, volumeTrend, statusDistribution, processingTime, hubBreakdown]) => {
        setData({ overview, volumeTrend, statusDistribution, processingTime, hubBreakdown, loading: false, error: null })
      })
      .catch(err => {
        setData(prev => ({ ...prev, loading: false, error: String(err) }))
      })
  }, [filters.from_date, filters.to_date, filters.hub_id, filters.service_id])

  return data
}
