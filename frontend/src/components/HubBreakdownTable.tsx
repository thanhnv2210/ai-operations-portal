import type { HubBreakdownData } from '@/types/dashboard'

interface Props {
  data: HubBreakdownData
}

function fmtPct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`
}

function fmtVolume(v: number): string {
  return v.toLocaleString('en-SG', { style: 'currency', currency: 'SGD', maximumFractionDigits: 0 })
}

export function HubBreakdownTable({ data }: Props) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-faint">
        Hub Breakdown
      </h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-faint uppercase tracking-wide">
            <th className="pb-2 font-medium">Hub</th>
            <th className="pb-2 font-medium text-right">Total</th>
            <th className="pb-2 font-medium text-right">Failed</th>
            <th className="pb-2 font-medium text-right">Fail Rate</th>
            <th className="pb-2 font-medium text-right">Volume</th>
          </tr>
        </thead>
        <tbody>
          {data.hubs.map(hub => (
            <tr key={hub.hub_id ?? 'unknown'} className="border-b border-border/50 last:border-0">
              <td className="py-2.5 font-medium text-foreground">{hub.hub_name}</td>
              <td className="py-2.5 text-right tabular-nums text-muted-foreground">{hub.total.toLocaleString()}</td>
              <td className="py-2.5 text-right tabular-nums text-muted-foreground">{hub.failed.toLocaleString()}</td>
              <td className={`py-2.5 text-right tabular-nums font-medium ${hub.failure_rate > 0.1 ? 'text-red-500' : hub.failure_rate > 0.05 ? 'text-amber-500' : 'text-green-500'}`}>
                {fmtPct(hub.failure_rate)}
              </td>
              <td className="py-2.5 text-right tabular-nums text-muted-foreground">{fmtVolume(hub.total_volume)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
