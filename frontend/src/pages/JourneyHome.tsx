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
  locked:      { label: 'Not started', bg: '#F5F5F5', color: '#8A8A8A' },
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
  stepConnector: { flex: 1, height: 2, marginTop: 19, background: '#E2E2E2', alignSelf: 'auto' },
  stepConnectorDone: { background: '#EF463C' },
  stepLabel: { marginTop: 10, fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, color: '#3C3C3C', textAlign: 'center' },
  stepStatus: { marginTop: 3, fontSize: 12, fontWeight: 300, textAlign: 'center' },

  /* Cards */
  cards: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 },
  card: {
    border: '1px solid #E2E2E2', borderRadius: 12,
    padding: '24px 22px', display: 'flex', flexDirection: 'column',
    background: '#fff', boxShadow: 'none',
    transition: 'border-color 180ms, box-shadow 180ms',
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
  cardLockNote: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    fontSize: 12, fontWeight: 400, color: '#B6B6B6',
  },
} satisfies Record<string, CSSProperties>

function StepNode({ state }: { state: NodeState }) {
  const nodeBase: CSSProperties = {
    width: 40, height: 40, borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, transition: 'all 180ms',
  }
  if (state === 'done') {
    return <div style={{ ...nodeBase, background: '#EF463C', border: '2px solid #EF463C' }}><CheckIcon /></div>
  }
  if (state === 'active') {
    return (
      <div style={{ ...nodeBase, background: '#fff', border: '2px solid #EF463C' }}>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#EF463C' }} />
      </div>
    )
  }
  return <div style={{ ...nodeBase, background: '#fff', border: '2px solid #E2E2E2' }}>
    <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#E2E2E2' }} />
  </div>
}

interface ModuleCardProps {
  mod: ModuleDef
  state: ModuleState
  meta: string
  onAction: () => void
  badgeOverride?: BadgeDef
}

function ModuleCard({ mod, state, meta, onAction, badgeOverride }: ModuleCardProps) {
  const badge = badgeOverride ?? BADGE[state] ?? BADGE.locked!
  const actionLabel = ACTION_LABEL[state]

  return (
    <div className="module-card" style={{ ...s.card, cursor: actionLabel ? 'pointer' : 'default' }} onClick={actionLabel ? onAction : undefined}>
      <div style={s.cardTop}>
        <div style={s.iconWrap}>
          <img style={s.icon} src={mod.icon} alt="" />
        </div>
        <span style={{ ...s.badge, background: badge.bg, color: badge.color }}>
          {badge.label}
        </span>
      </div>

      <p style={s.cardTitle}>{mod.title}</p>
      <p style={s.cardDesc}>{mod.desc}</p>

      <div style={s.cardFoot}>
        <span style={s.cardMeta}>{meta}</span>
        {actionLabel ? (
          <button
            type="button"
            className="module-card-action"
            style={{ ...s.cardAction, outline: 'none' }}
            onClick={onAction}
          >
            {actionLabel} ›
          </button>
        ) : (
          <span style={s.cardLockNote}><LockIcon /> locked</span>
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
              const statusText = BADGE[states[mod.key]]?.label ?? ''
              const statusColor = BADGE[states[mod.key]]?.color ?? '#8A8A8A'
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
          {MODULES.filter(mod => states[mod.key] !== 'hidden').map(mod => {
            const beingBuilt =
              mod.key === 'learning' &&
              states['learning'] === 'locked' &&
              states['assessment'] === 'done'
            return (
              <ModuleCard
                key={mod.key}
                mod={mod}
                state={states[mod.key]}
                meta={MODULE_META[mod.key]}
                onAction={() => navigate(mod.route)}
                badgeOverride={beingBuilt ? { label: 'Being built', bg: '#EFF6FF', color: '#2563EB' } : undefined}
              />
            )
          })}
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
