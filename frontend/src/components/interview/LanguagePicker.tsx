import { useRef, type CSSProperties, type KeyboardEvent } from 'react'
import type { InterviewLanguage } from '../../lib/interviewStrings'

/** The interview's language choice on the welcome screen (#83): a radio group, each option
 *  named in its own language so a learner finds theirs whichever one is showing. The page
 *  switches its own text as soon as one is picked, so the learner sees the choice before
 *  starting. Keyboard: one tab stop (the chosen option), arrow keys move and choose. */
const OPTIONS: { value: InterviewLanguage; label: string; lang: string }[] = [
  { value: 'en', label: 'English', lang: 'en' },
  { value: 'nl', label: 'Nederlands', lang: 'nl' },
]

const NEXT_KEYS = ['ArrowRight', 'ArrowDown']
const PREVIOUS_KEYS = ['ArrowLeft', 'ArrowUp']

/** What inline styles can't express: hover and keyboard focus. The backgrounds live here, not
 *  inline, so the hover can change them. Local, with an `lp-` prefix, the same idiom as the
 *  interview page's `iv-` and the playbook's `pb-`. */
const PICKER_CSS = `
.lp-option { background: transparent; color: var(--dlw-text); transition: background var(--dlw-duration) var(--dlw-ease); }
.lp-option:hover { background: var(--dlw-surface); }
.lp-option[aria-checked="true"], .lp-option[aria-checked="true"]:hover { background: var(--dlw-black); color: #fff; }
.lp-option:focus-visible { outline: 2px solid var(--dlw-primary-red); outline-offset: 2px; }
`

const s = {
  group: { display: 'inline-flex', gap: 0, border: '1px solid var(--dlw-border)', borderRadius: 999, padding: 3, background: '#fff' },
  option: {
    border: 'none', borderRadius: 999, padding: '7px 16px', fontSize: 13.5, fontWeight: 600,
    fontFamily: 'var(--dlw-font-ui)', cursor: 'pointer',
  },
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
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  function onKeyDown(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = NEXT_KEYS.includes(e.key) ? 1 : PREVIOUS_KEYS.includes(e.key) ? -1 : 0
    if (step === 0) return
    e.preventDefault()
    const next = (index + step + OPTIONS.length) % OPTIONS.length
    refs.current[next]?.focus()
    onChange(OPTIONS[next].value)
  }

  return (
    <div role="radiogroup" aria-label={label} style={s.group}>
      <style>{PICKER_CSS}</style>
      {OPTIONS.map((option, index) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            ref={el => { refs.current[index] = el }}
            type="button"
            role="radio"
            lang={option.lang}
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            className="lp-option"
            style={s.option}
            onClick={() => onChange(option.value)}
            onKeyDown={e => onKeyDown(e, index)}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
