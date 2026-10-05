import { useId, useState, type CSSProperties } from 'react'
import type { Difficulty, PlaybookShared, UseCase } from '../../types/domain'
import { parseSummary } from '../../lib/playbookSummary'
import { DEFAULT_INTERVIEW_LANGUAGE, PLAYBOOK_STRINGS, formatUseCaseCount, type InterviewLanguage, type PlaybookStrings } from '../../lib/interviewStrings'

/* The learner's playbook (redesign D, 2 October): C's order (Do this today first, the use
   cases as cards, next moves across, hesitations as cards, the summary last) in A's design
   language. Learner-only: the admin card keeps components/interview/Playbook.tsx, unchanged. */

/* The semantic difficulty palette, the same values as Playbook.tsx (kept separate so the
   admin component is not touched). */
const DIFFICULTY_CHIP: Record<Difficulty, { bg: string; color: string }> = {
  'Quick Win': { bg: '#EDFAF4', color: '#1D7A52' },
  'Worth a Session': { bg: '#FEFCE8', color: '#A16207' },
  'Bigger Build': { bg: '#FFF1E8', color: '#B24A0F' },
}
const CHIP_FALLBACK = { bg: 'var(--dlw-surface)', color: '#6B6B6B' }

function difficultyLabel(d: Difficulty, t: PlaybookStrings): string {
  const labels: Record<Difficulty, string> = {
    'Quick Win': t.difficultyQuickWin, 'Worth a Session': t.difficultyWorthASession, 'Bigger Build': t.difficultyBiggerBuild,
  }
  return labels[d] ?? d
}

/** The playbook strings end inline labels with ": " ("In practice: "); as a block label the
 *  colon goes. */
const blockLabel = (label: string) => label.replace(/:\s*$/, '')

/* What inline styles can't express: the red-dot markers, hover and focus, and the narrow-window
   and 200% zoom layouts. Local, with an `lpb-` prefix (the iv-/pb-/lp- idiom). */
