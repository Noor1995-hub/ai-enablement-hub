import { describe, expect, it } from 'vitest'
import { bubbleView, buildButtonStatus, liveAnnouncement, type DisplayMessage } from './interviewChatView'

const greeting: DisplayMessage = { role: 'assistant', text: 'Hi Sam, what does a typical week look like?' }
const answer: DisplayMessage = { role: 'user', text: 'Mostly planning.' }
const placeholder: DisplayMessage = { role: 'assistant', text: '' }

describe('bubbleView', () => {
  it('draws normal messages as text', () => {
    const msgs = [greeting, answer]
    expect(bubbleView(msgs, 0, false)).toBe('text')
    expect(bubbleView(msgs, 1, false)).toBe('text')
  })

  it('shows the empty placeholder as a typing indicator while the reply streams', () => {
    expect(bubbleView([greeting, answer, placeholder], 2, true)).toBe('typing')
  })

  it('keys on the visible text: a reply that so far holds only whitespace is still "typing"', () => {
    // #96 streams the ready marker first; once it is stripped, the visible text can be '' or '\n\n'.
    const markerOnly: DisplayMessage = { role: 'assistant', text: '\n\n' }
    expect(bubbleView([greeting, answer, markerOnly], 2, true)).toBe('typing')
  })

  it('hides an empty interviewer bubble once nothing is streaming (a failed or marker-only turn)', () => {
    expect(bubbleView([greeting, answer, placeholder], 2, false)).toBe('hidden')
  })

  it('only the last message can be the typing indicator', () => {
    expect(bubbleView([placeholder, answer], 0, true)).toBe('hidden')
  })

  it('keeps a busy cue while words stream in, until the reply is complete', () => {
    const streaming: DisplayMessage = { role: 'assistant', text: 'Which' }
    expect(bubbleView([greeting, answer, streaming], 2, true)).toBe('streaming')
    expect(bubbleView([greeting, answer, streaming], 2, false)).toBe('text')
  })

  it('an earlier interviewer message is plain text even while a later reply streams', () => {
    expect(bubbleView([greeting, answer, placeholder], 0, true)).toBe('text')
  })
})

describe('liveAnnouncement', () => {
  it('stays constant while a reply streams, so screen readers never read fragments', () => {
    const partial: DisplayMessage = { role: 'assistant', text: 'Which sys' }
    expect(liveAnnouncement([greeting, answer, partial], { loading: true, opening: false, error: null })).toBe(
      'The interviewer is typing.',
    )
  })

  it('announces the typing state while the opener is being prepared', () => {
    expect(liveAnnouncement([], { loading: false, opening: true, error: null })).toBe('The interviewer is typing.')
  })

  it('carries the finished interviewer reply once streaming ends', () => {
    expect(liveAnnouncement([greeting], { loading: false, opening: false, error: null })).toBe(greeting.text)
  })

  it('stays silent when a reply failed part-way, so the error alert speaks alone', () => {
    const partial: DisplayMessage = { role: 'assistant', text: 'Which sys' }
    expect(
      liveAnnouncement([greeting, answer, partial], { loading: false, opening: false, error: 'Connection lost.' }),
    ).toBe('')
  })

  it('announces nothing after the learner speaks or when the last reply is empty', () => {
    const idle = { loading: false, opening: false, error: null }
    expect(liveAnnouncement([greeting, answer], idle)).toBe('')
    expect(liveAnnouncement([greeting, answer, placeholder], idle)).toBe('')
    expect(liveAnnouncement([], idle)).toBe('')
  })
})

describe('buildButtonStatus', () => {
  it('says why the button is greyed out', () => {
    expect(buildButtonStatus({ canBuild: false, loading: false })).toBe(
      'Unlocks once the interviewer has enough to go on.',
    )
    expect(buildButtonStatus({ canBuild: false, loading: true })).toBe(
      'Unlocks once the interviewer has enough to go on.',
    )
  })

  it('explains the short wait while the interviewer is still replying', () => {
    expect(buildButtonStatus({ canBuild: true, loading: true })).toBe(
      'Available once the interviewer finishes replying.',
    )
  })

  it('has nothing to add once the button is usable', () => {
    expect(buildButtonStatus({ canBuild: true, loading: false })).toBeNull()
  })
})
