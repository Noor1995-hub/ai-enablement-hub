import { useState, type CSSProperties } from 'react'
import type { PlaybookShared, UseCase, Reframe, Difficulty } from '../../types/domain'

/* ── Difficulty badge palette (semantic, not the mockup's blue) ── */
const DIFFICULTY_BADGE: Record<Difficulty, { bg: string; color: string }> = {
  'Quick Win':        { bg: '#EDFAF4', color: '#1D7A52' },
  'Worth a Session':  { bg: '#FEFCE8', color: '#A16207' },
  'Bigger Build':     { bg: '#FFF1E8', color: '#B24A0F' },
}

/* ── Styles — mirrors the JourneyHome idiom: inline styles, hub card
   treatment (1px #E2E2E2 border, 12px radius, hub shadow), Mulish body /
   Work Sans headings via the --dlw-font-* tokens. ── */
const s = {
  root: { display: 'flex', flexDirection: 'column', gap: 40 },
  section: { display: 'flex', flexDirection: 'column' },
  h2: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 700,
    fontSize: 20, color: 'var(--dlw-black)', margin: '0 0 14px',
  },
  card: {
    border: '1px solid var(--dlw-border)', borderRadius: 12,
    background: '#fff', boxShadow: '0 16px 36px -20px rgba(16,24,32,0.30)',
    padding: '22px 24px',
  },
  paragraph: {
    margin: 0, fontSize: 15, lineHeight: 1.65, color: 'var(--dlw-text)', fontWeight: 300,
  },

  /* Use-case cards */
  ucCard: {
    border: '1px solid var(--dlw-border)', borderRadius: 12,
    background: '#fff', boxShadow: '0 16px 36px -20px rgba(16,24,32,0.30)',
    marginBottom: 14, overflow: 'hidden',
  },
  ucCardStartHere: { border: '2px solid var(--dlw-primary-red)' },
  ucTop: {
    width: '100%', display: 'flex', alignItems: 'center', gap: 12,
    padding: '16px 18px', background: 'none', border: 'none',
    cursor: 'pointer', textAlign: 'left', font: 'inherit', color: 'inherit',
  },
  ucRank: {
    width: 26, height: 26, borderRadius: 8, background: 'var(--dlw-surface)',
    color: 'var(--dlw-muted)', fontWeight: 700, fontSize: 13,
    fontFamily: 'var(--dlw-font-ui)', display: 'flex', alignItems: 'center',
    justifyContent: 'center', flexShrink: 0,
  },
  ucHeading: { display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 },
  ucName: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 16, color: 'var(--dlw-black)',
  },
  ucPain: { fontSize: 13, fontWeight: 300, color: 'var(--dlw-muted)' },
  startTag: {
    background: 'var(--dlw-primary-red)', color: '#fff',
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.04em', padding: '4px 10px', borderRadius: 999,
    flexShrink: 0, whiteSpace: 'nowrap',
  },
  badge: {
    display: 'inline-flex', alignItems: 'center',
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.04em', padding: '4px 10px', borderRadius: 999,
    flexShrink: 0, whiteSpace: 'nowrap',
  },
  chevron: {
    fontSize: 16, color: 'var(--dlw-muted)', flexShrink: 0,
    display: 'inline-block', transition: 'transform 200ms ease',
  },
  ucBody: {
    borderTop: '1px solid var(--dlw-border)', padding: '16px 18px 20px',
    display: 'flex', flexDirection: 'column', gap: 12,
  },
  ucParagraph: { margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--dlw-text)' },
  label: { fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, color: 'var(--dlw-black)' },
  baGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 },
  baBlock: {
    background: 'var(--dlw-surface)', border: '1px solid var(--dlw-border)',
    borderRadius: 10, padding: '10px 12px',
  },
  baLabel: {
    display: 'block', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase',
    color: 'var(--dlw-muted)', marginBottom: 4,
  },
  baText: { margin: 0, fontSize: 13, lineHeight: 1.5, color: 'var(--dlw-text)' },
  assumption: {
    margin: 0, fontSize: 12.5, lineHeight: 1.55, color: '#8A6D1E',
    background: '#FFFBEB', border: '1px dashed #F0D089', borderRadius: 8,
    padding: '8px 10px',
  },

  /* Next moves */
  moveRow: {
    display: 'flex', gap: 12, alignItems: 'flex-start',
    padding: '14px 0', borderBottom: '1px solid var(--dlw-border)',
  },
  moveRowLast: { borderBottom: 'none' },
  moveNum: {
    width: 26, height: 26, borderRadius: '50%', background: 'var(--dlw-primary-red)',
    color: '#fff', fontWeight: 700, fontSize: 13, fontFamily: 'var(--dlw-font-ui)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  moveText: { margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--dlw-text)' },
  moveBold: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, color: 'var(--dlw-black)' },
  moveWhy: { color: 'var(--dlw-muted)' },

  /* Reframes accordion */
  rf: {
    border: '1px solid var(--dlw-border)', borderRadius: 12,
    background: '#fff', marginBottom: 10, overflow: 'hidden',
  },
  rfQuestion: {
    width: '100%', display: 'flex', alignItems: 'center', gap: 8,
    justifyContent: 'space-between', padding: '14px 16px',
    background: 'none', border: 'none', cursor: 'pointer',
    textAlign: 'left', font: 'inherit', color: 'inherit',
  },
  rfHesitation: { fontStyle: 'italic', fontSize: 14, color: 'var(--dlw-text)' },
  rfBody: {
    borderTop: '1px solid var(--dlw-border)', padding: '14px 16px',
    display: 'flex', flexDirection: 'column', gap: 10,
  },
  rfBlock: {
    borderLeft: '3px solid var(--dlw-primary-red)', background: 'var(--dlw-red-tint)',
    borderRadius: '0 8px 8px 0', padding: '8px 12px',
  },
  rfBlockLabel: {
    display: 'block', fontFamily: 'var(--dlw-font-ui)', fontWeight: 700,
    fontSize: 11, letterSpacing: '0.04em', textTransform: 'uppercase',
    color: 'var(--dlw-muted)', marginBottom: 4,
  },
  rfBlockText: { margin: 0, fontSize: 13.5, lineHeight: 1.55, color: 'var(--dlw-text)' },

  /* Do this today CTA */
  cta: {
    background: 'linear-gradient(135deg, var(--dlw-primary-red), var(--dlw-sub-red-2))',
    color: '#fff', borderRadius: 12, padding: '24px 26px',
    boxShadow: '0 16px 36px -20px rgba(16,24,32,0.30)',
  },
  ctaAction: {
    margin: 0, fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 19, lineHeight: 1.5, color: '#fff',
  },
  ctaMeta: {
    display: 'flex', flexWrap: 'wrap', gap: '6px 20px', marginTop: 14,
    paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.25)',
  },
  ctaTime: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 12.5, color: '#fff',
  },
  ctaWhy: { fontSize: 13.5, lineHeight: 1.5, color: 'rgba(255,255,255,0.92)', fontWeight: 300 },
} satisfies Record<string, CSSProperties>

