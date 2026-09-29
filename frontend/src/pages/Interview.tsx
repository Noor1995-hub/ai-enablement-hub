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
import { useChat } from '../lib/useChat'
import type { InterviewState } from '../types/domain'

type Phase = 'loading' | 'welcome' | 'chat' | 'building' | 'done' | 'needs_assessment'

/** Fallback floor: if the interviewer never signals readiness, the manual build still
 *  unlocks once the learner has sent this many answers, so no one is ever stuck. The
 *  primary path is the model's own readiness signal (READY_MARKER). The server enforces the
 *  same floor (backend/src/services/interview_service.py _MIN_ANSWERS_WITHOUT_OFFER): keep
 *  the two numbers equal. */
const FALLBACK_MIN_ANSWERS = 6

/** Server caps chat message content at 4000 chars (backend/src/schemas/chat.py); over that is
 *  a 422. Guard the input so it can't be exceeded. */
const MAX_INPUT = 4000

/** The interviewer appends this marker (backend/prompts/interview.md) to the turn where it
 *  offers to build the playbook — the signal to reveal the button. Always stripped from
 *  display; the learner never sees it. Kept in sync with
 *  backend/src/services/interview_marker.py, the backend's single home for the marker. */
const READY_MARKER = '[[READY_TO_BUILD]]'

/** The toolbar hint doubles as the Build button's description (why it is greyed out). */
const BUILD_HINT_ID = 'interview-build-hint'

/** Strip the readiness marker from an assistant message for display, and report whether the
 *  full marker has arrived. Also hides a trailing *partial* marker so it never flashes while
 *  the message streams in a few characters at a time. */
function parseReadySignal(content: string): { text: string; ready: boolean } {
  if (content.includes(READY_MARKER)) {
    return { text: content.split(READY_MARKER).join('').trimEnd(), ready: true }
  }
  const max = Math.min(content.length, READY_MARKER.length - 1)
  for (let n = max; n > 0; n--) {
    if (READY_MARKER.startsWith(content.slice(content.length - n))) {
      return { text: content.slice(0, content.length - n).trimEnd(), ready: false }
    }
  }
  return { text: content, ready: false }
}

const s = {
  page: { minHeight: '100vh', background: '#fff', display: 'flex', flexDirection: 'column' },
  main: { flex: 1, width: 'min(760px, 100%)', margin: '0 auto', padding: '44px 40px 80px', boxSizing: 'border-box' },

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
  body: { fontSize: 16, fontWeight: 300, color: 'var(--dlw-muted)', lineHeight: 1.65, margin: '0 0 28px', maxWidth: '58ch' },

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
  noticeText: { margin: 0, fontSize: 13, lineHeight: 1.55, color: 'var(--dlw-muted)' },

  btnPrimary: {
    background: 'var(--dlw-dot-red)', border: 'none', borderRadius: 999,
    padding: '12px 28px', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 15, color: '#fff',
    transition: 'background 140ms',
  },
  btnPrimaryDisabled: { background: 'var(--dlw-border)', color: 'var(--dlw-muted)', cursor: 'not-allowed' },
  btnSmall: { padding: '9px 18px', fontSize: 13, whiteSpace: 'nowrap' },

  // ── Chat ──
  chatShell: {
    display: 'flex', flexDirection: 'column',
    height: 'min(640px, 70vh)', minHeight: 420,
    border: '1px solid var(--dlw-border)', borderRadius: 12,
    background: '#fff', boxShadow: '0 16px 36px -20px rgba(16,24,32,0.30)',
    overflow: 'hidden',
  },
  chatToolbar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
    padding: '14px 18px', borderBottom: '1px solid var(--dlw-border)', background: 'var(--dlw-surface)',
  },
  chatToolbarHint: { margin: 0, fontSize: 13, fontWeight: 300, color: 'var(--dlw-muted)' },

  messages: { flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 12 },
  emptyHint: { margin: '40px 0 0', fontSize: 14, fontWeight: 300, color: 'var(--dlw-muted)', textAlign: 'center' },
  bubble: {
    maxWidth: '78%', padding: '10px 14px', borderRadius: 14,
    fontSize: 14.5, lineHeight: 1.55, whiteSpace: 'pre-wrap',
  },
  bubbleUser: { alignSelf: 'flex-end', background: 'var(--dlw-primary-red)', color: '#fff', borderBottomRightRadius: 4 },
  bubbleAssistant: { alignSelf: 'flex-start', background: 'var(--dlw-surface)', color: 'var(--dlw-text)', borderBottomLeftRadius: 4 },
  chatError: { margin: 0, fontSize: 13, color: 'var(--dlw-primary-red)' },

  privacyNotice: { fontSize: 11.5, fontWeight: 300, color: 'var(--dlw-muted)', textAlign: 'center', padding: '8px 18px 0', margin: 0 },

  buildBar: {
    display: 'flex', justifyContent: 'center', alignItems: 'center',
    marginTop: 16,
  },

  chatForm: { display: 'flex', gap: 10, alignItems: 'flex-end', padding: '14px 18px', borderTop: '1px solid var(--dlw-border)' },
  chatInput: {
    flex: 1, padding: '11px 16px', borderRadius: 16,
    border: '1.5px solid var(--dlw-border)', fontFamily: 'var(--dlw-font-body)',
    fontSize: 14.5, lineHeight: 1.45, color: 'var(--dlw-text)', outline: 'none',
    boxSizing: 'border-box', resize: 'none', maxHeight: 140, overflowY: 'auto',
  },
  chatSend: { padding: '11px 24px', flexShrink: 0 },

  // ── Building ──
  buildingWrap: {
    minHeight: 400, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: 6, textAlign: 'center',
  },
  buildingTitle: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 20, color: 'var(--dlw-black)', margin: '18px 0 0' },
  buildingSub: { fontSize: 14, fontWeight: 300, color: 'var(--dlw-muted)', margin: '6px 0 0', maxWidth: '40ch' },
} satisfies Record<string, CSSProperties>

