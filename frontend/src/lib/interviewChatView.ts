/** A chat message as the interview page displays it: the ready marker already stripped. */
export interface DisplayMessage {
  role: 'user' | 'assistant'
  text: string
}

export type BubbleView = 'text' | 'streaming' | 'typing' | 'hidden'

/** How to draw message `index`.
 *  - 'typing': the last interviewer message has no visible text yet while its reply streams
 *    (the placeholder useChat adds before the first token). Keyed on the visible (parsed)
 *    text, not the raw content: the ready marker can stream in before any words.
 *  - 'streaming': words are arriving but the reply isn't finished; the page keeps a busy
 *    cue next to them until the stream closes.
 *  - 'hidden': an empty interviewer message once nothing is streaming (a turn that failed
 *    before any words), so no empty bubble is left behind.
 *  - 'text': everything else. */
export function bubbleView(messages: DisplayMessage[], index: number, loading: boolean): BubbleView {
  const m = messages[index]
  if (m.role === 'user') return 'text'
  const isLiveReply = loading && index === messages.length - 1
  if (m.text.trim() === '') return isLiveReply ? 'typing' : 'hidden'
  return isLiveReply ? 'streaming' : 'text'
}

const TYPING = 'The interviewer is typing.'

/** Text for the page's screen-reader live region during the chat. It stays the same while a
 *  reply streams, so screen readers never read out half-written fragments, then carries the
 *  finished reply. Silent after an error (the error's own alert speaks) and when the learner
 *  spoke last. */
export function liveAnnouncement(
  messages: DisplayMessage[],
  { loading, opening, error }: { loading: boolean; opening: boolean; error: string | null },
): string {
  if (loading || opening) return TYPING
  if (error) return ''
  const last = messages[messages.length - 1]
  return last?.role === 'assistant' ? last.text.trim() : ''
}

/** The Build button's own screen-reader description while it is greyed out (why, and what
 *  unlocks it), or null once it can be used. */
export function buildButtonStatus({ canBuild, loading }: { canBuild: boolean; loading: boolean }): string | null {
  if (!canBuild) return 'Unlocks once the interviewer has enough to go on.'
  if (loading) return 'Available once the interviewer finishes replying.'
  return null
}
