import { useEffect, useState, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { client, errorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import { LEVELS, LEVEL_GRADIENT } from '../lib/levels'
import {
  C1_OPTIONS, C2_OPTIONS, C3_OPTIONS, C4_OPTIONS, C5_OPTIONS, C6_OPTIONS,
  FREQ_OPTIONS, BREADTH_OPTIONS, TOOLS_OPTIONS, ATTITUDE_OPTIONS,
  READINESS_OPTIONS, BARRIERS_OPTIONS, SETUP_OPTIONS,
  type C1Code, type C2Code, type C3Code, type C4Code, type C5Code, type C6Code,
  type FreqCode, type BreadthCode, type ToolsCode, type AttitudeCode,
  type ReadinessCode, type BarriersCode, type SetupCode,
} from '../lib/surveyOptions'

// ── Answer state (typed via the derived surveyOptions unions) ─────────────────

interface SurveyAnswers {
  job_title: string
  department: string
  consent: boolean
  c1_code: C1Code | null
  c2_code: C2Code | null
  c3_code: C3Code | null
  c4_code: C4Code | null
  c5_codes: C5Code[]
  c6_code: C6Code | null
  b_setup: SetupCode[]
  b_freq: FreqCode | null
  b_breadth: BreadthCode | null
  b_tools: ToolsCode[]
  b_attitude: AttitudeCode | null
  b_readiness: ReadinessCode | null
  b_barriers: BarriersCode[]
  q_excitement: string
  q_timesink: string
}

type SingleField = 'c1_code' | 'c2_code' | 'c3_code' | 'c4_code' | 'c6_code'
type MultiField = 'c5_codes' | 'b_setup' | 'b_tools' | 'b_barriers'
type ScaleField = 'b_attitude' | 'b_readiness'
type TextField = 'q_excitement' | 'q_timesink'

// ── Step definitions ──────────────────────────────────────────────────────────

interface ChoiceOption { code: string; label: string }
interface ScaleOption { code: AttitudeCode | ReadinessCode; label: string; sub: string }

interface PlainStep { id: 'intro' | 'identity' | 'usage' | 'consent' | 'complete' }
interface SingleStep {
  id: string; field: SingleField; type: 'single'
  options: readonly ChoiceOption[]; eyebrow: string; question: string; hint?: string
}
interface MultiStep {
  id: string; field: MultiField; type: 'multi'
  options: readonly ChoiceOption[]; eyebrow: string; question: string; hint?: string
}
interface ScaleStep {
  id: string; field: ScaleField; type: 'scale'
  options: readonly ScaleOption[]; eyebrow: string; question: string
}
interface TextStep {
  id: string; field: TextField; type: 'text'; optional: true
  eyebrow: string; question: string
}
type StepDef = PlainStep | SingleStep | MultiStep | ScaleStep | TextStep

const STEPS: readonly StepDef[] = [
  { id: 'intro' },
  { id: 'identity' },
  { id: 'c1', field: 'c1_code',  type: 'single', options: C1_OPTIONS,
    eyebrow: 'Competency 1 of 6: Understanding',
    question: "When a tool like ChatGPT gives you an answer, which is closest to how you'd describe what it's actually doing?" },
  { id: 'c2', field: 'c2_code',  type: 'single', options: C2_OPTIONS,
    eyebrow: 'Competency 2 of 6: Use case spotting',
    question: 'Thinking about your everyday work, how far have you got with AI?' },
  { id: 'c3', field: 'c3_code',  type: 'single', options: C3_OPTIONS,
    eyebrow: 'Competency 3 of 6: Prompting',
    question: 'When an AI tool gives you a poor or unhelpful answer, what do you usually do?' },
  { id: 'c4', field: 'c4_code',  type: 'single', options: C4_OPTIONS,
    eyebrow: 'Competency 4 of 6: Critical evaluation',
    question: "You ask an AI tool to draft a market summary for a client. It comes back confident, polished, with specific figures and a competitor comparison. Which is closest to what you'd actually do with it?" },
  { id: 'c5', field: 'c5_codes', type: 'multi',  options: C5_OPTIONS,
    eyebrow: 'Competency 5 of 6: Responsible use',
    question: 'In the past month or so, which of these have you done with an AI tool?',
    hint: 'Select all that apply. No wrong answers, it just helps us pitch the training.' },
  { id: 'c6', field: 'c6_code',  type: 'single', options: C6_OPTIONS,
    eyebrow: 'Competency 6 of 6: Trust calibration',
    question: 'Thinking about how AI assistants actually work, which is closest to your view?' },
  { id: 'b_setup', field: 'b_setup', type: 'multi', options: SETUP_OPTIONS,
    eyebrow: 'Context',
    question: 'Have you set up any of these and keep reusing them?',
    hint: 'Select all that apply.' },
  { id: 'usage' },
  { id: 'tools',    field: 'b_tools',    type: 'multi',  options: TOOLS_OPTIONS,
    eyebrow: 'Context',
    question: 'Which AI tools have you used?',
    hint: 'Select all that apply.' },
  { id: 'attitude', field: 'b_attitude', type: 'scale',  options: ATTITUDE_OPTIONS,
    eyebrow: 'Context',
    question: 'Which of these best describes how you feel about using AI more in your work?' },
  { id: 'readiness',field: 'b_readiness',type: 'scale',  options: READINESS_OPTIONS,
    eyebrow: 'Context',
    question: 'How willing are you to change the way you work to make more use of AI?' },
  { id: 'barriers', field: 'b_barriers', type: 'multi',  options: BARRIERS_OPTIONS,
    eyebrow: 'Context',
    question: 'What gets in the way of using AI more in your work?',
    hint: 'Select all that apply.' },
  { id: 'q_excitement', field: 'q_excitement', type: 'text', optional: true,
    eyebrow: 'Optional',
    question: 'When it comes to AI and your work, what excites you and what worries you?' },
  { id: 'q_timesink',   field: 'q_timesink',   type: 'text', optional: true,
    eyebrow: 'Optional',
    question: "What's one task or part of your work that eats up time you'd love to get back?" },
  { id: 'consent' },
  { id: 'complete' },
]

const LAST_CONTENT_IDX = STEPS.findIndex(s => s.id === 'consent')

const EMPTY_ANSWERS: SurveyAnswers = {
  job_title: '', department: '', consent: false,
  c1_code: null, c2_code: null, c3_code: null, c4_code: null,
  c5_codes: [], c6_code: null,
  b_setup: [],
  b_freq: null, b_breadth: null, b_tools: [], b_attitude: null,
  b_readiness: null, b_barriers: [], q_excitement: '', q_timesink: '',
}

// ── Styles ────────────────────────────────────────────────────────────────────
// The old file's s.nav…s.dropdownDivider block was dead code (the nav is AppNav)
// and is deliberately not ported — same D2 class as JourneyHome's dead styles.

const s = {
  page: { minHeight: '100vh', background: '#fff', display: 'flex', flexDirection: 'column' },

  // Progress bar (two-part)
  progressBar: {
    display: 'flex', gap: 12, padding: '10px 40px 8px',
    background: '#fff', borderBottom: '1px solid #F0EFED',
  },
  progressPart: { flex: 1, display: 'flex', flexDirection: 'column', gap: 5 },
  progressLabel: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 11,
    color: '#ADADAD', letterSpacing: '0.06em', textTransform: 'uppercase',
  },
  progressSegWrap: { height: 4, background: '#F0EFED', borderRadius: 2, overflow: 'hidden' },
  progressSegFill: { height: '100%', background: '#EF463C', borderRadius: 2, transition: 'width 280ms ease' },

  // Read-only banner
  readonlyBanner: {
    background: '#FAFAF9', borderBottom: '1px solid #F0EFED',
    padding: '10px 40px', textAlign: 'center',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A',
  },

  // Main — survey steps read best in a narrow column; the intro screen widens to
  // 1080 so its header + level framework line up with the learning path (leading).
  main:      { flex: 1, width: 'min(680px, 100%)',  margin: '0 auto', padding: '44px 40px 80px' },
  mainWide:  { width: 'min(1080px, 100%)' },

  // Typography
  eyebrow: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase',
    color: '#EF463C', margin: '0 0 14px',
  },
  question: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 26, lineHeight: 1.3, letterSpacing: '-0.01em',
    color: '#101820', margin: '0 0 10px',
  },
  hint: { fontSize: 14, fontWeight: 300, color: '#8A8A8A', margin: '0 0 28px' },

  // Option cards
  options: { display: 'flex', flexDirection: 'column', gap: 10, marginTop: 28 },
  optionCard: {
    border: '1.5px solid #E2E2E2', borderRadius: 10,
    padding: '15px 18px', cursor: 'pointer',
    display: 'flex', alignItems: 'flex-start', gap: 14,
    background: '#fff', transition: 'border-color 140ms, background 140ms',
    userSelect: 'none',
  },
  optionCardSelected:  { border: '1.5px solid #EF463C', background: '#FEF6F5' },
  optionCardDisabled:  { cursor: 'default' },
  optionRadio: {
    width: 18, height: 18, borderRadius: '50%',
    borderWidth: 2, borderStyle: 'solid', borderColor: '#E2E2E2',
    flexShrink: 0, marginTop: 2,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'border-color 140ms',
  },
  optionRadioSelected: { borderColor: '#EF463C' },
  optionDot:           { width: 8, height: 8, borderRadius: '50%', background: '#EF463C' },
  optionCheckbox: {
    width: 18, height: 18, borderRadius: 4,
    borderWidth: 2, borderStyle: 'solid', borderColor: '#E2E2E2',
    flexShrink: 0, marginTop: 2,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'border-color 140ms, background 140ms',
  },
  optionCheckboxSelected: { borderColor: '#EF463C', background: '#EF463C' },
  optionLabel: { fontSize: 15, fontWeight: 300, lineHeight: 1.55, color: '#3C3C3C' },

  // Scale
  scaleRow:  { display: 'flex', gap: 10, marginTop: 28 },
  scaleCard: {
    flex: 1, border: '1.5px solid #E2E2E2', borderRadius: 10,
    padding: '16px 10px', cursor: 'pointer', textAlign: 'center',
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5,
    background: '#fff', transition: 'border-color 140ms, background 140ms',
    userSelect: 'none',
  },
  scaleCardSelected: { border: '1.5px solid #EF463C', background: '#FEF6F5' },
  scaleNum:          { fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 22, color: '#101820' },
  scaleNumSelected:  { color: '#EF463C' },
  scaleLabel:        { fontSize: 13, fontWeight: 600, color: '#3C3C3C' },
  scaleSub:          { fontSize: 11, fontWeight: 300, color: '#8A8A8A', lineHeight: 1.4 },

  // Text area
  textarea: {
    width: '100%', minHeight: 140, padding: '14px 16px', marginTop: 28,
    border: '1.5px solid #E2E2E2', borderRadius: 10,
    fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 15, lineHeight: 1.6,
    color: '#3C3C3C', resize: 'vertical', outline: 'none',
    transition: 'border-color 140ms', boxSizing: 'border-box',
  },

  // Identity inputs
  fieldGroup:  { marginBottom: 22 },
  fieldLabel:  { display: 'block', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: '#3C3C3C', marginBottom: 8 },
  input: {
    width: '100%', padding: '12px 16px',
    border: '1.5px solid #E2E2E2', borderRadius: 10,
    fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 15,
    color: '#3C3C3C', outline: 'none',
    transition: 'border-color 140ms', boxSizing: 'border-box',
  },

  // Consent
  consentBox: {
    border: '1.5px solid #E2E2E2', borderRadius: 10, padding: '18px 20px',
    display: 'flex', alignItems: 'flex-start', gap: 14, cursor: 'pointer',
    transition: 'border-color 140ms, background 140ms', marginTop: 28,
    userSelect: 'none',
  },
  consentBoxChecked: { borderColor: '#EF463C', background: '#FEF6F5' },
  consentCheck: {
    width: 20, height: 20, borderRadius: 5, border: '2px solid #E2E2E2',
    flexShrink: 0, marginTop: 1,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'border-color 140ms, background 140ms',
  },
  consentCheckChecked: { borderColor: '#EF463C', background: '#EF463C' },
  consentText: { fontSize: 15, fontWeight: 300, lineHeight: 1.6, color: '#3C3C3C' },

  // Navigation buttons
  navBtns: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    marginTop: 40, paddingTop: 24, borderTop: '1px solid #F0EFED',
  },
  btnBack: {
    background: 'none', border: '1px solid #E2E2E2', borderRadius: 999,
    padding: '10px 22px', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: '#8A8A8A',
    transition: 'border-color 140ms, color 140ms',
  },
  btnPrimary: {
    background: '#EF463C', border: 'none', borderRadius: 999,
    padding: '11px 28px', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 15, color: '#fff',
    transition: 'background 140ms',
  },
  btnPrimaryDisabled: { background: '#E2E2E2', cursor: 'not-allowed' },

  // Intro / complete screens
  bigHeading: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 44, lineHeight: 1.12, letterSpacing: '-0.015em',
    color: '#101820', margin: '0 0 18px',
  },
  bigBody: { fontSize: 17, fontWeight: 300, color: '#8A8A8A', lineHeight: 1.65, margin: '0 0 32px', maxWidth: '50ch' },
  bullets: { listStyle: 'none', padding: 0, margin: '0 0 40px', display: 'flex', flexDirection: 'column', gap: 10 },
  bullet:  { display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 15, fontWeight: 300, color: '#3C3C3C' },
  bulletDot: { width: 6, height: 6, borderRadius: '50%', background: '#EF463C', flexShrink: 0, marginTop: 7 },

  // Level-framework panel (intro) — styled to match the learning path progress panel
  fwPanel: {
    border: '1px solid #E2E2E2', borderRadius: 12,
    padding: '24px 30px 26px', marginBottom: 24,
  },
  fwLabel: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.14em', textTransform: 'uppercase',
    color: '#8A8A8A', margin: '0 0 26px',
  },
  fwTrack: {
    position: 'relative', height: 6, borderRadius: 999,
    background: '#F5F5F5', border: '1px solid #ECECEC',
    margin: '4px 0 30px',
  },
  fwFill: {
    position: 'absolute', inset: 0, borderRadius: 999,
    background: LEVEL_GRADIENT,
  },
  fwCheckpoint: {
    position: 'absolute', top: '50%', width: 42, height: 42, marginLeft: -21,
    transform: 'translateY(-50%)', borderRadius: '50%', border: '3px solid #fff',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,.14)', boxSizing: 'border-box',
  },
  fwCheckpointNum: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 16, color: '#fff',
  },
  fwGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 },
  fwCard: { textAlign: 'center', padding: '0 6px' },
  fwName: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 15, margin: '0 0 3px',
  },
  fwTagline: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 12,
    color: '#101820', margin: '0 0 3px',
  },
  fwSub: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 11,
    color: '#8A8A8A', lineHeight: 1.4, margin: 0,
  },

  // Usage step sub-labels
  subLabel: { fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 16, color: '#101820', margin: '0 0 14px' },
  usageSection: { marginBottom: 36 },
  usageOptions: { display: 'flex', flexDirection: 'column', gap: 8 },

  // Error
  errorMsg: { fontSize: 14, color: '#C42828', marginTop: 12, fontWeight: 300 },
} satisfies Record<string, CSSProperties>