// ── Welcome screen ──────────────────────────────────────────────────────────

function WelcomeScreen({ onStart }: { onStart: () => void }) {
  return (
    <div>
      <p style={s.eyebrow}>AI Opportunity Interview</p>
      <h1 style={s.heading}>Let&rsquo;s find where AI can actually help you.</h1>
      <p style={s.body}>
        A short conversation about your real, everyday work &mdash; the systems you're in, the
        tasks that eat your week, the bits you'd love to hand off. There are no wrong answers;
        the more concrete you are, the better the result. At the end, you get a{' '}
        <strong style={{ fontWeight: 600, color: 'var(--dlw-black)' }}>personalized playbook</strong>:
        practical AI use-cases and clear next steps, made for you.
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

      <button type="button" className="btn-red" style={s.btnPrimary} onClick={onStart}>
        Start the interview →
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
      <button type="button" className="btn-red" style={s.btnPrimary} onClick={onGoToAssessment}>
        Go to your assessment →
      </button>
    </div>
  )
}

// ── Chat screen ──────────────────────────────────────────────────────────────

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

  // Strip the readiness marker for display and detect the interviewer's build-offer signal.
  // `modelReady` is sticky: the marker lives in a past assistant message, which persists.
  const display = chat.messages.map(m =>
    m.role === 'assistant'
      ? { role: m.role, ...parseReadySignal(m.content) }
      : { role: m.role, text: m.content, ready: false },
  )
  const modelReady = display.some(d => d.ready)
  const answerCount = chat.messages.filter(m => m.role === 'user').length
  // Primary: reveal when the interviewer signals it's ready. Fallback: after the floor.
  const canBuild = modelReady || answerCount >= FALLBACK_MIN_ANSWERS
  const buildDisabled = !canBuild || chat.loading
  const toolbarHint = chatToolbarHint({ modelReady, canBuild, answerCount })

  // Pin the latest turn into view as messages arrive and stream in (keyed on message
  // count + the last message's length so it follows both new turns and streaming growth).
  const lastContentLen = chat.messages[chat.messages.length - 1]?.content.length ?? 0
  useEffect(() => {
    const el = messagesRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [chat.messages.length, lastContentLen])

  // Grow the input vertically with its content (long / multi-line answers); CSS maxHeight caps it.
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [input])

  // Keep the input focused across turns: the textarea stays enabled (so it never
  // loses focus on send), and we re-assert focus when a streamed reply finishes.
  useEffect(() => {
    if (!chat.loading) inputRef.current?.focus()
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
    <div>
      <div style={s.chatShell}>
        <div style={s.chatToolbar}>
          <p id={BUILD_HINT_ID} style={s.chatToolbarHint}>{toolbarHint}</p>
        </div>

        <div style={s.messages} ref={messagesRef}>
          {chat.messages.length === 0 && opening && (
            <p style={s.emptyHint}>Starting the interview…</p>
          )}
          {chat.messages.length === 0 && !opening && openError && (
            <div style={{ textAlign: 'center', marginTop: 40 }}>
              <p style={s.chatError}>{openError}</p>
              <button type="button" className="btn-red" style={{ ...s.btnPrimary, ...s.btnSmall, marginTop: 12 }} onClick={onRetryOpen}>
                Try again
              </button>
            </div>
          )}
          {display.map((m, i) => (
            <div
              key={i}
              style={{ ...s.bubble, ...(m.role === 'user' ? s.bubbleUser : s.bubbleAssistant) }}
            >
              {m.text}
            </div>
          ))}
          {chat.error && <p style={s.chatError}>{chat.error}</p>}
          {buildError && <p style={s.chatError}>{buildError}</p>}
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
            placeholder="Type your answer…  (Shift+Enter for a new line)"
            style={s.chatInput}
            rows={1}
            maxLength={MAX_INPUT}
          />
          <button
            type="submit"
            className="btn-red"
            style={{ ...s.btnPrimary, ...s.chatSend, ...((chat.loading || !input.trim()) ? s.btnPrimaryDisabled : {}) }}
            disabled={chat.loading || !input.trim()}
          >
            {chat.loading ? '…' : 'Send'}
          </button>
        </form>
      </div>

      {/* Always rendered, greyed out until the build is available, so nothing below the
          chat shifts when it unlocks. Also disabled while a reply streams, so a build never
          misses the interviewer's last turn. */}
      <div style={s.buildBar}>
        <button
          type="button"
          className="btn-red"
          style={{ ...s.btnPrimary, ...s.btnSmall, ...(buildDisabled ? s.btnPrimaryDisabled : {}) }}
          onClick={onBuildPlaybook}
          disabled={buildDisabled}
          aria-describedby={BUILD_HINT_ID}
        >
          Build my playbook
        </button>
      </div>
    </div>
  )
}

