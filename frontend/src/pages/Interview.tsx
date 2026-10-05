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
import LanguagePicker from '../components/interview/LanguagePicker'
import LearnerPlaybook from '../components/interview/LearnerPlaybook'
import { INTERVIEW_CSS } from '../components/interview/interviewCss'
import { useAuth } from '../contexts/AuthContext'
import { resolveInterviewTile } from '../lib/interviewAccess'
import { buildPlaybook, getInterviewState, openInterview } from '../lib/interviewApi'
import { allToolbarHints, chatToolbarHint } from '../lib/interviewHints'
import { parseReadySignal } from '../lib/interviewReady'
import { useChat } from '../lib/useChat'
import { DEFAULT_INTERVIEW_LANGUAGE, INTERVIEW_STRINGS, PLAYBOOK_STRINGS, interviewError, type InterviewLanguage, type InterviewStrings } from '../lib/interviewStrings'
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
  // The redesign's warm-grey page (the brand's own token); each screen sits on a white sheet
  // (interviewCss.ts iv-sheet).
  page: { minHeight: '100vh', background: 'var(--dlw-warm-grey)', display: 'flex', flexDirection: 'column' },
  main: { flex: 1, width: '100%', margin: '0 auto', padding: '0 24px', boxSizing: 'border-box' },
  // Chat phase: the page is pinned to the window so the chat and the Build button always fit.
  // inset:0, not height:100vh: vh units disagree with the baked-in :root zoom (same approach
  // as LessonPage's edit mode). overflowY:auto, so a very short window scrolls, never clips.
  pageChat: { position: 'fixed', inset: 0, minHeight: 0, overflowY: 'auto' },
  // 908 = the 860px sheet plus 2 x 24px padding, so the chat lines up with the other screens.
  mainChat: { display: 'flex', flexDirection: 'column', width: 'min(908px, 100%)', padding: '24px 24px 20px' },
  chatScreen: { flex: 1, display: 'flex', flexDirection: 'column' },

  loadingWrap: { minHeight: 400, display: 'flex' },
  errorMsg: { fontSize: 15, fontWeight: 300, color: 'var(--dlw-primary-red)', margin: 0 },

  // ── Buttons ──
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
  // The white sheet's look (background, radius, shadow) comes from the iv-chat class; the
  // radius stays inline too because overflow:clip needs it on the same element.
  chatShell: {
    display: 'flex', flexDirection: 'column',
    flex: '1 1 0', maxHeight: 720, borderRadius: 20,
    overflow: 'clip',
  },
  // All hints share one grid cell (only the current one visible), so the cell is as tall as
  // the longest hint at this width: a hint that wraps to two lines on a narrow window or at
  // 200% zoom never makes the toolbar jump when the hint changes.
  chatToolbarHints: { display: 'grid', flex: 1, minWidth: 0 },
  chatToolbarHint: { gridArea: '1 / 1', margin: 0, fontSize: 13.5, fontWeight: 400, lineHeight: 1.45, color: MUTED_TEXT },
  chatToolbarHintSpacer: { visibility: 'hidden' },

  // minHeight: always room for the latest message, however little space the window leaves.
  messages: { flex: '1 1 0', minHeight: 160, overflowY: 'auto', padding: '26px 28px', display: 'flex', flexDirection: 'column', gap: 18 },
  // position:relative contains the hidden speaker label (srOnly is absolute), so it scrolls
  // with the list instead of stretching the pinned chat page. The look per speaker comes from
  // the iv-msg-ai / iv-msg-me classes (interviewCss.ts): interviewer turns as plain text with
  // the red dot, the learner's answers in warm-grey bubbles.
  bubble: { position: 'relative', lineHeight: 1.55, whiteSpace: 'pre-wrap' },
  chatError: { margin: 0, fontSize: 13, color: 'var(--dlw-primary-red)' },
  typingDots: { display: 'inline-flex', gap: 4, alignItems: 'center', height: '1.55em', verticalAlign: 'bottom' },
  typingDotsAfterText: { marginLeft: 8 },
  // 4.89:1 on the bubble grey; the animation never dims below 3:1 (non-text contrast).
  typingDot: { width: 6, height: 6, borderRadius: '50%', background: MUTED_TEXT },

  privacyNotice: { fontSize: 12, fontWeight: 400, color: MUTED_TEXT, padding: '4px 28px 14px', margin: 0 },

  buildBar: {
    display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
    gap: 8, marginTop: 16,
  },
  buildError: { margin: 0, fontSize: 13, color: 'var(--dlw-primary-red)', textAlign: 'center' },

  chatForm: { display: 'flex', gap: 10, alignItems: 'flex-end', padding: '14px 20px 6px 28px', borderTop: '1px solid var(--dlw-border)' },
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

  // Headings that receive focus programmatically (tabIndex -1) are not controls: no ring.
  focusTarget: { outline: 'none' },
} satisfies Record<string, CSSProperties>

