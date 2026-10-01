import type { CSSProperties } from 'react'
import type { InterviewLanguage } from '../../lib/interviewStrings'

/** The interview's language choice on the welcome screen (#83): two toggle buttons, each
 *  named in its own language so a learner finds theirs whichever one is showing. The page
 *  switches its own text as soon as one is picked, so the learner sees the choice before
 *  starting. */
const OPTIONS: { value: InterviewLanguage; label: string; lang: string }[] = [
  { value: 'en', label: 'English', lang: 'en' },
  { value: 'nl', label: 'Nederlands', lang: 'nl' },
]

const s = {
  group: { display: 'inline-flex', gap: 0, border: '1px solid #E2E2E2', borderRadius: 999, padding: 3, background: '#fff' },
  option: {
    border: 'none', borderRadius: 999, padding: '7px 16px', fontSize: 13.5, fontWeight: 600,
    fontFamily: 'var(--dlw-font-ui)', cursor: 'pointer', background: 'transparent', color: '#4A4A4A',
  },
  selected: { background: 'var(--dlw-black)', color: '#fff' },
} satisfies Record<string, CSSProperties>

export default function LanguagePicker({
  value,
  onChange,
  label = 'Interview language',
}: {
  value: InterviewLanguage
  onChange: (language: InterviewLanguage) => void
  label?: string
}) {
  return (
    <div role="group" aria-label={label} style={s.group}>
      {OPTIONS.map(option => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            lang={option.lang}
            aria-pressed={selected}
            style={{ ...s.option, ...(selected ? s.selected : {}) }}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
