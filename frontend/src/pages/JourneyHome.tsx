import React, { useEffect, useState, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { client } from '../api/client'
import { DEFAULT_HIDDEN, DEFAULT_LOCKED, type ComponentKey } from '../lib/constants'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import Spinner from '../components/Spinner'

/* ── Component definitions ── */
interface ModuleDef {
  key: ComponentKey
  title: string
  desc: string
  icon: string
  route: string
}

const MODULES: ModuleDef[] = [
  {
    key: 'assessment',
    title: 'Maturity assessment',
    desc: 'A short, guided conversation that maps how your team works with AI today, no quiz, no scores to worry about.',
    icon: '/assets/icons/red/insight-graph.svg',
    route: '/assessment',
  },
  {
    key: 'learning',
    title: 'My learning path',
    desc: 'A set of components chosen for you, based on what your assessment revealed. Built to fit around a busy week.',
    icon: '/assets/icons/red/lightbulb.svg',
    route: '/learning',
  },
  {
    key: 'interview',
    title: 'Interview',
    desc: 'A deeper one-to-one to explore your day-to-day and where AI could genuinely help you, specifically.',
    icon: '/assets/icons/red/connection-people.svg',
    route: '/interview',
  },
]

const MODULE_META: Record<ComponentKey, string> = {
  assessment: 'Takes about 10 minutes',
  learning: 'Unlocks after assessment',
  interview: 'About 15 minutes',
}

/** Resolved per-component display state ('hidden' components are filtered out). */
type ModuleState = 'done' | 'in_progress' | 'available' | 'locked' | 'hidden'

interface BadgeDef {
  label: string
  bg: string
  color: string
}

/* ── State badge config ── */
const BADGE: Partial<Record<ModuleState, BadgeDef>> = {
  done:        { label: 'Completed',   bg: '#EDFAF4', color: '#1D7A52' },
  in_progress: { label: 'In progress', bg: '#FEFCE8', color: '#A16207' },
  available:   { label: 'Not started', bg: '#F5F5F5', color: '#8A8A8A' },
  locked:      { label: 'Locked',      bg: '#F1EFEC', color: '#9A958F' },
}

const BEING_BUILT_BADGE: BadgeDef = { label: 'Being built', bg: '#EFF6FF', color: '#2563EB' }

/** Resolve the badge for a component, applying the "Being built" override
 *  (learning locked while the assessment is done) over the plain Locked pill.
 *  Used by BOTH the stepper status text and the card pill so they stay in sync. */
function resolveBadge(key: ComponentKey, states: Record<ComponentKey, ModuleState>): BadgeDef {
  const state = states[key]
  if (key === 'learning' && state === 'locked' && states['assessment'] === 'done') {
    return BEING_BUILT_BADGE
  }
  return BADGE[state] ?? BADGE.locked!
}

const ACTION_LABEL: Partial<Record<ModuleState, string | null>> = {
  done:        'Review',
  in_progress: 'Continue',
  available:   'Start',
  locked:      null,
}

/* ── Stepper node config ── */
type NodeState = 'done' | 'active' | 'upcoming'

const NODE_STATE: Partial<Record<ModuleState, NodeState>> = {
  done:        'done',
  in_progress: 'active',
  available:   'upcoming',
  locked:      'upcoming',
}

/* ── Progress % ── */
function calcProgress(states: Record<ComponentKey, ModuleState>): number {
  const vals: Partial<Record<ModuleState, number>> = { locked: 0, available: 0, in_progress: 0.5, done: 1 }
  const visible = MODULES.filter(m => states[m.key] !== 'hidden')
  if (!visible.length) return 0
  const total = visible.reduce((s, m) => s + (vals[states[m.key]] ?? 0), 0)
  return Math.round((total / visible.length) * 100)
}

/* ── Icons ── */
function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none"
      stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3.5 9.5l3.5 3.5 7.5-8" />
    </svg>
  )
}
function LockIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none"
      stroke="currentColor" strokeWidth="1.4">
      <rect x="3" y="7" width="10" height="7" rx="1.5" />
      <path d="M5 7V5a3 3 0 0 1 6 0v2" />
    </svg>
  )
}
// Small check for the "Completed" pill — inherits the badge's text color.
function BadgeCheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 18 18" fill="none"
      stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3.5 9.5l3.5 3.5 7.5-8" />
    </svg>
  )
}