const CSS = `
.lpb { display: flex; flex-direction: column; overflow-wrap: anywhere; }
.lpb-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: var(--dlw-dot-red); flex: none; }
.lpb-h2 { font-family: var(--dlw-font-body); font-weight: 800; font-size: 25px; line-height: 1.2; letter-spacing: -0.012em; color: var(--dlw-black); margin: 0; }
.lpb-sec { margin-bottom: 48px; }
.lpb-sec-head { display: flex; align-items: baseline; justify-content: space-between; gap: 6px 16px; flex-wrap: wrap; margin-bottom: 18px; }
.lpb-count { margin: 0; font-size: 14px; color: #6B6B6B; font-weight: 400; }
.lpb-today { border-radius: 18px; background: var(--dlw-red-tint); border: 1.5px solid rgba(196, 40, 40, .28); padding: 30px 36px 28px; margin-bottom: 48px; }
.lpb-today h2 { display: flex; align-items: center; gap: 10px; margin: 0 0 12px; font-family: var(--dlw-font-ui); font-size: 14px; font-weight: 600; color: var(--dlw-primary-red); }
.lpb-act { margin: 0 0 22px; font-size: 30px; line-height: 1.25; font-weight: 800; letter-spacing: -0.015em; max-width: 32ch; color: var(--dlw-black); overflow-wrap: anywhere; }
.lpb-meta { display: flex; align-items: center; gap: 12px 22px; flex-wrap: wrap; padding-top: 18px; border-top: 1px solid rgba(196, 40, 40, .18); }
.lpb-time { display: inline-flex; background: #fff; color: var(--dlw-black); border: 1px solid rgba(196, 40, 40, .28); border-radius: 999px; padding: 4px 13px; font-family: var(--dlw-font-ui); font-weight: 700; font-size: 13.5px; }
.lpb-why { margin: 0; font-size: 15.5px; font-weight: 400; color: var(--dlw-text); }
.lpb-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: start; }
.lpb-card { border: 1px solid var(--dlw-border); border-radius: 14px; padding: 18px 20px 14px; background: #fff; display: flex; flex-direction: column; gap: 8px; scroll-margin-top: 16px; overflow-wrap: anywhere; }
.lpb-card.is-start { border: 2px solid var(--dlw-black); }
.lpb-card-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.lpb-rank { font-weight: 800; font-size: 15px; color: var(--dlw-black); width: 28px; height: 28px; border-radius: 50%; border: 1.5px solid var(--dlw-black); display: inline-flex; align-items: center; justify-content: center; }
.lpb-start { display: inline-flex; align-items: center; gap: 7px; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 12.5px; color: var(--dlw-primary-red); }
.lpb-start .lpb-dot { width: 8px; height: 8px; }
.lpb-chip { display: inline-flex; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 11.5px; padding: 3px 10px; border-radius: 999px; white-space: nowrap; }
.lpb-card h3 { margin: 0; font-weight: 800; font-size: 18px; line-height: 1.3; color: var(--dlw-black); }
.lpb-pain { margin: 0; font-size: 14.5px; line-height: 1.5; color: #6B6B6B; font-weight: 400; }
.lpb-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 2px 0 0; padding: 0; list-style: none; }
.lpb-tags li { font-family: var(--dlw-font-ui); font-size: 12px; font-weight: 500; color: var(--dlw-text); border: 1px solid var(--dlw-border); border-radius: 6px; padding: 2px 8px; }
.lpb-tags li.is-colleagues { border-color: transparent; background: var(--dlw-surface); }
.lpb-toggle { align-self: flex-start; border: none; background: none; padding: 6px 0; cursor: pointer; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 13px; color: var(--dlw-black); text-decoration: underline; text-underline-offset: 3px; text-decoration-color: var(--dlw-faint); }
.lpb-toggle:hover { text-decoration-color: currentColor; }
.lpb-toggle:focus-visible, .lpb a:focus-visible { outline: 2px solid var(--dlw-primary-red); outline-offset: 2px; }
.lpb-detail { display: flex; flex-direction: column; gap: 12px; padding-top: 12px; border-top: 1px solid var(--dlw-border); font-size: 14.5px; line-height: 1.55; font-weight: 400; }
.lpb-detail p { margin: 0; }
.lpb-label { display: block; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 12.5px; color: #6B6B6B; margin-bottom: 2px; }
.lpb-ba { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.lpb-ba div { background: var(--dlw-surface); border-radius: 10px; padding: 10px 12px; font-size: 13.5px; }
.lpb-assume { background: #FFFBEB; border: 1px dashed #E8C46A; border-radius: 10px; padding: 9px 12px; font-size: 14px; color: #6B5414; }
.lpb-assume .lpb-label { color: #6B5414; }
/* One column per move (the prompt asks for 2 to 4), set inline as --lpb-steps. */
.lpb-steps { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(var(--lpb-steps, 3), minmax(0, 1fr)); }
.lpb-steps li { position: relative; padding-right: 24px; overflow-wrap: anywhere; }
.lpb-steps li:not(:last-child)::before { content: ""; position: absolute; left: 42px; right: 10px; top: 15px; height: 2px; background: var(--dlw-border); }
.lpb-num { width: 32px; height: 32px; border-radius: 50%; background: var(--dlw-black); color: #fff; font-weight: 800; font-size: 14px; display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
.lpb-move { margin: 0 0 2px; font-weight: 800; font-size: 17px; line-height: 1.4; color: var(--dlw-black); }
.lpb-why-now { margin: 0 0 4px; font-size: 15px; line-height: 1.5; color: var(--dlw-text); font-weight: 400; }
.lpb-for { margin: 0; font-size: 13.5px; color: #6B6B6B; font-weight: 400; }
.lpb-for a { color: var(--dlw-black); text-underline-offset: 3px; text-decoration-color: var(--dlw-faint); }
.lpb-rfs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.lpb-rf { background: var(--dlw-warm-grey); border-radius: 14px; padding: 22px 24px; overflow-wrap: anywhere; }
.lpb-rf p { margin: 0 0 8px; font-size: 15px; line-height: 1.6; font-weight: 400; color: var(--dlw-text); }
.lpb-rf p:last-child { margin: 0; }
.lpb-q { font-size: 19px !important; line-height: 1.4 !important; font-weight: 700 !important; font-style: italic; color: var(--dlw-black) !important; margin-bottom: 12px !important; }
.lpb-concern { font-size: 13.5px !important; color: #6B6B6B !important; }
.lpb-summary { padding-top: 40px; border-top: 1px solid var(--dlw-border); margin-bottom: 0; }
.lpb-lead { font-size: 19px; line-height: 1.55; font-weight: 400; color: var(--dlw-black); margin: 18px 0 22px; max-width: 60ch; }
.lpb-bullets { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 40px; }
.lpb-bullets li { position: relative; padding-left: 26px; font-size: 16.5px; line-height: 1.55; color: var(--dlw-text); font-weight: 400; }
.lpb-bullets li::before { content: ""; position: absolute; left: 2px; top: .52em; width: 9px; height: 9px; border-radius: 50%; background: var(--dlw-dot-red); }
@media (max-width: 1100px) { .lpb-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 900px) {
  .lpb-cards, .lpb-steps, .lpb-rfs, .lpb-bullets { grid-template-columns: 1fr; }
  .lpb-today { padding: 24px; }
  .lpb-act { font-size: 24px; }
  .lpb-steps li { padding: 0 0 20px 48px; }
  .lpb-steps li:not(:last-child)::before { left: 15px; right: auto; top: 36px; bottom: 0; width: 2px; height: auto; }
  .lpb-num { position: absolute; left: 0; top: 0; }
}
`

