interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  highlight?: 'default' | 'danger' | 'warning'
}

export function MetricCard({ label, value, sub, highlight = 'default' }: MetricCardProps) {
  const borderColor = {
    default: 'border-border',
    danger: 'border-red-500',
    warning: 'border-amber-400',
  }[highlight]

  const valueColor = {
    default: 'text-foreground',
    danger: 'text-red-500',
    warning: 'text-amber-500',
  }[highlight]

  return (
    <div className={`rounded-xl border-2 ${borderColor} bg-card p-5 shadow-sm`}>
      <p className="text-xs font-semibold uppercase tracking-widest text-faint">{label}</p>
      <p className={`mt-2 text-3xl font-bold tabular-nums ${valueColor}`}>{value}</p>
      {sub && <p className="mt-1 text-sm text-muted-foreground">{sub}</p>}
    </div>
  )
}