/* ── Styles ── */
// The old file's s.nav…s.dropdownDivider block is dead code (the nav is AppNav)
// and is deliberately not ported (design-frontend.md §3, D2).
const s = {
  page: { minHeight: '100vh', background: '#fff', display: 'flex', flexDirection: 'column' },

  /* Main — header metrics match the learning path (the leading page) */
  main: { flex: 1, width: 'min(1080px, 100%)', margin: '0 auto', padding: '44px 40px 60px' },

  eyebrow: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase',
    color: '#EF463C', margin: '0 0 14px',
  },
  heading: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 44, lineHeight: 1.12, letterSpacing: '-0.015em',
    color: '#101820', margin: '0 0 12px',
  },
  subtitle: {
    fontSize: 17, lineHeight: 1.6, fontWeight: 300,
    color: '#8A8A8A', margin: '0 0 36px', maxWidth: '54ch',
  },

  /* Progress tracker */
  tracker: {
    border: '1px solid #E2E2E2', borderRadius: 12,
    padding: '22px 28px 26px', marginBottom: 36,
  },
  trackerHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    marginBottom: 24,
  },
  trackerLabel: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase',
    color: '#8A8A8A',
  },
  trackerPct: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 13, color: '#EF463C',
  },
  stepper: { display: 'flex', alignItems: 'flex-start' },
  stepItem: { display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 },
  stepConnector: { flex: 1, height: 4, marginTop: 22, background: '#EAEAEA', borderRadius: 999, transition: 'background 320ms ease' },
  stepConnectorDone: { background: '#EF463C' },
  stepLabel: { marginTop: 12, fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 13, color: '#101820', textAlign: 'center' },
  stepStatus: { marginTop: 3, fontSize: 12, fontWeight: 600, textAlign: 'center' },

  /* Cards */
  cards: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 },
  card: {
    border: '1px solid #E2E2E2', borderRadius: 12,
    padding: '24px 22px', display: 'flex', flexDirection: 'column',
    background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,.05)',
    transition: 'border-color 180ms, box-shadow 180ms, transform 180ms',
    cursor: 'default',
  },
  cardLocked: { background: '#FAFAF9', border: '1px solid #ECECEC' },
  cardTop: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 },
  iconWrap: {
    width: 52, height: 52, borderRadius: 10,
    background: '#FBF1F0', display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
  iconWrapLocked: { background: '#F1EFEC' },
  icon: { width: 32, height: 32, display: 'block' },
  iconLocked: { filter: 'grayscale(1)', opacity: 0.35 },
  badge: {
    display: 'inline-flex', alignItems: 'center',
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 11, letterSpacing: '0.04em',
    padding: '4px 10px', borderRadius: 999,
  },
  cardTitle: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 19, lineHeight: 1.2, color: '#101820', margin: '0 0 8px',
  },
  cardTitleLocked: { color: '#9A958F' },
  cardDesc: { fontSize: 14, lineHeight: 1.6, fontWeight: 300, color: '#8A8A8A', margin: '0 0 auto' },
  cardFoot: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    marginTop: 20, paddingTop: 16, borderTop: '1px solid #F0EFED',
  },
  cardMeta: { fontSize: 13, fontWeight: 300, color: '#B6B6B6' },
  cardAction: {
    display: 'inline-flex', alignItems: 'center', gap: 4,
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 14, color: '#EF463C', background: 'none',
    border: 'none', cursor: 'pointer', padding: 0,
    transition: 'color 180ms',
  },
} satisfies Record<string, CSSProperties>

