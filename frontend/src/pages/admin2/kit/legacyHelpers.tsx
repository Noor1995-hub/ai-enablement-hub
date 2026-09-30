/* Pre-kit badge helpers (level/band badges, rung pill, date format), kept until
 * the styling convergence lands. Re-exported from the kit barrel. */
import { s, LEVEL_STYLE, BAND_STYLE, RUNG_LABELS, RUNG_COLORS, RUNG_TEXT } from './legacyStyles'
import type { UsageBand } from './legacyStyles'
import type { LevelDef } from '../../../lib/levels'

// eslint-disable-next-line react-refresh/only-export-components -- badge components + tiny helpers, same grouping as the old app
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

// level/band arrive as `string | null` from the generated schema; unknown
// values render nothing, exactly like the old lookup-miss behaviour.
export function LevelBadge({ level }: { level: string | null | undefined }) {
  const st = level ? LEVEL_STYLE[level as LevelDef['code']] : undefined
  if (!st) return null
  return <span style={{ ...s.badge, background: st.bg, color: st.text }}>{st.label}</span>
}

export function BandBadge({ band }: { band: string | null | undefined }) {
  const st = band ? BAND_STYLE[band as UsageBand] : undefined
  if (!st) return null
  return <span style={{ ...s.badge, background: st.bg, color: st.text }}>{st.label}</span>
}

export function RungPill({ rung }: { rung: number | null | undefined }) {
  if (rung == null) return null
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 999,
      fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 10,
      background: RUNG_COLORS[rung], color: RUNG_TEXT[rung],
      whiteSpace: 'nowrap', flexShrink: 0,
    }}>
      {RUNG_LABELS[rung]}
    </span>
  )
}
