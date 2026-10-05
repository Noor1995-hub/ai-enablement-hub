import { describe, expect, it } from 'vitest'
import { INTERVIEW_CSS } from './interviewCss'

/** The rule body for a selector in INTERVIEW_CSS (the first rule that starts with it). */
function rule(selector: string): string {
  const start = INTERVIEW_CSS.indexOf(`${selector} {`)
  expect(start).toBeGreaterThanOrEqual(0)
  return INTERVIEW_CSS.slice(start, INTERVIEW_CSS.indexOf('}', start))
}

describe('INTERVIEW_CSS', () => {
  it('wraps long unbroken words on every sheet and in both chat bubbles, so nothing scrolls sideways at 200% zoom', () => {
    expect(rule('.iv-sheet')).toContain('overflow-wrap: anywhere')
    expect(rule('.iv-msg-ai')).toContain('overflow-wrap: anywhere')
    expect(rule('.iv-msg-me')).toContain('overflow-wrap: anywhere')
  })
})
