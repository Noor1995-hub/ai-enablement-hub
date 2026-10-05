import { describe, expect, it } from 'vitest'
import { parseSummary } from './playbookSummary'

describe('parseSummary', () => {
  it('splits a short intro from its bullet points', () => {
    const text = 'You already know where the time goes.\n\n- You rebuild the board deck by hand.\n- You check every SAP export twice.'
    expect(parseSummary(text)).toEqual({
      intro: ['You already know where the time goes.'],
      bullets: ['You rebuild the board deck by hand.', 'You check every SAP export twice.'],
    })
  })

  it('accepts the bullet characters a model sometimes uses instead of a hyphen', () => {
    expect(parseSummary('Intro.\n• One\n* Two').bullets).toEqual(['One', 'Two'])
  })

  it('keeps an older summary without bullets as a plain paragraph', () => {
    const text = 'You run the monthly close yourself and know exactly where it hurts.'
    expect(parseSummary(text)).toEqual({ intro: [text], bullets: [] })
  })

  it('ignores blank lines and stray whitespace', () => {
    expect(parseSummary('  Intro.  \n\n\n-   One  \n')).toEqual({ intro: ['Intro.'], bullets: ['One'] })
  })
})
