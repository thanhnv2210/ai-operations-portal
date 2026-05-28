import { useCallback, useEffect, useState } from 'react'
import {
  FONT_SIZE_EVENT,
  FONT_SIZE_MIN,
  FONT_SIZE_MAX,
  getAutoFontSize,
  getStoredFontSize,
  setStoredFontSize,
} from '@/components/FontScaler'

export function FontSizeControl() {
  const [autoSize, setAutoSize] = useState<number>(14)
  const [override, setOverride] = useState<number | null>(null)

  const refresh = useCallback(() => {
    setAutoSize(getAutoFontSize())
    setOverride(getStoredFontSize())
  }, [])

  useEffect(() => {
    refresh()
    window.addEventListener(FONT_SIZE_EVENT, refresh)
    window.addEventListener('focus', refresh)
    return () => {
      window.removeEventListener(FONT_SIZE_EVENT, refresh)
      window.removeEventListener('focus', refresh)
    }
  }, [refresh])

  const current = override ?? autoSize
  const isManual = override !== null

  function adjust(delta: number) {
    const next = Math.min(FONT_SIZE_MAX, Math.max(FONT_SIZE_MIN, current + delta))
    setStoredFontSize(next)
    setOverride(next)
  }

  function reset() {
    setStoredFontSize(null)
    setOverride(null)
  }

  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-foreground">Font size</p>
        <p className="text-xs text-muted-foreground">
          {isManual ? (
            <>Manual override — auto would be <span className="text-foreground">{autoSize}px</span></>
          ) : (
            <>Auto-detected from screen resolution</>
          )}
        </p>
      </div>

      <div className="flex items-center gap-2">
        {isManual && (
          <button
            onClick={reset}
            className="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Reset to auto
          </button>
        )}
        <div className="flex items-center gap-1 rounded-lg border border-border bg-background overflow-hidden">
          <button
            onClick={() => adjust(-1)}
            disabled={current <= FONT_SIZE_MIN}
            className="px-2.5 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Decrease font size"
          >
            −
          </button>
          <span className="min-w-[3.5rem] border-x border-border px-3 py-1.5 text-center text-sm font-medium tabular-nums text-foreground">
            {current}px
          </span>
          <button
            onClick={() => adjust(1)}
            disabled={current >= FONT_SIZE_MAX}
            className="px-2.5 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Increase font size"
          >
            +
          </button>
        </div>
      </div>
    </div>
  )
}
