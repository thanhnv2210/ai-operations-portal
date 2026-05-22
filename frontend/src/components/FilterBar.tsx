import type { DashboardFilters } from '@/types/dashboard'

interface FilterBarProps {
  filters: DashboardFilters
  onChange: (f: DashboardFilters) => void
}

const PRESETS = [
  { label: '7d',  days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '1y',  days: 365 },
]

function toIso(d: Date) {
  return d.toISOString().slice(0, 16)
}

function presetRange(days: number): { from_date: string; to_date: string } {
  const to = new Date()
  const from = new Date(to.getTime() - days * 86_400_000)
  return { from_date: toIso(from), to_date: toIso(to) }
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-sm">
      <div className="flex gap-1">
        {PRESETS.map(p => (
          <button
            key={p.label}
            onClick={() => onChange({ ...filters, ...presetRange(p.days) })}
            className="rounded-md px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-subtle transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="h-5 w-px bg-border" />

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="datetime-local"
          value={filters.from_date}
          onChange={e => onChange({ ...filters, from_date: e.target.value })}
          className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
        <span className="text-faint">→</span>
        <input
          type="datetime-local"
          value={filters.to_date}
          onChange={e => onChange({ ...filters, to_date: e.target.value })}
          className="rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </div>
    </div>
  )
}
