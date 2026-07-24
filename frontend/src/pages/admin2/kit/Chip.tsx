import type { ReactNode } from 'react'

export type ChipTone = 'default' | 'good' | 'warn' | 'info' | 'red'

interface ChipProps {
  children: ReactNode
  tone?: ChipTone
  /** CSS color for an optional leading dot (e.g. a maturity-level swatch) —
   * the one deliberately dynamic per-instance style value in this kit
   * (can't be a static `adm-` class since the color is caller data). */
  dot?: string
}

const TONE_CLASS: Record<ChipTone, string> = {
  default: 'adm-chip-default',
  good: 'adm-chip-good',
  warn: 'adm-chip-warn',
  info: 'adm-chip-info',
  red: 'adm-chip-red',
}

/** Small status/label pill. Tone always pairs with the text content itself
 * (never color-only) — callers supply the word ("Active", "Stalled", …).
 * Prototype: docs/design-prototypes/admin-redesign/styles.css `.chip`. */
export function Chip({ children, tone = 'default', dot }: ChipProps) {
  return (
    <span className={`adm-chip ${TONE_CLASS[tone]}`}>
      {dot && <span className="adm-chip-dot" style={{ background: dot }} />}
      {children}
    </span>
  )
}
