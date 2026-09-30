// AI Opportunity Interview — the real journey page behind /interview, replacing the
// ComingSoon placeholder. A small state machine: welcome → chat → building → done.
// Chat rendering mirrors components/ChatPanel.tsx's bubble styling and streaming-aware
// input, but isn't a reuse of ChatPanel itself (its "+ New conversation"/History header
// doesn't fit a single interview conversation). Welcome copy/structure follows
// docs/design-prototypes/ai-interviewer/mockup.html's "Welcome" screen, restyled onto
// the hub's real design system (index.css --dlw-* tokens), the same idiom as
// pages/JourneyHome.tsx and pages/Assessment.tsx.
import { useEffect, useRef, useState, type CSSProperties, type FormEvent, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { client } from '../api/client'
import AppNav from '../components/AppNav'
import Spinner from '../components/Spinner'
import Playbook from '../components/interview/Playbook'
import { useAuth } from '../contexts/AuthContext'
import { resolveInterviewTile } from '../lib/interviewAccess'
import { buildPlaybook, getInterviewState, openInterview } from '../lib/interviewApi'
import { chatToolbarHint } from '../lib/interviewHints'
import { parseReadySignal } from '../lib/interviewReady'
import { useChat } from '../lib/useChat'
import { bubbleView, buildButtonStatus, liveAnnouncement } from '../lib/interviewChatView'
import type { InterviewState } from '../types/domain'

type Phase = 'loading' | 'welcome' | 'chat' | 'building' | 'done' | 'needs_assessment'

/** Secondary text on the interviewer screens. The hub's --dlw-muted (#8A8A8A) is 3.45:1 on
 *  white, below the 4.5:1 minimum for normal text; this is 5.33:1 on white and 4.89:1 on
 *  the grey toolbar. Local on purpose: the token is hub-wide. */
const MUTED_TEXT = '#6B6B6B'

/** Ids for screen-reader descriptions (the Build button's status, the input's key help) and
 *  the headings that take focus when the build screens appear. */
const BUILD_STATUS_ID = 'interview-build-status'
const INPUT_HELP_ID = 'interview-input-help'
const BUILDING_HEADING_ID = 'interview-building-heading'
const PLAYBOOK_HEADING_ID = 'interview-playbook-heading'

/** Fallback floor: if the interviewer never signals readiness, the manual build still
 *  unlocks once the learner has sent this many answers, so no one is ever stuck. The
 *  primary path is the model's own readiness signal (lib/interviewReady.ts READY_MARKER). The server enforces the
 *  same floor (backend/src/services/interview_service.py _MIN_ANSWERS_WITHOUT_OFFER): keep
 *  the two numbers equal. */
const FALLBACK_MIN_ANSWERS = 6

/** Server caps chat message content at 4000 chars (backend/src/schemas/chat.py); over that is
 *  a 422. Guard the input so it can't be exceeded. */
const MAX_INPUT = 4000

/** The toolbar hint doubles as the Build button's description (why it is greyed out). */
const BUILD_HINT_ID = 'interview-build-hint'

const s = {
  page: { minHeight: '100vh', background: '#fff', display: 'flex', flexDirection: 'column' },
  main: { flex: 1, width: 'min(760px, 100%)', margin: '0 auto', padding: '44px 40px 80px', boxSizing: 'border-box' },
  // Chat phase: the page is pinned to the window so the chat and the Build button always fit.
  // inset:0, not height:100vh: vh units disagree with the baked-in :root zoom (same approach
  // as LessonPage's edit mode). overflowY:auto, so a very short window scrolls, never clips.
  pageChat: { position: 'fixed', inset: 0, minHeight: 0, overflowY: 'auto' },
  mainChat: { display: 'flex', flexDirection: 'column', padding: '28px 40px 24px' },
  chatScreen: { flex: 1, display: 'flex', flexDirection: 'column' },

  loadingWrap: { minHeight: 400, display: 'flex' },
  errorMsg: { fontSize: 15, fontWeight: 300, color: 'var(--dlw-primary-red)', margin: '40px 0 0' },

  // ── Welcome ──
  eyebrow: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase',
    color: 'var(--dlw-dot-red)', margin: '0 0 14px',
  },
  heading: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 40, lineHeight: 1.15, letterSpacing: '-0.015em',
    color: 'var(--dlw-black)', margin: '0 0 18px',
  },
  body: { fontSize: 16, fontWeight: 300, color: MUTED_TEXT, lineHeight: 1.65, margin: '0 0 28px', maxWidth: '58ch' },

  stepsGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, margin: '0 0 24px' },
  stepCard: { border: '1px solid var(--dlw-border)', borderRadius: 10, padding: '14px 16px' },
  stepLabel: {
    display: 'block', fontFamily: 'var(--dlw-font-ui)', fontWeight: 700,
    fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase',
    color: 'var(--dlw-dot-red)', marginBottom: 6,
  },
  stepText: { margin: 0, fontSize: 13.5, fontWeight: 300, lineHeight: 1.5, color: 'var(--dlw-text)' },

  notice: {
    display: 'flex', gap: 10, alignItems: 'flex-start',
    background: 'var(--dlw-surface)', border: '1px solid var(--dlw-border)',
    borderRadius: 10, padding: '12px 14px', margin: '0 0 32px',
  },
  noticeText: { margin: 0, fontSize: 13, lineHeight: 1.55, color: MUTED_TEXT },

  // Primary-red base (white text 5.70:1; the brighter dot-red was 3.74:1, too low for the
  // small buttons). Used with className "btn-red-dark", whose hover darkens to sub-red-2.
  btnPrimary: {
    background: 'var(--dlw-primary-red)', border: 'none', borderRadius: 999,
    padding: '12px 28px', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 15, color: '#fff',
    transition: 'background 140ms',
  },
  // #5E5E5E on the grey is 5.01:1, so the greyed-out labels stay readable.
  btnPrimaryDisabled: { background: 'var(--dlw-border)', color: '#5E5E5E', cursor: 'not-allowed' },
  btnSmall: { padding: '9px 18px', fontSize: 13, whiteSpace: 'nowrap' },

  // ── Chat ──
  // Fills the height left above the Build button, capped on tall windows. overflow:clip (not
  // hidden) keeps the rounded corners but is not a scroll container, so the box never shrinks
  // below its content: in a very short window or at high zoom the page scrolls instead of the
  // conversation collapsing or the answer box being cut off.
  chatShell: {
    display: 'flex', flexDirection: 'column',
    flex: '1 1 0', maxHeight: 720,
    border: '1px solid var(--dlw-border)', borderRadius: 12,
    background: '#fff', boxShadow: '0 16px 36px -20px rgba(16,24,32,0.30)',
    overflow: 'clip',
  },
  chatToolbar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
    padding: '14px 18px', borderBottom: '1px solid var(--dlw-border)', background: 'var(--dlw-surface)',
  },
  chatToolbarHint: { margin: 0, fontSize: 13, fontWeight: 300, color: MUTED_TEXT },

  // minHeight: always room for the latest message, however little space the window leaves.
  messages: { flex: '1 1 0', minHeight: 160, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 12 },
  // position:relative contains the hidden speaker label (srOnly is absolute), so it scrolls
  // with the list instead of stretching the pinned chat page.
  bubble: {
    position: 'relative', maxWidth: '78%', padding: '10px 14px', borderRadius: 14,
    fontSize: 14.5, lineHeight: 1.55, whiteSpace: 'pre-wrap',
  },
  bubbleUser: { alignSelf: 'flex-end', background: 'var(--dlw-primary-red)', color: '#fff', borderBottomRightRadius: 4 },
  bubbleAssistant: { alignSelf: 'flex-start', background: 'var(--dlw-surface)', color: 'var(--dlw-text)', borderBottomLeftRadius: 4 },
  chatError: { margin: 0, fontSize: 13, color: 'var(--dlw-primary-red)' },
  typingDots: { display: 'inline-flex', gap: 4, alignItems: 'center', height: '1.55em', verticalAlign: 'bottom' },
  typingDotsAfterText: { marginLeft: 8 },
  // 4.89:1 on the bubble grey; the animation never dims below 3:1 (non-text contrast).
  typingDot: { width: 6, height: 6, borderRadius: '50%', background: MUTED_TEXT },

  privacyNotice: { fontSize: 11.5, fontWeight: 300, color: MUTED_TEXT, textAlign: 'center', padding: '8px 18px 0', margin: 0 },

  buildBar: {
    display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
    gap: 8, marginTop: 16,
  },
  buildError: { margin: 0, fontSize: 13, color: 'var(--dlw-primary-red)', textAlign: 'center' },

  chatForm: { display: 'flex', gap: 10, alignItems: 'flex-end', padding: '14px 18px', borderTop: '1px solid var(--dlw-border)' },
  // overflowY is set by the auto-grow effect (only scrolls once maxHeight is reached).
  chatInput: {
    flex: 1, padding: '11px 16px', borderRadius: 16,
    border: '1.5px solid var(--dlw-border)', fontFamily: 'var(--dlw-font-body)',
    // A transparent outline, not none: invisible normally, but Windows high-contrast mode
    // paints it, so the focus stays visible there too.
    fontSize: 14.5, lineHeight: 1.45, color: 'var(--dlw-text)', outline: '2px solid transparent',
    boxSizing: 'border-box', resize: 'none', maxHeight: 140,
  },
  // Visible keyboard focus: the inline outline:none above removes the browser's ring.
  chatInputFocused: { border: '1.5px solid var(--dlw-primary-red)' },
  chatSend: { padding: '11px 24px', flexShrink: 0 },

  // Read by screen readers, invisible on screen.
  srOnly: {
    position: 'absolute', width: 1, height: 1, padding: 0, margin: -1,
    overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0,
  },

  // ── Building ──
  buildingWrap: {
    minHeight: 400, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: 6, textAlign: 'center',
  },
  buildingTitle: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 20, color: 'var(--dlw-black)', margin: '18px 0 0', outline: 'none' },
  // Headings that receive focus programmatically (tabIndex -1) are not controls: no ring.
  focusTarget: { outline: 'none' },
  buildingSub: { fontSize: 14, fontWeight: 300, color: MUTED_TEXT, margin: '6px 0 0', maxWidth: '40ch' },
} satisfies Record<string, CSSProperties>

