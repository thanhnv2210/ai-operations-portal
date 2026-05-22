const FAILED = ['FAILED', 'DECLINED', 'FRAUD', 'AML']
const SUCCESS = ['SUCCESS', 'COMPLETED', 'CONFIRMED', 'REFUNDED']
const PENDING = ['PENDING', 'IN_PROGRESS', 'SUBMITTED', 'ON_HOLD', 'RESERVED', 'ACCEPTED', 'VALIDATED']

function classify(status: string): 'success' | 'failed' | 'pending' | 'neutral' {
  const s = status.toUpperCase()
  if (FAILED.some(p => s.includes(p))) return 'failed'
  if (SUCCESS.some(p => s.includes(p))) return 'success'
  if (PENDING.some(p => s.includes(p))) return 'pending'
  return 'neutral'
}

const colors = {
  success: 'bg-green-500/15 text-green-400 ring-green-500/20',
  failed:  'bg-red-500/15 text-red-400 ring-red-500/20',
  pending: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
  neutral: 'bg-subtle text-muted-foreground ring-border',
}

export function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="text-faint">—</span>
  const kind = classify(status)
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${colors[kind]}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}
