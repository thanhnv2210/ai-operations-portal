/** Singapore Time (UTC+8) helpers */

const SGT_OFFSET_MS = 8 * 60 * 60 * 1000

/**
 * Returns a "YYYY-MM-DDTHH:MM" string in SGT for use in datetime-local inputs.
 * The value represents the wall-clock time in Singapore.
 */
export function toSgtIso(d: Date): string {
  const sgt = new Date(d.getTime() + SGT_OFFSET_MS)
  return sgt.toISOString().slice(0, 16)
}

/**
 * Formats a date string or Date object for display in SGT.
 */
export function fmtSgt(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(d).toLocaleString('en-SG', {
    timeZone: 'Asia/Singapore',
    dateStyle: 'short',
    timeStyle: 'short',
  })
}
