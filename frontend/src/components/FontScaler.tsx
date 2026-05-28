import { useEffect } from 'react'
import {
  FONT_STORAGE_KEY,
  FONT_SIZE_EVENT,
  FONT_SIZE_MIN,
  FONT_SIZE_MAX,
} from '@/lib/font-size-config'

export { FONT_STORAGE_KEY, FONT_SIZE_EVENT, FONT_SIZE_MIN, FONT_SIZE_MAX }

/**
 * Auto-detect base font size from screen.width (logical CSS pixels).
 * Covers mobile → tablet → laptop → desktop → HiDPI monitors.
 */
export function getAutoFontSize(): number {
  const w = window.screen.width
  if (w <  768) return 16   // Mobile
  if (w < 1280) return 15   // Tablet / iPad
  if (w < 1440) return 14   // Small laptop
  if (w < 1920) return 15   // MacBook 16" / standard laptop
  if (w < 2560) return 16   // 1080p desktop
  if (w < 3840) return 17   // 27" 1440p / 4K HiDPI
  return 18                  // Native 4K / 5K
}

export function getStoredFontSize(): number | null {
  try {
    const v = localStorage.getItem(FONT_STORAGE_KEY)
    const n = v ? parseInt(v, 10) : NaN
    return isNaN(n) ? null : n
  } catch {
    return null
  }
}

export function setStoredFontSize(size: number | null) {
  try {
    if (size === null) localStorage.removeItem(FONT_STORAGE_KEY)
    else localStorage.setItem(FONT_STORAGE_KEY, String(size))
  } catch {}
  window.dispatchEvent(new CustomEvent(FONT_SIZE_EVENT))
}

function applyFontSize() {
  const size = getStoredFontSize() ?? getAutoFontSize()
  document.documentElement.style.fontSize = `${size}px`
}

function watchDevicePixelRatio(onChanged: () => void): () => void {
  const dpr = window.devicePixelRatio
  const mq = window.matchMedia(`(resolution: ${dpr}dppx)`)
  function handler() {
    mq.removeEventListener('change', handler)
    onChanged()
    watchDevicePixelRatio(onChanged)
  }
  mq.addEventListener('change', handler)
  return () => mq.removeEventListener('change', handler)
}

/**
 * Mount once in App. Keeps html font-size in sync with:
 * - initial load (after FOUC script has already set it)
 * - display changes (DPR, focus, visibility)
 * - manual overrides dispatched via FONT_SIZE_EVENT
 */
export function FontScaler() {
  useEffect(() => {
    applyFontSize()
    window.addEventListener('resize', applyFontSize)
    window.addEventListener('focus', applyFontSize)
    document.addEventListener('visibilitychange', applyFontSize)
    window.addEventListener(FONT_SIZE_EVENT, applyFontSize)
    const stopWatching = watchDevicePixelRatio(applyFontSize)
    return () => {
      window.removeEventListener('resize', applyFontSize)
      window.removeEventListener('focus', applyFontSize)
      document.removeEventListener('visibilitychange', applyFontSize)
      window.removeEventListener(FONT_SIZE_EVENT, applyFontSize)
      stopWatching()
    }
  }, [])
  return null
}