// ── Building screen ──────────────────────────────────────────────────────────

function BuildingScreen() {
  return (
    <div style={s.buildingWrap}>
      <Spinner />
      <h2 style={s.buildingTitle}>Building your playbook&hellip;</h2>
      <p style={s.buildingSub}>
        Turning our conversation into practical use-cases and clear next steps. This usually takes
        a minute or two — hang tight and keep this tab open; your playbook will appear here.
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

  function runOpener() {
    setOpening(true)
    setOpenError(null)
    openInterview()
      .then(({ conversation_id }) => chat.loadConversation(conversation_id))
      .catch((e: unknown) =>
        setOpenError(e instanceof Error ? e.message : 'Could not start the interview.'),
      )
      .finally(() => setOpening(false))
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
        setPhase('done')
      })
      .catch((e: unknown) => {
        setBuildError(e instanceof Error ? e.message : 'Could not build your playbook.')
        setPhase('chat')
      })
  }

  return (
    <div style={s.page}>
      <AppNav backTo="/" title="AI Opportunity Interview" />
      <main style={s.main}>
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
            openError={openError}
            onRetryOpen={runOpener}
          />
        ) : phase === 'building' ? (
          <BuildingScreen />
        ) : state?.playbook ? (
          <Playbook shared={state.playbook} />
        ) : (
          <p style={s.errorMsg}>Your playbook isn&rsquo;t available right now. Please refresh.</p>
        )}
      </main>
    </div>
  )
}
