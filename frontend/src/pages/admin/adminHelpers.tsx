import { s, LEVEL_STYLE, BAND_STYLE, RUNG_LABELS, RUNG_COLORS, RUNG_TEXT } from './adminStyles'
import type { ScoreLevel, UsageBand } from './adminStyles'

// eslint-disable-next-line react-refresh/only-export-components -- badge components + tiny helpers, same grouping as the old app
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

// level/band arrive as `string | null` from the generated schema; unknown
// values render nothing, exactly like the old lookup-miss behaviour.
export function LevelBadge({ level }: { level: string | null | undefined }) {
  const st = level ? LEVEL_STYLE[level as ScoreLevel] : undefined
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

interface FieldProps {
  id: string
  label: string
  type?: string
  placeholder?: string
  value: string
  onChange: (value: string) => void
  focused?: boolean
  onFocus?: () => void
  onBlur?: () => void
}

export function Field({ id, label, type = 'text', placeholder, value, onChange, focused, onFocus, onBlur }: FieldProps) {
  return (
    <div style={s.fieldWrap}>
      <label htmlFor={id} style={s.label}>{label}</label>
      <input
        id={id} type={type} placeholder={placeholder} value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={onFocus} onBlur={onBlur}
        style={{ ...s.input, ...(focused ? s.inputFocus : {}) }}
        autoComplete="off"
      />
    </div>
  )
}
