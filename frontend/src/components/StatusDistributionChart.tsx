import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { StatusDistributionData } from '@/types/dashboard'

const FAILED_PATTERNS = ['FAILED', 'DECLINED', 'FRAUD', 'AML']

function isFailedStatus(status: string): boolean {
  return FAILED_PATTERNS.some(p => status.includes(p))
}

interface Props {
  data: StatusDistributionData
}

export function StatusDistributionChart({ data }: Props) {
  const chartData = data.statuses.slice(0, 12).map(s => ({
    status: s.status.replace(/_/g, ' '),
    count: s.count,
    failed: isFailedStatus(s.status),
  }))

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-faint">
        Status Distribution
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 24, left: 8, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} allowDecimals={false} />
          <YAxis type="category" dataKey="status" tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} width={160} />
          <Tooltip
            contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8 }}
            labelStyle={{ color: 'var(--foreground)' }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.failed ? '#ef4444' : '#6366f1'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
