import { describe, expect, it } from 'vitest'
import { chatToolbarHint } from './interviewHints'

const base = { modelReady: false, canBuild: false, answerCount: 0, hasMessages: true }

describe('chatToolbarHint', () => {
  it('explains the greyed-out Build button before the first answer', () => {
    expect(chatToolbarHint(base)).toBe(
      'Answer in your own words. Build my playbook unlocks once the interviewer has enough to go on.',
    )
  })

  it('does not ask for an answer while there is nothing to answer yet (opening, failed opener, loading)', () => {
    expect(chatToolbarHint({ ...base, hasMessages: false })).toBe(
      'Build my playbook unlocks once the interviewer has enough to go on.',
    )
  })

  it('encourages the learner once they have answered', () => {
    expect(chatToolbarHint({ ...base, answerCount: 1 })).toBe(
      'Keep going: the more you share, the better your playbook.',
    )
  })

  it('offers the build once the fallback floor is reached', () => {
    expect(chatToolbarHint({ ...base, canBuild: true, answerCount: 8 })).toBe(
      'You can build your playbook now, or keep going for a richer result.',
    )
  })

  it("the interviewer's ready signal wins, even before any answer", () => {
    const ready = "Your playbook's ready to build whenever you are, or keep chatting to add more."
    expect(chatToolbarHint({ ...base, modelReady: true, canBuild: true, answerCount: 5 })).toBe(ready)
    expect(chatToolbarHint({ ...base, modelReady: true, canBuild: true, answerCount: 0 })).toBe(ready)
  })

  it('follows the house style: no em dash, en dash or ellipsis character', () => {
    const states = [
      base,
      { ...base, hasMessages: false },
      { ...base, answerCount: 1 },
      { ...base, canBuild: true, answerCount: 8 },
      { ...base, modelReady: true, canBuild: true },
    ]
    for (const st of states) expect(chatToolbarHint(st)).not.toMatch(/[—–…]/)
  })
})

describe('chatToolbarHint in Dutch (#83)', () => {
  it('speaks the learner\'s chosen language', () => {
    expect(chatToolbarHint({ ...base, answerCount: 1 }, 'nl')).toBe(
      'Ga gerust verder: hoe meer u vertelt, hoe beter uw playbook.',
    )
  })
})
