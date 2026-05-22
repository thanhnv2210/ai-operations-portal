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
 * Formats a date string for display in SGT.
 * The backend returns naive ISO strings (no timezone suffix) that represent
 * SGT wall-clock time. We append +08:00 before parsing so JavaScript does
 * not misinterpret them as local or UTC time.
 */
export function fmtSgt(d: string | null | undefined): string {
  if (!d) return '—'
  const hasOffset = d.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(d)
  const iso = hasOffset ? d : `${d}+08:00`
  return new Date(iso).toLocaleString('en-SG', {
    timeZone: 'Asia/Singapore',
    dateStyle: 'short',
    timeStyle: 'short',
  })
}