// ── Welcome screen ──────────────────────────────────────────────────────────

function WelcomeScreen({
  onStart,
  language,
  onLanguageChange,
}: {
  onStart: () => void
  language: InterviewLanguage
  onLanguageChange: (language: InterviewLanguage) => void
}) {
  const t = INTERVIEW_STRINGS[language]
  const steps: [string, string][] = [
    [t.stepTalkLabel, t.stepTalkText], [t.stepBuildLabel, t.stepBuildText], [t.stepStartLabel, t.stepStartText],
  ]
  return (
    <div className="iv-sheet">
      {/* The learner's language choice (#83), first thing on the page: the screen switches
          as soon as one is picked, and the interview runs in it. */}
      <div className="iv-top">
        <LanguagePicker value={language} onChange={onLanguageChange} label={t.languagePickerLabel} />
      </div>
      {/* No eyebrow above the heading here: the heading says it on its own. */}
      <h1 className="iv-h1">{t.welcomeHeading}</h1>
      <p className="iv-lead">
        {t.welcomeBodyBefore}<strong>{t.welcomeBodyStrong}</strong>{t.welcomeBodyAfter}
      </p>
      {/* The three steps really are a sequence: a line with the logo's red dots. */}
      <ol className="iv-steps">
        {steps.map(([label, text]) => (
          <li key={label}><span className="iv-dot" aria-hidden="true" /><strong>{label}</strong><span>{text}</span></li>
        ))}
      </ol>
      <div className="iv-start">
        <button type="button" className="btn-red-dark" style={{ ...s.btnPrimary, padding: '14px 32px', fontSize: 16 }} onClick={onStart}>
          {t.startButton}
        </button>
        <p className="iv-privacy">{t.privacyNotice}</p>
      </div>
    </div>
  )
}

// ── Needs-assessment notice ──────────────────────────────────────────────────
// Shown instead of Welcome/Chat when the learner hasn't completed their assessment
// yet (and isn't an admin): mirrors the backend's assessment gate on the write paths,
// so a learner never sees a 403 or an un-winnable "Try again" button.

function NeedsAssessmentScreen({ onGoToAssessment, t }: { onGoToAssessment: () => void; t: InterviewStrings }) {
  return (
    <div className="iv-sheet">
      <h1 className="iv-h1">{t.needsAssessmentHeading}</h1>
      <p className="iv-lead">{t.needsAssessmentText}</p>
      <button type="button" className="btn-red-dark" style={s.btnPrimary} onClick={onGoToAssessment}>
        {t.needsAssessmentButton}
      </button>
    </div>
  )
}

// ── Chat screen ──────────────────────────────────────────────────────────────

/** A quiet speech-bubble outline next to "Your interviewer" (redesign D): the black disc with
 *  the logo dot was too prominent. Decorative; the name next to it says who it is. */
function InterviewerMark() {
  return (
    <svg className="iv-mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {/* Path written with commas, not spaces: the house-style guard reads a capitalised
          literal with spaces as prose. */}
      <path d="M4,5.5A2.5,2.5,0,0,1,6.5,3h11A2.5,2.5,0,0,1,20,5.5v8a2.5,2.5,0,0,1-2.5,2.5H10l-4.2,3.6c-.5.4-1.3.1-1.3-.6V16A2.5,2.5,0,0,1,4,13.5z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

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
  language: InterviewLanguage
}