function StepNode({ state }: { state: NodeState }) {
  const nodeBase: CSSProperties = {
    position: 'relative', width: 44, height: 44, borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, transition: 'all 180ms',
  }
  if (state === 'done') {
    return (
      <div style={{
        ...nodeBase,
        background: 'radial-gradient(circle at 32% 30%, #F2685F, #EF463C)',
        boxShadow: '0 4px 12px rgba(239,70,60,.28)',
      }}>
        <CheckIcon />
      </div>
    )
  }
  if (state === 'active') {
    return (
      <div style={{
        ...nodeBase, background: '#fff', border: '2.5px solid #EF463C',
        boxShadow: '0 2px 8px rgba(239,70,60,.18)',
      }}>
        {/* pulsing ring, same accent as the learning-path current node */}
        <span style={{
          position: 'absolute', inset: -5, borderRadius: '50%',
          border: '2.5px solid #EF463C', animation: 'jh-pulse 1.9s ease-out infinite',
          pointerEvents: 'none',
        }} />
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#EF463C' }} />
      </div>
    )
  }
  return (
    <div style={{ ...nodeBase, background: '#fff', border: '2px solid #E2E2E2' }}>
      <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#E2E2E2' }} />
    </div>
  )
}

interface ModuleCardProps {
  mod: ModuleDef
  state: ModuleState
  meta: string
  onAction: () => void
  badge: BadgeDef
}

function ModuleCard({ mod, state, meta, onAction, badge }: ModuleCardProps) {
  const actionLabel = ACTION_LABEL[state]
  const locked = state === 'locked'
  const showLock = badge.label === 'Locked' // not shown once "Being built" overrides it

  return (
    <div
      className={`module-card${locked ? ' is-locked' : ''}`}
      style={{ ...s.card, ...(locked ? s.cardLocked : {}), cursor: actionLabel ? 'pointer' : 'default' }}
      onClick={actionLabel ? onAction : undefined}
    >
      <div style={s.cardTop}>
        <div style={{ ...s.iconWrap, ...(locked ? s.iconWrapLocked : {}) }}>
          <img style={{ ...s.icon, ...(locked ? s.iconLocked : {}) }} src={mod.icon} alt="" />
        </div>
        <span style={{ ...s.badge, background: badge.bg, color: badge.color, gap: 5 }}>
          {state === 'done' && <BadgeCheckIcon />}
          {showLock && <LockIcon size={12} />}
          {badge.label}
        </span>
      </div>

      <p style={{ ...s.cardTitle, ...(locked ? s.cardTitleLocked : {}) }}>{mod.title}</p>
      <p style={s.cardDesc}>{mod.desc}</p>

      <div style={s.cardFoot}>
        <span style={s.cardMeta}>{meta}</span>
        {actionLabel && (
          <button
            type="button"
            className="module-card-action"
            style={{ ...s.cardAction, outline: 'none' }}
            onClick={onAction}
          >
            {actionLabel} ›
          </button>
        )}
      </div>
    </div>
  )
}

