export interface OverviewData {
  total_transactions: number
  failed_transactions: number
  failure_rate: number
  total_volume: number
  avg_volume_per_tx: number
  from_date: string
  to_date: string
}

export interface VolumeTrendPoint {
  bucket: string
  total: number
  failed: number
}

export interface VolumeTrendData {
  interval: 'hour' | 'day'
  points: VolumeTrendPoint[]
}

export interface StatusCount {
  status: string
  count: number
}

export interface StatusDistributionData {
  statuses: StatusCount[]
}

export interface ProcessingTimeData {
  p50_seconds: number | null
  p95_seconds: number | null
  sample_size: number
}

export interface HubMetric {
  hub_id: number | null
  hub_name: string
  total: number
  failed: number
  failure_rate: number
  total_volume: number
}

export interface HubBreakdownData {
  hubs: HubMetric[]
}

export interface DashboardFilters {
  from_date: string
  to_date: string
  hub_id?: number
  service_id?: number
}