/* ── Use-case card (collapsed header + expandable body) ── */
function UseCaseCard({ uc, open, onToggle }: { uc: UseCase; open: boolean; onToggle: () => void }) {
  const badge = DIFFICULTY_BADGE[uc.difficulty]
  return (
    <div style={{ ...s.ucCard, ...(uc.start_here ? s.ucCardStartHere : {}) }}>
      <button type="button" onClick={onToggle} style={s.ucTop} aria-expanded={open}>
        <span style={s.ucRank}>{uc.rank}</span>
        <span style={s.ucHeading}>
          <span style={s.ucName}>{uc.name}</span>
          {uc.pain_it_kills && <span style={s.ucPain}>{uc.pain_it_kills}</span>}
        </span>
        {uc.start_here && <span style={s.startTag}>★ Start Here</span>}
        <span style={{ ...s.badge, background: badge.bg, color: badge.color }}>{uc.difficulty}</span>
        <span style={{ ...s.chevron, transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>▾</span>
      </button>
      {open && (
        <div style={s.ucBody}>
          {uc.in_practice && (
            <p style={s.ucParagraph}><span style={s.label}>In practice: </span>{uc.in_practice}</p>
          )}
          {(uc.before || uc.after) && (
            <div style={s.baGrid}>
              <div style={s.baBlock}>
                <span style={s.baLabel}>Before</span>
                <p style={s.baText}>{uc.before}</p>
              </div>
              <div style={s.baBlock}>
                <span style={s.baLabel}>After</span>
                <p style={s.baText}>{uc.after}</p>
              </div>
            </div>
          )}
          {uc.impact && (
            <p style={s.ucParagraph}><span style={s.label}>Impact: </span>{uc.impact}</p>
          )}
          {uc.assumption_to_check != null && (
            <p style={s.assumption}>
              <span style={s.label}>Assumption to check: </span>{uc.assumption_to_check}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Reframe accordion row ── */
function ReframeRow({ reframe, open, onToggle }: { reframe: Reframe; open: boolean; onToggle: () => void }) {
  return (
    <div style={s.rf}>
      <button type="button" onClick={onToggle} style={s.rfQuestion} aria-expanded={open}>
        <span style={s.rfHesitation}>&ldquo;{reframe.their_hesitation}&rdquo;</span>
        <span style={{ ...s.chevron, transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>▾</span>
      </button>
      {open && (
        <div style={s.rfBody}>
          <div style={s.rfBlock}>
            <span style={s.rfBlockLabel}>The real concern</span>
            <p style={s.rfBlockText}>{reframe.the_concern}</p>
          </div>
          <div style={s.rfBlock}>
            <span style={s.rfBlockLabel}>Reframe</span>
            <p style={s.rfBlockText}>{reframe.reframe}</p>
          </div>
          <div style={s.rfBlock}>
            <span style={s.rfBlockLabel}>First proof</span>
            <p style={s.rfBlockText}>{reframe.first_proof}</p>
          </div>
        </div>
      )}
    </div>
  )
}

/** Pure presentational render of a learner's playbook — no data fetching.
 *  Shared by the journey page and the admin card; each supplies its own
 *  `PlaybookShared` (fetched separately). Layout/copy follow
 *  docs/design-prototypes/ai-interviewer/mockup.html's "Playbook" tab,
 *  restyled onto the hub's real design system (see index.css --dlw-* tokens). */
export default function Playbook({ shared }: { shared: PlaybookShared }) {
  // Ranks whose card is expanded; the start_here use-case begins open.
  const [openRanks, setOpenRanks] = useState<Set<number>>(
    () => new Set(shared.use_cases.filter(uc => uc.start_here).map(uc => uc.rank)),
  )
  function toggleRank(rank: number) {
    setOpenRanks(prev => {
      const next = new Set(prev)
      if (next.has(rank)) next.delete(rank)
      else next.add(rank)
      return next
    })
  }

  // Reframes have no stable id, so track open state by list index.
  const [openReframes, setOpenReframes] = useState<Set<number>>(() => new Set())
  function toggleReframe(idx: number) {
    setOpenReframes(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const sortedMoves = [...shared.next_moves].sort((a, b) => a.order - b.order)
  const hasToday = Boolean(shared.do_this_today?.action)

  return (
    <div style={s.root}>
      {shared.where_you_are_today && (
        <section style={s.section}>
          <h2 style={s.h2}>Where you are today</h2>
          <div style={s.card}>
            <p style={s.paragraph}>{shared.where_you_are_today}</p>
          </div>
        </section>
      )}

      {shared.use_cases.length > 0 && (
        <section style={s.section}>
          <h2 style={s.h2}>Your AI use-cases</h2>
          {shared.use_cases.map(uc => (
            <UseCaseCard
              key={uc.rank}
              uc={uc}
              open={openRanks.has(uc.rank)}
              onToggle={() => toggleRank(uc.rank)}
            />
          ))}
        </section>
      )}

      {sortedMoves.length > 0 && (
        <section style={s.section}>
          <h2 style={s.h2}>Your next moves</h2>
          <div style={s.card}>
            {sortedMoves.map((move, i) => (
              <div
                key={move.order}
                style={{ ...s.moveRow, ...(i === sortedMoves.length - 1 ? s.moveRowLast : {}) }}
              >
                <span style={s.moveNum}>{i + 1}</span>
                <p style={s.moveText}>
                  <span style={s.moveBold}>{move.move}</span>
                  {move.why_now && <><br /><span style={s.moveWhy}>{move.why_now}</span></>}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {shared.reframes.length > 0 && (
        <section style={s.section}>
          <h2 style={s.h2}>What might be holding you back</h2>
          {shared.reframes.map((rf, idx) => (
            <ReframeRow
              key={idx}
              reframe={rf}
              open={openReframes.has(idx)}
              onToggle={() => toggleReframe(idx)}
            />
          ))}
        </section>
      )}

      {hasToday && (
        <section style={s.section}>
          <h2 style={s.h2}>Do this today</h2>
          <div style={s.cta}>
            <p style={s.ctaAction}>{shared.do_this_today.action}</p>
            {(shared.do_this_today.time_required || shared.do_this_today.why_this_one) && (
              <div style={s.ctaMeta}>
                {shared.do_this_today.time_required && (
                  <span style={s.ctaTime}>⏱ {shared.do_this_today.time_required}</span>
                )}
                {shared.do_this_today.why_this_one && (
                  <span style={s.ctaWhy}>{shared.do_this_today.why_this_one}</span>
                )}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