// ── Welcome screen ──────────────────────────────────────────────────────────

function WelcomeScreen({ onStart }: { onStart: () => void }) {
  return (
    <div>
      <p style={s.eyebrow}>AI Opportunity Interview</p>
      <h1 style={s.heading}>Let&rsquo;s find where AI can actually help you.</h1>
      <p style={s.body}>
        A short conversation about your real, everyday work: the systems you're in, the tasks
        that eat your week, the bits you'd love to hand off. It takes about 15 minutes, and there
        are no wrong answers; the more concrete you are, the better the result. At the end, you
        get a{' '}
        <strong style={{ fontWeight: 600, color: 'var(--dlw-black)' }}>personalised playbook</strong>:
        practical AI use cases and clear next steps, made for you.
      </p>

      <div style={s.stepsGrid}>
        <div style={s.stepCard}>
          <span style={s.stepLabel}>1 &middot; Talk</span>
          <p style={s.stepText}>A few questions about your week and the tools you use.</p>
        </div>
        <div style={s.stepCard}>
          <span style={s.stepLabel}>2 &middot; Build</span>
          <p style={s.stepText}>We turn the conversation into your playbook.</p>
        </div>
        <div style={s.stepCard}>
          <span style={s.stepLabel}>3 &middot; Start</span>
          <p style={s.stepText}>You leave with a first step you can take today.</p>
        </div>
      </div>

      <div style={s.notice}>
        <span aria-hidden="true">🔒</span>
        <p style={s.noticeText}>
          Conversations are stored and may be reviewed by hub admins to improve the hub.
        </p>
      </div>

      <button type="button" className="btn-red-dark" style={s.btnPrimary} onClick={onStart}>
        Start the interview <span aria-hidden="true">→</span>
      </button>
    </div>
  )
}