const s = { srOnly: { position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0 } } satisfies Record<string, CSSProperties>

function UseCaseCard({ uc, idBase, open, onToggle, t }: { uc: UseCase; idBase: string; open: boolean; onToggle: () => void; t: PlaybookStrings }) {
  const chip = DIFFICULTY_CHIP[uc.difficulty] ?? CHIP_FALLBACK
  const detailId = `${idBase}-detail`
  const hasTags = uc.systems_involved.length > 0 || uc.cross_functional
  return (
    <article className={`lpb-card${uc.start_here ? ' is-start' : ''}`} id={idBase} aria-labelledby={`${idBase}-name`}>
      <div className="lpb-card-top">
        <span className="lpb-rank">{uc.rank}</span>
        {uc.start_here && <span className="lpb-start"><span className="lpb-dot" aria-hidden="true" />{t.startHere}</span>}
        <span className="lpb-chip" style={{ background: chip.bg, color: chip.color }}>{difficultyLabel(uc.difficulty, t)}</span>
      </div>
      <h3 id={`${idBase}-name`}>{uc.name}</h3>
      {uc.pain_it_kills && <p className="lpb-pain">{uc.pain_it_kills}</p>}
      {hasTags && (
        <ul className="lpb-tags" aria-label={t.systems}>
          {uc.systems_involved.map(sys => <li key={sys}>{sys}</li>)}
          {uc.cross_functional && <li className="is-colleagues">{t.withColleagues}</li>}
        </ul>
      )}
      <button type="button" className="lpb-toggle" aria-expanded={open} aria-controls={detailId} onClick={onToggle}>
        {open ? t.hideDetails : t.showDetails}
      </button>
      {open && (
        <div className="lpb-detail" id={detailId}>
          {uc.in_practice && <p><span className="lpb-label">{blockLabel(t.inPractice)}</span>{uc.in_practice}</p>}
          {(uc.before || uc.after) && (
            <div className="lpb-ba">
              <div><span className="lpb-label">{t.before}</span>{uc.before}</div>
              <div><span className="lpb-label">{t.after}</span>{uc.after}</div>
            </div>
          )}
          {uc.impact && <p><span className="lpb-label">{blockLabel(t.impact)}</span>{uc.impact}</p>}
          {uc.assumption_to_check != null && (
            <p className="lpb-assume"><span className="lpb-label">{blockLabel(t.assumptionToCheck)}</span>{uc.assumption_to_check}</p>
          )}
        </div>
      )}
    </article>
  )
}

