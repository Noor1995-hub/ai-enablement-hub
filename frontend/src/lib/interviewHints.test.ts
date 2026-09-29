import { describe, expect, it } from 'vitest'
import { chatToolbarHint } from './interviewHints'

const base = { modelReady: false, canBuild: false, answerCount: 0 }

describe('chatToolbarHint', () => {
  it('explains the greyed-out Build button before the first answer', () => {
    expect(chatToolbarHint(base)).toBe(
      'Answer in your own words. Build my playbook unlocks once the interviewer has enough to go on.',
    )
  })

  it('encourages the learner once they have answered', () => {
    expect(chatToolbarHint({ ...base, answerCount: 1 })).toBe(
      'Keep going — the more you share, the better your playbook.',
    )
  })

  it('offers the build once the fallback floor is reached', () => {
    expect(chatToolbarHint({ ...base, canBuild: true, answerCount: 8 })).toBe(
      'You can build your playbook now, or keep going for a richer result.',
    )
  })

  it("the interviewer's ready signal wins, even before any answer", () => {
    const ready = "Your playbook's ready to build whenever you are — or keep chatting to add more."
    expect(chatToolbarHint({ modelReady: true, canBuild: true, answerCount: 5 })).toBe(ready)
    expect(chatToolbarHint({ modelReady: true, canBuild: true, answerCount: 0 })).toBe(ready)
  })
})