export default function JourneyHome() {
  const navigate = useNavigate()
  const { user } = useAuth()
  // Defaults are only ever visible on the fetch-failure fallback — first paint
  // shows a spinner until /api/me/journey resolves (loaded flag below).
  const [states, setStates] = useState<Record<ComponentKey, ModuleState>>({ assessment: 'available', learning: 'locked', interview: 'locked' })
  const [loaded, setLoaded] = useState(false)
  const progress = calcProgress(states)

  const userId = user?.id

  useEffect(() => {
    if (!userId) return
    let cancelled = false
    async function load() {
      // One aggregate call replaces the old project_component_settings +
      // survey_responses pair. Contract deviation from design-frontend §3:
      // survey_status is 'not_started' | 'in_progress' | 'complete' (not 'none').
      const { data } = await client.GET('/api/me/journey')
      if (cancelled) return
      if (!data) { setLoaded(true); return } // fall back to the default render

      const resolved = {} as Record<ComponentKey, ModuleState>
      for (const mod of MODULES) {
        // The server already applies the DEFAULT_HIDDEN/LOCKED fallback; keep a
        // defensive client-side fallback for a missing component key.
        const row = data.components[mod.key]
        const hidden = row ? row.hidden : DEFAULT_HIDDEN[mod.key]
        const locked = row ? row.locked : DEFAULT_LOCKED[mod.key]

        if (hidden) {
          resolved[mod.key] = 'hidden'
        } else if (mod.key === 'assessment') {
          if (data.survey_status === 'complete') resolved[mod.key] = 'done'
          else if (data.survey_status === 'in_progress') resolved[mod.key] = 'in_progress'
          else resolved[mod.key] = locked ? 'locked' : 'available'
        } else if (mod.key === 'learning') {
          // Locked/being-built takes precedence (the card is inert); otherwise
          // reflect real lesson progress so the pill moves to In progress once a
          // lesson is completed, and Completed once every assigned lesson is done.
          if (locked) resolved[mod.key] = 'locked'
          else if (data.learning_status === 'complete') resolved[mod.key] = 'done'
          else if (data.learning_status === 'in_progress') resolved[mod.key] = 'in_progress'
          else resolved[mod.key] = 'available'
        } else {
          resolved[mod.key] = locked ? 'locked' : 'available'
        }
      }
      setStates(resolved)
      setLoaded(true)
    }
    load()
    return () => { cancelled = true }
  }, [userId])

  const firstName = user?.first_name ?? ''

  return (
    <div style={s.page}>
      <style>{`@keyframes jh-pulse { 0% { transform: scale(1); opacity: .5; } 70%, 100% { transform: scale(1.55); opacity: 0; } }`}</style>
      <AppNav title="AI enablement hub" />

      {/* Main */}
      <main style={s.main}>
        <p style={s.eyebrow}>your enablement journey</p>
        <h1 style={s.heading}>Welcome{firstName ? `, ${firstName}.` : '.'}</h1>
        <p style={s.subtitle}>
          Here is where you are today, and what comes next on your path to working
          confidently with AI. Pick up wherever you left off.
        </p>

        {!loaded ? (
          // minHeight ≈ tracker + cards so the decorative bottom strip doesn't jump
          <div style={{ minHeight: 480, display: 'flex' }}>
            <Spinner />
          </div>
        ) : (
          <>
        {/* Progress tracker */}
        <div style={s.tracker}>
          <div style={s.trackerHeader}>
            <span style={s.trackerLabel}>your progress</span>
            <span style={s.trackerPct}>{progress}% complete</span>
          </div>
          <div style={s.stepper}>
            {MODULES.filter(mod => states[mod.key] !== 'hidden').map((mod, i, visible) => {
              const nodeState = NODE_STATE[states[mod.key]] ?? 'upcoming'
              const prevDone = i > 0 && states[visible[i - 1].key] === 'done'
              // Same resolved badge as the card pill, so the two never disagree.
              const stepBadge = resolveBadge(mod.key, states)
              const statusText = stepBadge.label
              const statusColor = stepBadge.color
              return (
                <React.Fragment key={mod.key}>
                  {i > 0 && (
                    <div style={{ ...s.stepConnector, ...(prevDone ? s.stepConnectorDone : {}) }} />
                  )}
                  <div style={s.stepItem}>
                    <StepNode state={nodeState} />
                    <span style={s.stepLabel}>{mod.title}</span>
                    <span style={{ ...s.stepStatus, color: statusColor }}>{statusText}</span>
                  </div>
                </React.Fragment>
              )
            })}
          </div>
        </div>

        {/* Component cards */}
        <div style={s.cards}>
          {MODULES.filter(mod => states[mod.key] !== 'hidden').map(mod => (
            <ModuleCard
              key={mod.key}
              mod={mod}
              state={states[mod.key]}
              meta={MODULE_META[mod.key]}
              onAction={() => navigate(mod.route)}
              badge={resolveBadge(mod.key, states)}
            />
          ))}
        </div>
          </>
        )}
      </main>

      {/* Bottom decorative strip */}
      <div style={{
        width: '100%',
        height: 102,
        backgroundImage: 'url(/visual.png)',
        backgroundRepeat: 'repeat-x',
        backgroundSize: 'auto 100%',
        backgroundPosition: 'left bottom',
        flexShrink: 0,
      }} />
    </div>
  )
}