// ── Needs-assessment notice ──────────────────────────────────────────────────
// Shown instead of Welcome/Chat when the learner hasn't completed their assessment
// yet (and isn't an admin): mirrors the backend's assessment gate on the write paths,
// so a learner never sees a 403 or an un-winnable "Try again" button.

function NeedsAssessmentScreen({ onGoToAssessment }: { onGoToAssessment: () => void }) {
  return (
    <div>
      <p style={s.eyebrow}>AI Opportunity Interview</p>
      <h1 style={s.heading}>Complete your assessment first</h1>
      <p style={s.body}>
        The interview builds on your assessment answers, so it opens once your assessment is done.
      </p>
      <button type="button" className="btn-red-dark" style={s.btnPrimary} onClick={onGoToAssessment}>
        Go to your assessment <span aria-hidden="true">→</span>
      </button>
    </div>
  )
}

// ── Chat screen ──────────────────────────────────────────────────────────────

/** What inline styles can't express: the typing-dot keyframes (the dots never dim below
 *  75%, so they stay above 3:1) and the conversation's inset keyboard focus ring (inset, so
 *  the chat box's clipping can't cut it off). Local, with an `iv-` prefix, the same idiom as
 *  JourneyHome's jh-pulse. */
const CHAT_CSS = `
@keyframes iv-typing { 0%, 60%, 100% { opacity: .75; transform: translateY(0) } 30% { opacity: 1; transform: translateY(-3px) } }
.iv-typing-dot { animation: iv-typing 1.2s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { .iv-typing-dot { animation: none; opacity: 1; } }
.iv-conversation:focus-visible { outline: 2px solid var(--dlw-primary-red); outline-offset: -2px; }
`