/** The redesigned playbook for the learner. Pure presentational; the page supplies the h1. */
export default function LearnerPlaybook({ shared, language = DEFAULT_INTERVIEW_LANGUAGE }: { shared: PlaybookShared; language?: InterviewLanguage }) {
  const t = PLAYBOOK_STRINGS[language]
  const id = useId()
  const [openRanks, setOpenRanks] = useState<Set<number>>(() => new Set())
  const toggle = (rank: number) => setOpenRanks(prev => {
    const next = new Set(prev)
    if (next.has(rank)) next.delete(rank)
    else next.add(rank)
    return next
  })

  const useCases = [...shared.use_cases].sort((a, b) => a.rank - b.rank)
  const cardId = (rank: number) => `${id}-uc-${rank}`
  const moves = [...shared.next_moves].sort((a, b) => a.order - b.order)
  const summary = parseSummary(shared.where_you_are_today ?? '')
  const today = shared.do_this_today
  const hasToday = Boolean(today?.action)

  return (
    <div className="lpb">
      <style>{CSS}</style>

      {hasToday && (
        <section className="lpb-today" aria-labelledby={`${id}-today`}>
          <h2 id={`${id}-today`}><span className="lpb-dot" aria-hidden="true" />{t.doThisToday}</h2>
          <p className="lpb-act">{today.action}</p>
          {(today.time_required || today.why_this_one) && (
            <div className="lpb-meta">
              {today.time_required && <span className="lpb-time"><span style={s.srOnly}>{t.timeNeeded}</span>{today.time_required}</span>}
              {today.why_this_one && <p className="lpb-why">{today.why_this_one}</p>}
            </div>
          )}
        </section>
      )}

      {useCases.length > 0 && (
        <section className="lpb-sec" aria-labelledby={`${id}-ucs`}>
          <div className="lpb-sec-head">
            <h2 className="lpb-h2" id={`${id}-ucs`}>{t.useCases}</h2>
            <p className="lpb-count">{formatUseCaseCount(useCases.length, t)}</p>
          </div>
          <div className="lpb-cards">
            {useCases.map(uc => (
              <UseCaseCard key={uc.rank} uc={uc} idBase={cardId(uc.rank)} open={openRanks.has(uc.rank)} onToggle={() => toggle(uc.rank)} t={t} />
            ))}
          </div>
        </section>
      )}

      {moves.length > 0 && (
        <section className="lpb-sec" aria-labelledby={`${id}-moves`}>
          <div className="lpb-sec-head"><h2 className="lpb-h2" id={`${id}-moves`}>{t.nextMoves}</h2></div>
          <ol className="lpb-steps" style={{ '--lpb-steps': moves.length } as CSSProperties}>
            {moves.map((m, i) => {
              const linked = useCases.find(uc => uc.rank === m.linked_use_case)
              return (
                <li key={m.order}>
                  <span className="lpb-num" aria-hidden="true">{i + 1}</span>
                  <p className="lpb-move">{m.move}</p>
                  {m.why_now && <p className="lpb-why-now">{m.why_now}</p>}
                  {linked && <p className="lpb-for">{t.forUseCase}<a href={`#${cardId(linked.rank)}`}>{linked.name}</a></p>}
                </li>
              )
            })}
          </ol>
        </section>
      )}

      {shared.reframes.length > 0 && (
        <section className="lpb-sec" aria-labelledby={`${id}-rfs`}>
          <div className="lpb-sec-head"><h2 className="lpb-h2" id={`${id}-rfs`}>{t.holdingYouBack}</h2></div>
          <div className="lpb-rfs">
            {shared.reframes.map((rf, i) => (
              <div className="lpb-rf" key={i}>
                <p className="lpb-q">&ldquo;{rf.their_hesitation}&rdquo;</p>
                <p>{rf.reframe}</p>
                <p><strong style={{ fontWeight: 800, color: 'var(--dlw-black)' }}>{t.firstProof}: </strong>{rf.first_proof}</p>
                <p className="lpb-concern">{t.realConcern}: {rf.the_concern}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {(summary.intro.length > 0 || summary.bullets.length > 0) && (
        <section className="lpb-sec lpb-summary" aria-labelledby={`${id}-sum`}>
          <h2 className="lpb-h2" id={`${id}-sum`}>{t.whereYouAreToday}</h2>
          {summary.intro.map((line, i) => <p className="lpb-lead" key={i}>{line}</p>)}
          {summary.bullets.length > 0 && <ul className="lpb-bullets">{summary.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>}
        </section>
      )}
    </div>
  )
}
