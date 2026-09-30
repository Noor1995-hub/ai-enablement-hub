/** The interviewer puts this marker (backend/prompts/interview.md) on the first line of the
 *  turn where it offers to build the playbook (older stored turns have it on the last line):
 *  the signal to reveal the button. Always stripped from display; the learner never sees it.
 *  Kept in sync with backend/src/services/interview_marker.py, the backend's single home for
 *  the marker. */
export const READY_MARKER = '[[READY_TO_BUILD]]'

/** The marker plus any spaces right after it, so an inline "[[...]] With that" leaves no gap. */
const MARKER_RE = /\[\[READY_TO_BUILD\]\][ \t]*/g

/** Strip the readiness marker from an assistant message for display, and report whether the
 *  full marker has arrived. Also hides a trailing *partial* marker so it never flashes while
 *  the message streams in a few characters at a time. */
export function parseReadySignal(content: string): { text: string; ready: boolean } {
  if (content.includes(READY_MARKER)) {
    return { text: content.replace(MARKER_RE, '').trim(), ready: true }
  }
  const max = Math.min(content.length, READY_MARKER.length - 1)
  for (let n = max; n > 0; n--) {
    if (READY_MARKER.startsWith(content.slice(content.length - n))) {
      return { text: content.slice(0, content.length - n).trimEnd(), ready: false }
    }
  }
  return { text: content, ready: false }
}