/** Three pulsing dots while the interviewer's reply is on the way: alone in a bubble before
 *  the first words, after the words while the reply is still streaming. Screen readers get
 *  "The interviewer is typing." from the page's live region instead. */
function TypingDots({ afterText = false }: { afterText?: boolean }) {
  return (
    <span style={{ ...s.typingDots, ...(afterText ? s.typingDotsAfterText : {}) }} aria-hidden="true">
      <span className="iv-typing-dot" style={s.typingDot} />
      <span className="iv-typing-dot" style={{ ...s.typingDot, animationDelay: '0.15s' }} />
      <span className="iv-typing-dot" style={{ ...s.typingDot, animationDelay: '0.3s' }} />
    </span>
  )
}

/** Chat messages as displayed: the readiness marker stripped, plus the build-offer signal. */
function toDisplay(messages: ReturnType<typeof useChat>['messages']) {
  return messages.map(m =>
    m.role === 'assistant'
      ? { role: m.role, ...parseReadySignal(m.content) }
      : { role: m.role, text: m.content, ready: false },
  )
}

/** Grow the answer box with its content; CSS maxHeight caps it. Measured with the scrollbar
 *  off (a scrollbar left over from a longer text narrows the box and over-measures), and
 *  border-box means the height includes the borders, which scrollHeight doesn't. It only
 *  scrolls once the cap is reached, so a sub-pixel gap never shows a needless scrollbar. */
