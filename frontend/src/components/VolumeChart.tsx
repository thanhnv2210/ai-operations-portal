import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { VolumeTrendData } from '@/types/dashboard'

interface VolumeChartProps {
  data: VolumeTrendData
}

function formatBucket(bucket: string): string {
  const d = new Date(bucket)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export function VolumeChart({ data }: VolumeChartProps) {
  const chartData = data.points.map(p => ({
    date: formatBucket(p.bucket),
    Successful: p.total - p.failed,
    Failed: p.failed,
  }))

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-faint">
        Transaction Volume
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8 }}
            labelStyle={{ color: 'var(--foreground)' }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: 'var(--muted-foreground)' }} />
          <Bar dataKey="Successful" stackId="a" fill="#22c55e" radius={[0, 0, 0, 0]} />
          <Bar dataKey="Failed" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