function ChatScreen({ chat, buildError, onBuildPlaybook, opening, openError, onRetryOpen, language }: ChatScreenProps) {
  const t = INTERVIEW_STRINGS[language]
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
  const toolbarHint = chatToolbarHint({ modelReady, canBuild, answerCount, hasMessages: display.length > 0 }, language)
  const buildStatus = buildButtonStatus({ canBuild, loading: chat.loading }, language)
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
      <h1 style={s.srOnly}>{t.eyebrow}</h1>
      <style>{CHAT_CSS}</style>

      <div className="iv-chat" style={s.chatShell}>
        <div className="iv-chat-head">
          <InterviewerMark />
          <div style={{ flex: 1, minWidth: 0 }}>
            <p className="iv-who">{t.interviewerName}</p>
            <div style={s.chatToolbarHints}>
              <p id={BUILD_HINT_ID} style={s.chatToolbarHint}>{toolbarHint}</p>
              {/* Hidden (to screen readers too): they only hold the toolbar's height. */}
              {allToolbarHints(language).filter(hint => hint !== toolbarHint).map(hint => (
                <p key={hint} style={{ ...s.chatToolbarHint, ...s.chatToolbarHintSpacer }}>{hint}</p>
              ))}
            </div>
          </div>
        </div>

        {/* Not a live region (the page-level one announces replies once, complete).
            Focusable so keyboard users can scroll back through the conversation. */}
        <div
          style={s.messages}
          ref={messagesRef}
          role="region"
          aria-label={t.conversationLabel}
          tabIndex={0}
          className="iv-conversation"
        >
          {chat.messages.length === 0 && opening && (
            <div className="iv-msg-ai" style={s.bubble}>
              <span style={s.srOnly}>{t.typing}</span>
              <TypingDots />
            </div>
          )}
          {chat.messages.length === 0 && !opening && openError && (
            <div style={{ textAlign: 'center', marginTop: 40 }}>
              <p role="alert" style={s.chatError}>{openError}</p>
              <button type="button" className="btn-red-dark" style={{ ...s.btnPrimary, ...s.btnSmall, marginTop: 12 }} onClick={onRetryOpen}>
                {t.tryAgain}
              </button>
            </div>
          )}
          {display.map((m, i) => {
            const view = bubbleView(display, i, chat.loading)
            if (view === 'hidden') return null
            return (
              <div key={i} className={m.role === 'user' ? 'iv-msg-me' : 'iv-msg-ai'} style={s.bubble}>
                {view === 'typing' ? (
                  <>
                    <span style={s.srOnly}>{t.typing}</span>
                    <TypingDots />
                  </>
                ) : (
                  <>
                    <span style={s.srOnly}>{m.role === 'user' ? t.speakerYou : t.speakerInterviewer}</span>
                    {m.text}
                    {view === 'streaming' && <TypingDots afterText />}
                  </>
                )}
              </div>
            )
          })}
          {chat.error && <p role="alert" style={s.chatError}>{interviewError(chat.error, language, 'chatFailed')}</p>}
        </div>

        <p style={s.privacyNotice}>{t.privacyNotice}</p>

        <form onSubmit={onSubmit} style={s.chatForm}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            onFocus={() => setInputFocused(true)}
            onBlur={() => setInputFocused(false)}
            aria-label={t.answerLabel}
            aria-describedby={INPUT_HELP_ID}
            placeholder={t.answerPlaceholder}
            style={{ ...s.chatInput, ...(inputFocused ? s.chatInputFocused : {}) }}
            rows={1}
            maxLength={MAX_INPUT}
          />
          {/* The placeholder's key help disappears once the learner types; keep it available. */}
          <span id={INPUT_HELP_ID} style={s.srOnly}>{t.answerHelp}</span>
          {/* Stays "Send" while a reply streams: the typing dots next to the reply show the
              interviewer is still busy until it has finished. */}
          <button
            type="submit"
            className="btn-red-dark"
            style={{ ...s.btnPrimary, ...s.chatSend, ...((chat.loading || !input.trim()) ? s.btnPrimaryDisabled : {}) }}
            disabled={chat.loading || !input.trim()}
          >
            {t.send}
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
          {t.buildButton}
        </button>
        {buildStatus && <span id={BUILD_STATUS_ID} style={s.srOnly}>{buildStatus}</span>}
      </div>
    </div>
  )
}

// ── Building screen ──────────────────────────────────────────────────────────

