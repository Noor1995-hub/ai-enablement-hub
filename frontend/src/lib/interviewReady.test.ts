import { describe, expect, it } from 'vitest'
import { READY_MARKER, parseReadySignal } from './interviewReady'

describe('parseReadySignal', () => {
  it('hides a marker on the first line of the offer (#96) and leaves no blank line', () => {
    expect(parseReadySignal(`${READY_MARKER}\nThat's plenty. Shall I build it?`)).toEqual({
      text: "That's plenty. Shall I build it?",
      ready: true,
    })
  })

  it('still hides a marker on the last line (turns stored before #96)', () => {
    expect(parseReadySignal(`Shall I build it?\n${READY_MARKER}`)).toEqual({
      text: 'Shall I build it?',
      ready: true,
    })
  })

  it('hides a marker that is still streaming in at the start', () => {
    expect(parseReadySignal('[[READY_')).toEqual({ text: '', ready: false })
  })

  it('hides a partial marker streaming in at the end', () => {
    expect(parseReadySignal('Shall I build it?\n[[REA')).toEqual({ text: 'Shall I build it?', ready: false })
  })

  it('leaves no stray space where an inline marker sat mid-turn', () => {
    expect(parseReadySignal(`Clear picture.\n\n${READY_MARKER} With that, shall I build it?`)).toEqual({
      text: 'Clear picture.\n\nWith that, shall I build it?',
      ready: true,
    })
  })

  it('leaves a plain turn alone', () => {
    expect(parseReadySignal('Which system is it?')).toEqual({ text: 'Which system is it?', ready: false })
  })
})