// ── Small helpers ─────────────────────────────────────────────────────────────

function CheckSvg() {
  return (
    <svg width="11" height="9" viewBox="0 0 11 9" fill="none">
      <path d="M1 4.5l3 3L10 1" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

interface OptionCardProps {
  option: ChoiceOption
  selected: boolean
  onClick: () => void
  disabled: boolean
}

function OptionCard({ option, selected, onClick, disabled }: OptionCardProps) {
  return (
    <div
      role="button" tabIndex={disabled ? -1 : 0}
      className={`option-card${selected ? ' option-selected' : ''}`}
      onClick={disabled ? undefined : onClick}
      onKeyDown={disabled ? undefined : e => e.key === 'Enter' && onClick()}
      style={{
        ...s.optionCard,
        ...(selected ? s.optionCardSelected : {}),
        ...(disabled ? s.optionCardDisabled : {}),
      }}
    >
      <div style={{ ...s.optionRadio, ...(selected ? s.optionRadioSelected : {}) }}>
        {selected && <div style={s.optionDot} />}
      </div>
      <span style={s.optionLabel}>{option.label}</span>
    </div>
  )
}

interface MultiCardProps {
  option: ChoiceOption
  checked: boolean
  onChange: () => void
  disabled: boolean
}

function MultiCard({ option, checked, onChange, disabled }: MultiCardProps) {
  return (
    <div
      role="checkbox" aria-checked={checked} tabIndex={disabled ? -1 : 0}
      className={`option-card${checked ? ' option-selected' : ''}`}
      onClick={disabled ? undefined : onChange}
      onKeyDown={disabled ? undefined : e => e.key === ' ' && onChange()}
      style={{
        ...s.optionCard,
        ...(checked ? s.optionCardSelected : {}),
        ...(disabled ? s.optionCardDisabled : {}),
      }}
    >
      <div style={{ ...s.optionCheckbox, ...(checked ? s.optionCheckboxSelected : {}) }}>
        {checked && <CheckSvg />}
      </div>
      <span style={s.optionLabel}>{option.label}</span>
    </div>
  )
}

interface ScaleCardProps {
  option: ScaleOption
  selected: boolean
  onClick: () => void
  disabled: boolean
}

function ScaleCard({ option, selected, onClick, disabled }: ScaleCardProps) {
  return (
    <div
      role="button" tabIndex={disabled ? -1 : 0}
      className={`option-card${selected ? ' option-selected' : ''}`}
      onClick={disabled ? undefined : onClick}
      onKeyDown={disabled ? undefined : e => e.key === 'Enter' && onClick()}
      style={{
        ...s.scaleCard,
        ...(selected ? s.scaleCardSelected : {}),
        ...(disabled ? s.optionCardDisabled : {}),
      }}
    >
      <span style={{ ...s.scaleNum, ...(selected ? s.scaleNumSelected : {}) }}>{option.code}</span>
      <span style={s.scaleLabel}>{option.label}</span>
      <span style={s.scaleSub}>{option.sub}</span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Assessment() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [step, setStep]               = useState(0)
  const [answers, setAnswers]         = useState<SurveyAnswers>(EMPTY_ANSWERS)
  const [status, setStatus]           = useState<'in_progress' | 'complete'>('in_progress')
  const [justCompleted, setJustCompleted] = useState(false)
  const [saving, setSaving]           = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const [focusedField, setFocusedField] = useState<string | null>(null)

  useEffect(() => { window.scrollTo(0, 0) }, [step])

  const userId = user?.id

  // Load existing survey response on mount
  useEffect(() => {
    if (!userId) return
    let cancelled = false
    async function load() {
      const { data: resp, error: surveyErr } = await client.GET('/api/survey/me')
      if (cancelled) return
      if (surveyErr) { setError('Failed to load your assessment progress. Please refresh.'); return }

      if (resp) {
        setStatus(resp.status === 'complete' ? 'complete' : 'in_progress')
        // The generated schema types answer codes as plain string|null; the
        // values come from the surveyOptions arrays, so narrowing to the
        // derived unions at this boundary is sound.
        setAnswers({
          job_title:    resp.job_title    ?? '',
          department:   resp.department   ?? '',
          consent:      resp.consent      ?? false,
          c1_code:      (resp.c1_code as C1Code | null) ?? null,
          c2_code:      (resp.c2_code as C2Code | null) ?? null,
          c3_code:      (resp.c3_code as C3Code | null) ?? null,
          c4_code:      (resp.c4_code as C4Code | null) ?? null,
          c5_codes:     (resp.c5_codes as C5Code[] | null) ?? [],
          c6_code:      (resp.c6_code as C6Code | null) ?? null,
          b_setup:      (resp.b_setup as SetupCode[] | null) ?? [],
          b_freq:       (resp.b_freq as FreqCode | null) ?? null,
          b_breadth:    (resp.b_breadth as BreadthCode | null) ?? null,
          b_tools:      (resp.b_tools as ToolsCode[] | null) ?? [],
          b_attitude:   (resp.b_attitude as AttitudeCode | null) ?? null,
          b_readiness:  (resp.b_readiness as ReadinessCode | null) ?? null,
          b_barriers:   (resp.b_barriers as BarriersCode[] | null) ?? [],
          q_excitement: resp.q_excitement ?? '',
          q_timesink:   resp.q_timesink   ?? '',
        })
        // Resume in-progress from saved step; read-only starts at intro (step 0).
        // Cap at LAST_CONTENT_IDX so the terminal complete screen is never loaded
        // from DB — it only appears after a fresh in-session submission.
        const savedStep = resp.status === 'complete'
          ? 0
          : Math.min(resp.current_step ?? 0, LAST_CONTENT_IDX)
        setStep(savedStep)
      }
    }
    load()
    return () => { cancelled = true }
  }, [userId])

  const isReadOnly = status === 'complete'

  // Two-part progress: Part 1 = competencies (steps 2–7), Part 2 = context (steps 8–15)
  const PART1_START = 2, PART1_END = 7
  const PART2_START = 8, PART2_END = 15
  const part1Pct = step < PART1_START ? 0
    : step > PART1_END ? 100
    : Math.round(((step - PART1_START + 1) / (PART1_END - PART1_START + 1)) * 100)
  const part2Pct = step < PART2_START ? 0
    : step > PART2_END ? 100
    : Math.round(((step - PART2_START + 1) / (PART2_END - PART2_START + 1)) * 100)

  function canProceed(): boolean {
    if (isReadOnly) return true
    switch (STEPS[step].id) {
      case 'intro':        return true
      case 'identity':     return (answers.job_title || '').trim().length > 0 && (answers.department || '').trim().length > 0
      case 'c1':           return !!answers.c1_code
      case 'c2':           return !!answers.c2_code
      case 'c3':           return !!answers.c3_code
      case 'c4':           return !!answers.c4_code
      case 'c5':           return (answers.c5_codes || []).length > 0
      case 'c6':           return !!answers.c6_code
      case 'b_setup':      return (answers.b_setup || []).length > 0
      case 'usage':        return !!answers.b_freq && !!answers.b_breadth
      case 'tools':        return (answers.b_tools || []).length > 0
      case 'attitude':     return answers.b_attitude != null
      case 'readiness':    return answers.b_readiness != null
      case 'barriers':     return (answers.b_barriers || []).length > 0
      case 'q_excitement': return true
      case 'q_timesink':   return true
      case 'consent':      return answers.consent === true
      case 'complete':     return true
      default:             return true
    }
  }

  async function saveProgress(nextStep: number) {
    // Backend upserts on the token's user id; empty answers are sent as null
    // to mirror the old upsert payload exactly.
    const { error: saveErr } = await client.PUT('/api/survey/me', {
      body: {
        current_step: nextStep,
        job_title:    answers.job_title   || null,
        department:   answers.department  || null,
        consent:      answers.consent     || null,
        c1_code:      answers.c1_code,
        c2_code:      answers.c2_code,
        c3_code:      answers.c3_code,
        c4_code:      answers.c4_code,
        c5_codes:     answers.c5_codes.length  ? answers.c5_codes  : null,
        c6_code:      answers.c6_code,
        b_setup:      answers.b_setup.length   ? answers.b_setup   : null,
        b_freq:       answers.b_freq,
        b_breadth:    answers.b_breadth,
        b_tools:      answers.b_tools.length   ? answers.b_tools   : null,
        b_attitude:   answers.b_attitude,
        b_readiness:  answers.b_readiness,
        b_barriers:   answers.b_barriers.length ? answers.b_barriers : null,
        q_excitement: answers.q_excitement || null,
        q_timesink:   answers.q_timesink   || null,
      },
    })
    if (saveErr) throw new Error(errorMessage(saveErr, 'Failed to save your progress. Please try again.'))
  }

  async function handleNext() {
    if (!canProceed()) return
    if (isReadOnly) { setStep(s => Math.min(s + 1, STEPS.length - 1)); return }

    const isSubmit = step === LAST_CONTENT_IDX
    setSaving(true)
    setError(null)
    try {
      await saveProgress(step + 1)
      if (isSubmit) {
        const { error: completeErr } = await client.POST('/api/survey/complete')
        if (completeErr) {
          throw new Error(errorMessage(completeErr, 'Failed to complete assessment.'))
        }

        setJustCompleted(true)
        setStatus('complete')
        setStep(STEPS.length - 1)
      } else {
        setStep(s => s + 1)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save your progress. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  function handleBack() {
    if (step <= 0) return
    setStep(s => s - 1)
  }

  // The generic step renderers below iterate heterogeneous option arrays, so the
  // per-step field↔code correlation can't be expressed to TS — the runtime values
  // are correct by construction (each step's options ARE the source of its union).
  function setAnswer(field: keyof SurveyAnswers, value: SurveyAnswers[keyof SurveyAnswers]) {
    setAnswers(prev => ({ ...prev, [field]: value } as SurveyAnswers))
  }

  function toggleMulti(field: MultiField, code: string) {
    setAnswers(prev => {
      const cur: readonly string[] = prev[field]
      const next = cur.includes(code) ? cur.filter(c => c !== code) : [...cur, code]
      return { ...prev, [field]: next } as SurveyAnswers
    })
  }

  // ── Step renderers ──────────────────────────────────────────────────────────

  function renderIntro() {
    // Events sit at the circle centres: 1/8, 3/8, 5/8, 7/8 of full width
    const EVENTS = [
      { label: 'Maturity assessment', pct: 12.5, color: '#EF463C' },
      { label: 'Learning path',       pct: 37.5, color: '#D0607A' },
      { label: 'Inspiration session', pct: 62.5, color: '#AB9BCB' },
      { label: '1-to-1 session',      pct: 87.5, color: '#72C4BF' },
    ]

    const sectionLabel: CSSProperties = {
      fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
      letterSpacing: '0.14em', textTransform: 'uppercase',
      color: '#8A8A8A', margin: '0 0 14px',
    }

    return (
      <div>
        <p style={s.eyebrow}>Maturity assessment</p>
        <h1 style={s.bigHeading}>Let's map where you stand with AI.</h1>
        <p style={s.bigBody}>
          This assessment is the starting point of your AI journey. It establishes where you are today so your learning path can be tailored to get you where you need to be.
        </p>

        {/* ── Level framework — bordered panel + gradient checkpoint bar, the same
            visual language as the learning path's "current level" box ── */}
        <div style={s.fwPanel}>
          <p style={s.fwLabel}>Level framework</p>

          {/* Gradient track with a numbered checkpoint per level */}
          <div style={s.fwTrack}>
            <div style={s.fwFill} />
            {LEVELS.map((level, i) => (
              <div key={level.code} style={{
                ...s.fwCheckpoint,
                left: `${(i + 0.5) * 25}%`,
                background: level.color,
              }}>
                <span style={s.fwCheckpointNum}>{i + 1}</span>
              </div>
            ))}
          </div>

          {/* Level detail, one column under each checkpoint */}
          <div style={s.fwGrid}>
            {LEVELS.map(level => (
              <div key={level.code} style={s.fwCard}>
                <p style={{ ...s.fwName, color: level.color }}>{level.name}</p>
                <p style={s.fwTagline}>{level.tagline}</p>
                <p style={s.fwSub}>{level.sub}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── Learning journey ── */}
        <div style={{ marginBottom: 28 }}>
          <p style={sectionLabel}>Learning journey</p>

          {/* Arrow + event markers */}
          <div style={{ position: 'relative', height: 54 }}>
            {/* Gradient line */}
            <div style={{
              position: 'absolute', top: 6, left: 0, right: 10, height: 3,
              background: 'linear-gradient(to right, #EF463C 30%, #AB9BCB 70%, #72C4BF)',
              borderRadius: 2,
            }} />
            {/* Arrowhead */}
            <div style={{
              position: 'absolute', top: 0, right: 0,
              width: 0, height: 0,
              borderTop: '7px solid transparent',
              borderBottom: '7px solid transparent',
              borderLeft: '12px solid #72C4BF',
            }} />

            {/* Event dots + labels */}
            {EVENTS.map(ev => (
              <div key={ev.label} style={{
                position: 'absolute', left: `${ev.pct}%`,
                top: 0, transform: 'translateX(-50%)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
              }}>
                <div style={{
                  width: 14, height: 14, borderRadius: '50%',
                  background: ev.color, border: '2px solid #fff',
                  flexShrink: 0,
                }} />
                <p style={{
                  fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 10,
                  color: ev.color, margin: 0, textAlign: 'center',
                  whiteSpace: 'nowrap',
                }}>{ev.label}</p>
              </div>
            ))}
          </div>
        </div>

        <p style={{ fontSize: 14, fontWeight: 300, color: '#8A8A8A', lineHeight: 1.65, margin: '0 0 32px' }}>
          Everyone on this project starts from a different place and that is completely fine. By the end, <strong style={{ fontWeight: 600, color: '#101820' }}>Practitioner is the new baseline</strong> for the whole team. However, throughout the project <strong style={{ fontWeight: 600, color: '#101820' }}>everyone will be upskilled.</strong> Your learning path is built around where you are today, giving more advanced people more advanced modules.
        </p>

        <ul style={s.bullets}>
          {[
            'Takes about 10 minutes',
            'No right or wrong answers, just pick what feels most accurate',
            'Your answers are shared only with your delaware coach',
          ].map(t => (
            <li key={t} style={s.bullet}><div style={s.bulletDot} />{t}</li>
          ))}
        </ul>
        <button style={s.btnPrimary} onClick={handleNext}>Start →</button>
      </div>
    )
  }

  function renderIdentity() {
    return (
      <div>
        <p style={s.eyebrow}>About you</p>
        <h2 style={s.question}>Before we begin, a few details about your role.</h2>
        <div style={{ marginTop: 28 }}>
          <div style={s.fieldGroup}>
            <label style={s.fieldLabel}>Job title</label>
            <input
              style={{ ...s.input, ...(focusedField === 'job_title' && !isReadOnly ? { borderColor: '#EF463C' } : {}) }}
              type="text"
              placeholder="e.g. Finance Manager"
              value={answers.job_title ?? ''}
              onChange={e => setAnswer('job_title', e.target.value)}
              disabled={isReadOnly}
              onFocus={() => { if (!isReadOnly) setFocusedField('job_title') }}
              onBlur={() => setFocusedField(null)}
            />
          </div>
          <div style={s.fieldGroup}>
            <label style={s.fieldLabel}>Department</label>
            <input
              style={{ ...s.input, ...(focusedField === 'department' && !isReadOnly ? { borderColor: '#EF463C' } : {}) }}
              type="text"
              placeholder="e.g. Finance, HR, Operations…"
              value={answers.department ?? ''}
              onChange={e => setAnswer('department', e.target.value)}
              disabled={isReadOnly}
              onFocus={() => { if (!isReadOnly) setFocusedField('department') }}
              onBlur={() => setFocusedField(null)}
            />
          </div>
        </div>
      </div>
    )
  }

  function renderSingle(def: SingleStep) {
    return (
      <div>
        <p style={s.eyebrow}>{def.eyebrow}</p>
        <h2 style={s.question}>{def.question}</h2>
        {def.hint && <p style={s.hint}>{def.hint}</p>}
        <div style={s.options}>
          {def.options.map(opt => (
            <OptionCard
              key={`${step}-${opt.code}`}
              option={opt}
              selected={answers[def.field] === opt.code}
              onClick={() => setAnswer(def.field, opt.code)}
              disabled={isReadOnly}
            />
          ))}
        </div>
      </div>
    )
  }

  function renderMulti(def: MultiStep) {
    const vals: readonly string[] = answers[def.field] ?? []
    return (
      <div>
        <p style={s.eyebrow}>{def.eyebrow}</p>
        <h2 style={s.question}>{def.question}</h2>
        {def.hint && <p style={s.hint}>{def.hint}</p>}
        <div style={s.options}>
          {def.options.map(opt => (
            <MultiCard
              key={`${step}-${opt.code}`}
              option={opt}
              checked={vals.includes(opt.code)}
              onChange={() => toggleMulti(def.field, opt.code)}
              disabled={isReadOnly}
            />
          ))}
        </div>
      </div>
    )
  }

  function renderScale(def: ScaleStep) {
    return (
      <div>
        <p style={s.eyebrow}>{def.eyebrow}</p>
        <h2 style={s.question}>{def.question}</h2>
        <div style={s.scaleRow}>
          {def.options.map(opt => (
            <ScaleCard
              key={`${step}-${opt.code}`}
              option={opt}
              selected={answers[def.field] === opt.code}
              onClick={() => setAnswer(def.field, opt.code)}
              disabled={isReadOnly}
            />
          ))}
        </div>
      </div>
    )
  }

  function renderUsage() {
    return (
      <div>
        <p style={s.eyebrow}>Context: Usage</p>
        <h2 style={s.question}>How are you using AI tools for work right now?</h2>
        <div style={{ marginTop: 28 }}>
          <div style={s.usageSection}>
            <p style={s.subLabel}>How often do you use AI tools for work?</p>
            <div style={s.usageOptions}>
              {FREQ_OPTIONS.map(opt => (
                <OptionCard
                  key={`${step}-freq-${opt.code}`}
                  option={opt}
                  selected={answers.b_freq === opt.code}
                  onClick={() => setAnswer('b_freq', opt.code)}
                  disabled={isReadOnly}
                />
              ))}
            </div>
          </div>
          <div style={s.usageSection}>
            <p style={s.subLabel}>Across how much of your work?</p>
            <div style={s.usageOptions}>
              {BREADTH_OPTIONS.map(opt => (
                <OptionCard
                  key={`${step}-breadth-${opt.code}`}
                  option={opt}
                  selected={answers.b_breadth === opt.code}
                  onClick={() => setAnswer('b_breadth', opt.code)}
                  disabled={isReadOnly}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  function renderText(def: TextStep) {
    return (
      <div>
        <p style={s.eyebrow}>{def.eyebrow}</p>
        <h2 style={s.question}>{def.question}</h2>
        <textarea
          style={{ ...s.textarea, ...(focusedField === def.field && !isReadOnly ? { borderColor: '#EF463C' } : {}) }}
          placeholder="Type your answer here…"
          value={answers[def.field] ?? ''}
          onChange={e => setAnswer(def.field, e.target.value)}
          disabled={isReadOnly}
          onFocus={() => { if (!isReadOnly) setFocusedField(def.field) }}
          onBlur={() => setFocusedField(null)}
        />
      </div>
    )
  }

  function renderConsent() {
    const checked = answers.consent === true
    return (
      <div>
        <p style={s.eyebrow}>Almost done</p>
        <h2 style={s.question}>One last thing before we submit.</h2>
        <p style={{ ...s.hint, marginTop: 10 }}>
          Your answers will be shared with your delaware coach to personalise your learning path. They will not be shared with your employer in a way that identifies you individually. Your personal data will only be used in the purpose of this project.
        </p>
        <div
          style={{ ...s.consentBox, ...(checked ? s.consentBoxChecked : {}) }}
          onClick={isReadOnly ? undefined : () => setAnswer('consent', !checked)}
          role="checkbox"
          aria-checked={checked}
          tabIndex={isReadOnly ? -1 : 0}
          onKeyDown={isReadOnly ? undefined : e => e.key === ' ' && setAnswer('consent', !checked)}
        >
          <div style={{ ...s.consentCheck, ...(checked ? s.consentCheckChecked : {}) }}>
            {checked && <CheckSvg />}
          </div>
          <span style={s.consentText}>
            I understand my answers will be accessible to my delaware coach and used to shape my personalised learning path.
          </span>
        </div>
      </div>
    )
  }

  function renderComplete() {
    return (
      <div>
        <p style={s.eyebrow}>Done</p>
        <h1 style={s.bigHeading}>
          {justCompleted
            ? `Thank you${user?.first_name ? `, ${user.first_name}` : ''}.`
            : 'Assessment complete.'}
        </h1>
        <p style={s.bigBody}>
          {justCompleted
            ? 'Your answers have been saved. Your delaware coach will be in touch with your personalised learning path shortly.'
            : 'Your answers have been saved. Use the back button to review them, or return to the hub.'}
        </p>
        <button style={s.btnPrimary} onClick={() => navigate('/')}>Back to hub</button>
      </div>
    )
  }

  function renderStep() {
    const def = STEPS[step]
    if (!def) return null
    if ('type' in def) {
      switch (def.type) {
        case 'single': return renderSingle(def)
        case 'multi':  return renderMulti(def)
        case 'scale':  return renderScale(def)
        case 'text':   return renderText(def)
      }
    }
    switch (def.id) {
      case 'intro':    return renderIntro()
      case 'identity': return renderIdentity()
      case 'usage':    return renderUsage()
      case 'consent':  return renderConsent()
      case 'complete': return renderComplete()
      default:         return null
    }
  }

  // ── Nav buttons ─────────────────────────────────────────────────────────────

  function renderNavButtons() {
    const isIntro    = step === 0
    const isComplete = step === STEPS.length - 1
    const isSubmit   = !isReadOnly && step === LAST_CONTENT_IDX
    const ok         = canProceed()

    if (isIntro || isComplete) return null // intro has inline button; complete has inline button

    const showBack = isReadOnly ? step > 1 : step > 0
    const nextLabel = saving ? 'Saving…' : isSubmit ? 'Submit' : isReadOnly && step === LAST_CONTENT_IDX ? 'Back to hub' : 'Next →'

    return (
      <div style={s.navBtns}>
        {showBack ? (
          <button
            className="btn-ghost"
            style={s.btnBack}
            onClick={handleBack}
          >
            ← Back
          </button>
        ) : <div />}
        <button
          className="btn-red"
          style={{ ...s.btnPrimary, ...(!ok ? s.btnPrimaryDisabled : {}) }}
          onClick={isReadOnly && step === LAST_CONTENT_IDX ? () => navigate('/') : handleNext}
          disabled={!ok || saving}
        >
          {nextLabel}
        </button>
      </div>
    )
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div style={s.page}>
      <AppNav backTo="/" title="Maturity assessment" />

      {/* Progress bar — two parts */}
      <div style={s.progressBar}>
        <div style={s.progressPart}>
          <span style={s.progressLabel}>Part 1 · Competencies</span>
          <div style={s.progressSegWrap}>
            <div style={{ ...s.progressSegFill, width: `${part1Pct}%` }} />
          </div>
        </div>
        <div style={s.progressPart}>
          <span style={s.progressLabel}>Part 2 · Context</span>
          <div style={s.progressSegWrap}>
            <div style={{ ...s.progressSegFill, width: `${part2Pct}%` }} />
          </div>
        </div>
      </div>

      {/* Read-only banner */}
      {isReadOnly && (
        <div style={s.readonlyBanner}>
          This assessment is complete, your answers are shown for reference only.
        </div>
      )}

      {/* Main content */}
      <main style={{ ...s.main, ...(step === 0 ? s.mainWide : {}) }}>
        {renderStep()}
        {error && <p style={s.errorMsg}>{error}</p>}
        {renderNavButtons()}
      </main>
    </div>
  )
}