function BuildingScreen({ language }: { language: InterviewLanguage }) {
  const t = INTERVIEW_STRINGS[language]
  const p = PLAYBOOK_STRINGS[language]
  // The playbook's own section order (LearnerPlaybook), so the list matches what appears.
  const parts = [p.doThisToday, p.useCases, p.nextMoves, p.holdingYouBack, p.whereYouAreToday]
  return (
    <div className="iv-sheet">
      {/* Indeterminate on purpose: the build reports no progress, so nothing pretends to. */}
      <div className="iv-track" aria-hidden="true"><span className="iv-dot iv-run" /></div>
      <h1 id={BUILDING_HEADING_ID} tabIndex={-1} className="iv-h1" style={s.focusTarget}>{t.buildingHeading}</h1>
      <p className="iv-lead" style={{ fontSize: 18, color: 'var(--dlw-text)' }}>{t.buildingText}</p>
      <p className="iv-small">{t.playbookWillContain}</p>
      <ul className="iv-parts">
        {parts.map(part => <li key={part}><span className="iv-dot" aria-hidden="true" />{part}</li>)}
      </ul>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Interview() {
  const chat = useChat('interview')
  const navigate = useNavigate()
  const { bypassesLocks } = useAuth()
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
  // The interview language (#83): picked on the welcome screen, then the interview's own.
  const [language, setLanguage] = useState<InterviewLanguage>(DEFAULT_INTERVIEW_LANGUAGE)
  const t = INTERVIEW_STRINGS[language]
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
          bypassesLocks,
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
        if (data.status !== 'not_started') setLanguage(data.language)

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
        setLoadError(e instanceof Error ? e.message : INTERVIEW_STRINGS.en.loadFailed)
      }
    }

    load()
    return () => { cancelled = true }
    // Mount-only: chat.loadConversation is stable (useCallback with no deps), and this
    // effect must run exactly once regardless of the fresh `chat` object identity each render.
    // `bypassesLocks` (read by needsAssessment) is safe to capture once: App.tsx renders no route until
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
    openInterview(language)
      .then(({ conversation_id, language: chosen }) => {
        setLanguage(chosen) // an interview that already existed keeps its own language
        return chat.loadConversation(conversation_id)
      })
      .catch((e: unknown) =>
        setOpenError(e instanceof Error ? e.message : INTERVIEW_STRINGS.en.openFailed),
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
        setState({ status: 'complete', playbook: pb, language })
        setBuiltNow(true)
        setPhase('done')
      })
      .catch((e: unknown) => {
        setBuildError(e instanceof Error ? e.message : INTERVIEW_STRINGS.en.buildFailed)
        setPhase('chat')
      })
  }

  const chatLayout = phase === 'chat' && !loadError
  // Errors in the interview's language (raw server text in English, the dictionary in Dutch).
  const shownOpenError =
    interviewError(openError, language, 'openFailed') ??
    (openerSettled && chat.messages.length === 0 ? t.openFailed : null)
  const shownBuildError = interviewError(buildError, language, 'buildFailed')
  const shownLoadError = interviewError(loadError, language, 'loadFailed')
  const announcement =
    phase === 'chat'
      ? liveAnnouncement(toDisplay(chat.messages), { loading: chat.loading, opening, error: chat.error }, language)
      : phase === 'building'
        ? t.buildingAnnouncement
        : phase === 'done' && builtNow
          ? t.readyAnnouncement
          : ''

  return (
    <div style={chatLayout ? { ...s.page, ...s.pageChat } : s.page}>
      <style>{INTERVIEW_CSS}</style>
      {/* Short on purpose: AppNav's 64px bar can't fit a two-line title. */}
      <AppNav backTo="/" title="Interview" />
      {/* The page's only live region, mounted once for every phase so screen readers pick up
          each change: replies once complete (never half-written fragments), then the build.
          It sits outside <main>, so it carries the interview's language itself. */}
      <div aria-live="polite" lang={language} style={s.srOnly}>{announcement}</div>
      <main lang={language} style={chatLayout ? { ...s.main, ...s.mainChat } : s.main}>
        {shownLoadError ? (
          <div className="iv-sheet"><p style={s.errorMsg}>{shownLoadError}</p></div>
        ) : phase === 'loading' ? (
          <div style={s.loadingWrap}><Spinner /></div>
        ) : phase === 'needs_assessment' ? (
          <NeedsAssessmentScreen onGoToAssessment={() => navigate('/assessment')} t={t} />
        ) : phase === 'welcome' ? (
          <WelcomeScreen onStart={handleStart} language={language} onLanguageChange={setLanguage} />
        ) : phase === 'chat' ? (
          <ChatScreen
            chat={chat}
            buildError={shownBuildError}
            onBuildPlaybook={handleBuildPlaybook}
            opening={opening}
            openError={shownOpenError}
            onRetryOpen={runOpener}
            language={language}
          />
        ) : phase === 'building' ? (
          <BuildingScreen language={language} />
        ) : state?.playbook ? (
          // The heading lives here, not in the playbook component. The admin card keeps its own
          // Playbook (components/interview/Playbook.tsx); this page renders the learner's.
          <div className="iv-sheet iv-sheet-wide">
            <header className="iv-pb-head">
              <h1 id={PLAYBOOK_HEADING_ID} tabIndex={-1} className="iv-h1" style={s.focusTarget}>{t.playbookHeading}</h1>
              <p>{t.playbookIntro}</p>
            </header>
            <LearnerPlaybook shared={state.playbook} language={language} />
          </div>
        ) : (
          <div className="iv-sheet"><p style={s.errorMsg}>{t.playbookUnavailable}</p></div>
        )}
      </main>
    </div>
  )
}