function growTextarea(el: HTMLTextAreaElement) {
  el.style.overflowY = 'hidden'
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight + el.offsetHeight - el.clientHeight}px`
  el.style.overflowY = el.scrollHeight > el.clientHeight + 1 ? 'auto' : 'hidden'
}

interface ChatScreenProps {
  chat: ReturnType<typeof useChat>
  buildError: string | null
  onBuildPlaybook: () => void
  opening: boolean
  openError: string | null
  onRetryOpen: () => void
}

function ChatScreen({ chat, buildError, onBuildPlaybook, opening, openError, onRetryOpen }: ChatScreenProps) {
  const [input, setInput] = useState('')
  const messagesRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const buildRef = useRef<HTMLButtonElement>(null)

  // Strip the readiness marker for display and detect the interviewer's build-offer signal.
  // `modelReady` is sticky: the marker lives in a past assistant message, which persists.
  const display = toDisplay(chat.messages)
  const modelReady = display.some(d => d.ready)
  const answerCount = chat.messages.filter(m => m.role === 'user').length
  // Primary: reveal when the interviewer signals it's ready. Fallback: after the floor.
  const canBuild = modelReady || answerCount >= FALLBACK_MIN_ANSWERS
  const buildDisabled = !canBuild || chat.loading
  const toolbarHint = chatToolbarHint({ modelReady, canBuild, answerCount, hasMessages: display.length > 0 })
  const buildStatus = buildButtonStatus({ canBuild, loading: chat.loading })
  const [inputFocused, setInputFocused] = useState(false)
  // Back from a failed build: focus starts on the Build button next to its error (moving
  // it to the answer box could cut the error announcement short). Cleared once the learner
  // sends, so later turns focus the answer box as usual.
  const focusBuildFirstRef = useRef(Boolean(buildError))

  // Pin the latest turn into view as messages arrive and stream in (keyed on message
  // count + the last message's length so it follows both new turns and streaming growth).
  const lastContentLen = chat.messages[chat.messages.length - 1]?.content.length ?? 0
  useEffect(() => {
    const el = messagesRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [chat.messages.length, lastContentLen])

  // Grow the input vertically with its content (long / multi-line answers).
  useEffect(() => {
    if (inputRef.current) growTextarea(inputRef.current)
  }, [input])

  // Re-measure when the box gets narrower or wider (window resize, zoom): the text rewraps,
  // and with the scrollbar off it would otherwise be clipped until the next keystroke.
  useEffect(() => {
    const el = inputRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    let width = el.clientWidth
    const observer = new ResizeObserver(() => {
      if (el.clientWidth === width) return // our own height changes, not a new width
      width = el.clientWidth
      growTextarea(el)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Keep the input focused across turns: the textarea stays enabled (so it never
  // loses focus on send), and we re-assert focus when a streamed reply finishes.
  useEffect(() => {
    if (chat.loading) {
      focusBuildFirstRef.current = false
      return
    }
    if (focusBuildFirstRef.current) buildRef.current?.focus()
    else inputRef.current?.focus()
  }, [chat.loading])

  function submit() {
    const trimmed = input.trim()
    if (!trimmed || chat.loading) return
    setInput('')
    void chat.send(trimmed)
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    submit()
  }

  // Enter sends; Shift+Enter inserts a newline so learners can draft multi-line answers.
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div style={s.chatScreen}>
      <h1 style={s.srOnly}>AI Opportunity Interview</h1>
      <style>{CHAT_CSS}</style>

      <div style={s.chatShell}>
        <div style={s.chatToolbar}>
          <p id={BUILD_HINT_ID} style={s.chatToolbarHint}>{toolbarHint}</p>
        </div>

        {/* Not a live region (the page-level one announces replies once, complete).
            Focusable so keyboard users can scroll back through the conversation. */}
        <div
          style={s.messages}
          ref={messagesRef}
          role="region"
          aria-label="Conversation"
          tabIndex={0}
          className="iv-conversation"
        >
          {chat.messages.length === 0 && opening && (
            <div style={{ ...s.bubble, ...s.bubbleAssistant }}>
              <span style={s.srOnly}>The interviewer is typing</span>
              <TypingDots />
            </div>
          )}
          {chat.messages.length === 0 && !opening && openError && (
            <div style={{ textAlign: 'center', marginTop: 40 }}>
              <p role="alert" style={s.chatError}>{openError}</p>
              <button type="button" className="btn-red-dark" style={{ ...s.btnPrimary, ...s.btnSmall, marginTop: 12 }} onClick={onRetryOpen}>
                Try again
              </button>
            </div>
          )}
          {display.map((m, i) => {
            const view = bubbleView(display, i, chat.loading)
            if (view === 'hidden') return null
            return (
              <div
                key={i}
                style={{ ...s.bubble, ...(m.role === 'user' ? s.bubbleUser : s.bubbleAssistant) }}
              >
                {view === 'typing' ? (
                  <>
                    <span style={s.srOnly}>The interviewer is typing</span>
                    <TypingDots />
                  </>
                ) : (
                  <>
                    <span style={s.srOnly}>{m.role === 'user' ? 'You: ' : 'Interviewer: '}</span>
                    {m.text}
                    {view === 'streaming' && <TypingDots afterText />}
                  </>
                )}
              </div>
            )
          })}
          {chat.error && <p role="alert" style={s.chatError}>{chat.error}</p>}
        </div>

        <p style={s.privacyNotice}>
          Conversations are stored and may be reviewed by hub admins to improve the hub.
        </p>

        <form onSubmit={onSubmit} style={s.chatForm}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            onFocus={() => setInputFocused(true)}
            onBlur={() => setInputFocused(false)}
            aria-label="Type your answer"
            aria-describedby={INPUT_HELP_ID}
            placeholder="Type your answer (Shift+Enter for a new line)"
            style={{ ...s.chatInput, ...(inputFocused ? s.chatInputFocused : {}) }}
            rows={1}
            maxLength={MAX_INPUT}
          />
          {/* The placeholder's key help disappears once the learner types; keep it available. */}
          <span id={INPUT_HELP_ID} style={s.srOnly}>Press Enter to send, Shift+Enter for a new line.</span>
          {/* Stays "Send" while a reply streams: the typing dots next to the reply show the
              interviewer is still busy until it has finished. */}
          <button
            type="submit"
            className="btn-red-dark"
            style={{ ...s.btnPrimary, ...s.chatSend, ...((chat.loading || !input.trim()) ? s.btnPrimaryDisabled : {}) }}
            disabled={chat.loading || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>

      {/* Always rendered, greyed out until the build is available, so nothing below the
          chat shifts when it unlocks. Also disabled while a reply streams, so a build never
          misses the interviewer's last turn. A failed build reports right here, where the
          learner clicked. */}
      <div style={s.buildBar}>
        {buildError && <p role="alert" style={s.buildError}>{buildError}</p>}
        <button
          ref={buildRef}
          type="button"
          className="btn-red-dark"
          style={{ ...s.btnPrimary, ...s.btnSmall, ...(buildDisabled ? s.btnPrimaryDisabled : {}) }}
          onClick={onBuildPlaybook}
          disabled={buildDisabled}
          aria-describedby={buildStatus ? `${BUILD_STATUS_ID} ${BUILD_HINT_ID}` : BUILD_HINT_ID}
        >
          Build my playbook
        </button>
        {buildStatus && <span id={BUILD_STATUS_ID} style={s.srOnly}>{buildStatus}</span>}
      </div>
    </div>
  )
}

// ── Building screen ──────────────────────────────────────────────────────────

function BuildingScreen() {
  return (
    <div style={s.buildingWrap}>
      {/* A plain block wrapper: the shared Spinner stretches (flex: 1) in a flex column,
          which pushed the title far below it. */}
      <div><Spinner /></div>
      <h1 id={BUILDING_HEADING_ID} tabIndex={-1} style={s.buildingTitle}>Building your playbook</h1>
      <p style={s.buildingSub}>
        Turning our conversation into practical use cases and clear next steps. This usually
        takes a minute or two, so hang tight and keep this tab open. Your playbook will appear here.
      </p>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Interview() {
  const chat = useChat('interview')
  const navigate = useNavigate()
  const { role } = useAuth()
  const [state, setState] = useState<InterviewState | null>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)
  const [opening, setOpening] = useState(false)
  const [openError, setOpenError] = useState<string | null>(null)
  // The opener finished (success or failure). If it "succeeded" but no greeting loaded (the
  // conversation fetch failed quietly), the learner still gets an error and Try again.
  const [openerSettled, setOpenerSettled] = useState(false)
  // A playbook built during this visit (not one reopened later): its arrival is announced.
  const [builtNow, setBuiltNow] = useState(false)
  const openedRef = useRef(false)

  useEffect(() => {
    let cancelled = false

    // Mirrors the backend's require_completed_assessment gate on the write paths, so a
    // learner without a completed assessment sees a calm notice instead of a Welcome/Chat
    // screen that would 403 on Start/Send. A completed playbook (data.status === 'complete')
    // never reaches this check, so it always renders regardless of assessment state. If the
    // journey call fails, fall back to today's behaviour — the backend gate still protects.
    async function needsAssessment(interviewStatus: InterviewState['status']): Promise<boolean> {
      try {
        const { data } = await client.GET('/api/me/journey')
        if (!data) return false
        const tile = resolveInterviewTile({
          componentLocked: false,
          role,
          surveyStatus: data.survey_status,
          interviewStatus,
        })
        return tile === 'needs_assessment'
      } catch {
        return false
      }
    }

    async function load() {
      try {
        const data = await getInterviewState()
        if (cancelled) return
        setState(data)

        if (data.status !== 'complete' && (await needsAssessment(data.status))) {
          if (cancelled) return
          setPhase('needs_assessment')
          return
        }
        if (cancelled) return

        if (data.status === 'not_started') {
          setPhase('welcome')
        } else if (data.status === 'in_progress') {
          openedRef.current = true
          setPhase('chat')
          if (data.conversation_id) void chat.loadConversation(data.conversation_id)
        } else {
          setPhase('done')
        }
      } catch (e) {
        if (cancelled) return
        setLoadError(e instanceof Error ? e.message : 'Failed to load your interview.')
      }
    }

    load()
    return () => { cancelled = true }
    // Mount-only: chat.loadConversation is stable (useCallback with no deps), and this
    // effect must run exactly once regardless of the fresh `chat` object identity each render.
    // `role` (read by needsAssessment) is safe to capture once: App.tsx renders no route until
    // the auth restore has finished, so it is final by the time this page mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // The building and playbook screens start at the top, even when the learner had scrolled
  // down to reach the Build button. Focus moves to their heading, since the Build button the
  // learner clicked is gone (a freshly built playbook only; a reopened one keeps the default).
  useEffect(() => {
    if (phase === 'building' || phase === 'done') window.scrollTo(0, 0)
    if (phase === 'building') document.getElementById(BUILDING_HEADING_ID)?.focus()
    if (phase === 'done' && builtNow) document.getElementById(PLAYBOOK_HEADING_ID)?.focus()
  }, [phase, builtNow])

  function runOpener() {
    setOpening(true)
    setOpenError(null)
    setOpenerSettled(false)
    openInterview()
      .then(({ conversation_id }) => chat.loadConversation(conversation_id))
      .catch((e: unknown) =>
        setOpenError(e instanceof Error ? e.message : 'Could not start the interview.'),
      )
      .finally(() => {
        setOpening(false)
        setOpenerSettled(true)
      })
  }

  function handleStart() {
    setPhase('chat')
    if (openedRef.current) return
    openedRef.current = true
    runOpener()
  }

  function handleBuildPlaybook() {
    setPhase('building')
    setBuildError(null)
    buildPlaybook()
      .then(pb => {
        setState({ status: 'complete', playbook: pb })
        setBuiltNow(true)
        setPhase('done')
      })
      .catch((e: unknown) => {
        setBuildError(e instanceof Error ? e.message : 'Could not build your playbook.')
        setPhase('chat')
      })
  }

  const chatLayout = phase === 'chat' && !loadError
  const shownOpenError =
    openError ??
    (openerSettled && chat.messages.length === 0 ? 'Could not start the interview. Please try again.' : null)
  const announcement =
    phase === 'chat'
      ? liveAnnouncement(toDisplay(chat.messages), { loading: chat.loading, opening, error: chat.error })
      : phase === 'building'
        ? 'Building your playbook. This usually takes a minute or two.'
        : phase === 'done' && builtNow
          ? 'Your playbook is ready.'
          : ''

  return (
    <div style={chatLayout ? { ...s.page, ...s.pageChat } : s.page}>
      {/* Short on purpose: AppNav's 64px bar can't fit a two-line title. */}
      <AppNav backTo="/" title="Interview" />
      {/* The page's only live region, mounted once for every phase so screen readers pick up
          each change: replies once complete (never half-written fragments), then the build. */}
      <div aria-live="polite" style={s.srOnly}>{announcement}</div>
      <main style={chatLayout ? { ...s.main, ...s.mainChat } : s.main}>
        {loadError ? (
          <p style={s.errorMsg}>{loadError}</p>
        ) : phase === 'loading' ? (
          <div style={s.loadingWrap}><Spinner /></div>
        ) : phase === 'needs_assessment' ? (
          <NeedsAssessmentScreen onGoToAssessment={() => navigate('/assessment')} />
        ) : phase === 'welcome' ? (
          <WelcomeScreen onStart={handleStart} />
        ) : phase === 'chat' ? (
          <ChatScreen
            chat={chat}
            buildError={buildError}
            onBuildPlaybook={handleBuildPlaybook}
            opening={opening}
            openError={shownOpenError}
            onRetryOpen={runOpener}
          />
        ) : phase === 'building' ? (
          <BuildingScreen />
        ) : state?.playbook ? (
          // The heading lives here, not in Playbook: the admin panel renders Playbook too.
          <div>
            <p style={s.eyebrow}>AI Opportunity Interview</p>
            <h1 id={PLAYBOOK_HEADING_ID} tabIndex={-1} style={{ ...s.heading, ...s.focusTarget }}>Your AI playbook</h1>
            <p style={s.body}>Built from your interview. You can come back to it any time from the hub.</p>
            <Playbook shared={state.playbook} />
          </div>
        ) : (
          <p style={s.errorMsg}>Your playbook isn&rsquo;t available right now. Please refresh.</p>
        )}
      </main>
    </div>
  )
}
