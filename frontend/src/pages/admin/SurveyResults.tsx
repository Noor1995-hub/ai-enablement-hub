import {
  COMPETENCY_QA,
  FREQ_LABELS, BREADTH_LABELS, ATTITUDE_LABELS, READINESS_LABELS,
  type CompetencyQA,
} from '../../lib/surveyOptions'
import type { AdminSurvey } from '../../types/domain'
import { s } from './adminStyles'
import { LevelBadge, BandBadge, RungPill, formatDate } from './adminHelpers'

// Maps the competency key to its typed rung column so the lookup below stays
// inside AdminSurvey's keys (no string-index casts).
const RUNG_FIELDS = {
  c1: 'c1_rung', c2: 'c2_rung', c3: 'c3_rung',
  c4: 'c4_rung', c5: 'c5_rung', c6: 'c6_rung',
} as const satisfies Record<CompetencyQA['key'], keyof AdminSurvey>

export default function SurveyResults({ survey }: { survey: AdminSurvey }) {
  const completedDate = survey.completed_at ? formatDate(survey.completed_at) : null

  return (
    <div>
      {/* overall result */}
      <div style={{ padding: '12px 14px', background: '#FAFAF9', border: '1px solid #F0EFED', borderRadius: 8, marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          {survey.score_level && (
            <div>
              <p style={{ fontSize: 10, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, color: '#B6B6B6', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 5 }}>Maturity level</p>
              <LevelBadge level={survey.score_level} />
            </div>
          )}
          {survey.usage_band && (
            <div>
              <p style={{ fontSize: 10, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, color: '#B6B6B6', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 5 }}>AI usage frequency</p>
              <BandBadge band={survey.usage_band} />
            </div>
          )}
          {survey.safety_flag && (
            <div>
              <p style={{ fontSize: 10, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, color: '#B6B6B6', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 5 }}>Flag</p>
              <span style={{ ...s.badge, background: '#FFF0EF', color: '#C42828' }}>⚠ Data safety</span>
            </div>
          )}
        </div>
        {completedDate && (
          <p style={{ fontSize: 11, color: '#B6B6B6', fontFamily: 'var(--dlw-font-ui)', marginTop: 10 }}>Completed {completedDate}</p>
        )}
      </div>

      {/* identity */}
      {(survey.job_title || survey.department) && (
        <div style={{ marginBottom: 14, padding: '9px 12px', background: '#FAFAF9', borderRadius: 6, border: '1px solid #F0EFED' }}>
          <p style={s.surveyQLabel}>Role</p>
          <p style={{ fontSize: 13, color: '#3C3C3C', margin: 0 }}>
            {[survey.job_title, survey.department].filter(Boolean).join(' · ')}
          </p>
        </div>
      )}

      {/* competency Q&As */}
      <p style={{ ...s.panelSectionTitle, marginBottom: 10 }}>Competency answers</p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
        {COMPETENCY_QA.map(({ key, field, label, options, multi }) => {
          const rung = survey[RUNG_FIELDS[key]]
          const raw  = survey[field]
          let answerText: string | null

          if (multi && Array.isArray(raw)) {
            answerText = raw.map(code => options[code]).filter(Boolean).join(' / ')
          } else {
            answerText = raw && !Array.isArray(raw) ? options[raw] : null
          }

          return (
            <div key={key} style={{ padding: '10px 12px', background: '#FAFAF9', borderRadius: 8, border: '1px solid #F0EFED' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, marginBottom: answerText ? 8 : 0 }}>
                <span style={{ fontSize: 11, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, color: '#8A8A8A', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  {label}
                </span>
                <RungPill rung={rung} />
              </div>
              {answerText && (
                <p style={{ fontSize: 13, color: '#3C3C3C', lineHeight: 1.55, margin: 0 }}>"{answerText}"</p>
              )}
              {!answerText && (
                <p style={{ fontSize: 13, color: '#C4C4C4', margin: 0, fontStyle: 'italic' }}>No answer recorded</p>
              )}
            </div>
          )
        })}
      </div>

      {/* usage context */}
      {(survey.b_freq || survey.b_breadth || survey.b_attitude || survey.b_readiness) && (
        <>
          <p style={{ ...s.panelSectionTitle, marginBottom: 10 }}>Usage context</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
            {survey.b_freq && (
              <div style={{ padding: '10px 12px', background: '#FAFAF9', borderRadius: 6, border: '1px solid #F0EFED' }}>
                <p style={s.surveyQLabel}>Frequency</p>
                <p style={{ fontSize: 13, color: '#3C3C3C', margin: 0 }}>{(FREQ_LABELS as Record<string, string>)[survey.b_freq] ?? survey.b_freq}</p>
              </div>
            )}
            {survey.b_breadth && (
              <div style={{ padding: '10px 12px', background: '#FAFAF9', borderRadius: 6, border: '1px solid #F0EFED' }}>
                <p style={s.surveyQLabel}>Breadth</p>
                <p style={{ fontSize: 13, color: '#3C3C3C', margin: 0 }}>{(BREADTH_LABELS as Record<string, string>)[survey.b_breadth] ?? survey.b_breadth}</p>
              </div>
            )}
            {survey.b_attitude != null && (
              <div style={{ padding: '10px 12px', background: '#FAFAF9', borderRadius: 6, border: '1px solid #F0EFED' }}>
                <p style={s.surveyQLabel}>Attitude towards AI</p>
                <p style={{ fontSize: 13, color: '#3C3C3C', margin: 0 }}>{(ATTITUDE_LABELS as Record<number, string>)[survey.b_attitude] ?? survey.b_attitude}</p>
              </div>
            )}
            {survey.b_readiness != null && (
              <div style={{ padding: '10px 12px', background: '#FAFAF9', borderRadius: 6, border: '1px solid #F0EFED' }}>
                <p style={s.surveyQLabel}>Readiness to change</p>
                <p style={{ fontSize: 13, color: '#3C3C3C', margin: 0 }}>{(READINESS_LABELS as Record<number, string>)[survey.b_readiness] ?? survey.b_readiness}</p>
              </div>
            )}
          </div>
        </>
      )}

      {/* open questions */}
      {(survey.q_excitement || survey.q_timesink) && (
        <>
          <p style={{ ...s.panelSectionTitle, marginBottom: 10 }}>Open questions</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {survey.q_excitement && (
              <div>
                <p style={s.surveyQLabel}>What excites them about AI</p>
                <p style={s.surveyQText}>{survey.q_excitement}</p>
              </div>
            )}
            {survey.q_timesink && (
              <div>
                <p style={s.surveyQLabel}>Biggest time sink they'd like help with</p>
                <p style={s.surveyQText}>{survey.q_timesink}</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
