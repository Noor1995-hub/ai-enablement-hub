// AI Opportunity Interview — the real journey page behind /interview, replacing the
// ComingSoon placeholder. A small state machine: welcome → chat → building → done.
// Chat rendering mirrors components/ChatPanel.tsx's bubble styling and streaming-aware
// input, but isn't a reuse of ChatPanel itself (its "+ New conversation"/History header
// doesn't fit a single interview conversation). Welcome copy/structure follows
// docs/design-prototypes/ai-interviewer/mockup.html's "Welcome" screen, restyled onto
// the hub's real design system (index.css --dlw-* tokens), the same idiom as
// pages/JourneyHome.tsx and pages/Assessment.tsx.
import { useEffect, useState, type CSSProperties, type FormEvent } from 'react'
import AppNav from '../components/AppNav'
import Spinner from '../components/Spinner'
import Playbook from '../components/interview/Playbook'
import { buildPlaybook, getInterviewState } from '../lib/interviewApi'
import { useChat } from '../lib/useChat'
import type { InterviewState } from '../types/domain'

type Phase = 'loading' | 'welcome' | 'chat' | 'building' | 'done'

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

  chatForm: { display: 'flex', gap: 10, alignItems: 'center', padding: '14px 18px', borderTop: '1px solid var(--dlw-border)' },
  chatInput: {
    flex: 1, padding: '11px 16px', borderRadius: 999,
    border: '1.5px solid var(--dlw-border)', fontFamily: 'var(--dlw-font-body)',
    fontSize: 14.5, color: 'var(--dlw-text)', outline: 'none', boxSizing: 'border-box',
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

// ── Chat screen ──────────────────────────────────────────────────────────────

interface ChatScreenProps {
  chat: ReturnType<typeof useChat>
  buildError: string | null
  onBuildPlaybook: () => void
}

function ChatScreen({ chat, buildError, onBuildPlaybook }: ChatScreenProps) {
  const [input, setInput] = useState('')

  // The placeholder assistant bubble `send()` appends while streaming starts out
  // empty — don't count that as "the interviewer has replied" or the button would
  // enable a beat before any real content lands.
  const hasAssistantReply = chat.messages.some(m => m.role === 'assistant' && m.content.trim().length > 0)

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || chat.loading) return
    setInput('')
    void chat.send(trimmed)
  }

  return (
    <div>
      <div style={s.chatShell}>
        <div style={s.chatToolbar}>
          <p style={s.chatToolbarHint}>
            {hasAssistantReply
              ? "You can keep chatting as long as you like — build your playbook whenever you're ready."
              : 'Say hello to get started.'}
          </p>
          <button
            type="button"
            className="btn-red"
            style={{ ...s.btnPrimary, ...s.btnSmall, ...(!hasAssistantReply ? s.btnPrimaryDisabled : {}) }}
            disabled={!hasAssistantReply}
            onClick={onBuildPlaybook}
          >
            Build my playbook
          </button>
        </div>

        <div style={s.messages}>
          {chat.messages.length === 0 && (
            <p style={s.emptyHint}>Say hello to begin the interview.</p>
          )}
          {chat.messages.map((m, i) => (
            <div
              key={i}
              style={{ ...s.bubble, ...(m.role === 'user' ? s.bubbleUser : s.bubbleAssistant) }}
            >
              {m.content}
            </div>
          ))}
          {chat.error && <p style={s.chatError}>{chat.error}</p>}
          {buildError && <p style={s.chatError}>{buildError}</p>}
        </div>

        <p style={s.privacyNotice}>
          Conversations are stored and may be reviewed by hub admins to improve the hub.
        </p>

        <form onSubmit={onSubmit} style={s.chatForm}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type your answer…"
            style={s.chatInput}
            disabled={chat.loading}
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
        Turning our conversation into practical use-cases and clear next steps.
      </p>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Interview() {
  const chat = useChat('interview')
  const [state, setState] = useState<InterviewState | null>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data = await getInterviewState()
        if (cancelled) return
        setState(data)
        if (data.status === 'not_started') {
          setPhase('welcome')
        } else if (data.status === 'in_progress') {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
        ) : phase === 'welcome' ? (
          <WelcomeScreen onStart={() => setPhase('chat')} />
        ) : phase === 'chat' ? (
          <ChatScreen chat={chat} buildError={buildError} onBuildPlaybook={handleBuildPlaybook} />
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
