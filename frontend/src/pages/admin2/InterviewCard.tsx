import { useState, type ReactNode } from 'react'
import Playbook from '../../components/interview/Playbook'
import { s } from '../admin/adminStyles'
import type { AdminInterview, PlaybookInternal } from '../../types/domain'
import { useInterview, useResetInterview } from './api'
import { Chip, ConfirmButton, EmptyState, ErrorState, Spinner } from './kit'
import type { ChipTone } from './kit'

const TIER_TONE: Record<string, ChipTone> = {
  RICH: 'good',
  PARTIAL: 'warn',
  THIN: 'default',
}

/** Admin-only view of a learner's AI interview — status/input-quality tier at
 * a glance, the delaware-internal analysis (never shown to the learner), the
 * learner-facing playbook (the same `<Playbook>` the journey page renders),
 * and the raw transcript as plain text. Wired to `useInterview` with the same
 * isLoading/error/data ladder as the sibling "Assessment results" card
 * (UserDetailPage.tsx's `useSurvey` wiring). */
export default function InterviewCard({ userId }: { userId: string }) {
  const q = useInterview(userId)
  const reset = useResetInterview()

  if (q.isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (q.error) {
    return <ErrorState message={q.error.message} onRetry={() => void q.refetch()} />
  }

  if (!q.data) return null
  const data = q.data

  if (data.status === 'not_started') {
    return <EmptyState title="This person hasn't taken the interview yet." />
  }

  return (
    <div>
      {data.status === 'in_progress' && (
        <p className="adm-empty-hint" style={{ marginBottom: 16 }}>
          Interview in progress — no playbook generated yet.
        </p>
      )}

      {data.status === 'complete' && (
        <>
          {data.tier && (
            <div style={{ marginBottom: 20 }}>
              <p style={s.surveyQLabel}>Input quality</p>
              <Chip tone={TIER_TONE[data.tier] ?? 'default'}>{data.tier}</Chip>
            </div>
          )}

          {data.internal && <InternalAnalysis internal={data.internal} />}

          {data.shared && (
            <div style={{ marginTop: 28 }}>
              <p style={{ ...s.panelSectionTitle, marginBottom: 14 }}>Shared playbook</p>
              <Playbook shared={data.shared} />
            </div>
          )}
        </>
      )}

      <TranscriptBlock transcript={data.transcript} />

      <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #F0EFED' }}>
        <ConfirmButton
          label="Reset interview"
          confirmLabel="Yes, delete this interview"
          busy={reset.isPending}
          onConfirm={() => reset.mutate(userId)}
        />
        {reset.isError && (
          <p className="adm-form-msg adm-form-msg-err">
            {reset.error instanceof Error ? reset.error.message : 'Failed to reset the interview.'}
          </p>
        )}
      </div>
    </div>
  )
}

// ── Internal analysis (admin-only) ──────────────────────────────────────────

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <p style={{ ...s.panelSectionTitle, marginBottom: 10 }}>{title}</p>
      {children}
    </div>
  )
}

function Field({ label, text }: { label: string; text: string | null | undefined }) {
  if (!text) return null
  return (
    <div style={{ marginBottom: 10 }}>
      <p style={s.surveyQLabel}>{label}</p>
      <p style={s.surveyQText}>{text}</p>
    </div>
  )
}

function MiniField({ label, text }: { label: string; text: string | null | undefined }) {
  if (!text) return null
  return (
    <div>
      <span style={{ ...s.surveyQLabel, display: 'block' }}>{label}</span>
      <span style={{ fontSize: 12.5, color: '#3C3C3C' }}>{text}</span>
    </div>
  )
}

function BulletList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div style={{ marginBottom: 10 }}>
      <p style={s.surveyQLabel}>{label}</p>
      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {items.map((item, i) => (
          <li key={i} style={{ fontSize: 13, color: '#3C3C3C', lineHeight: 1.6, marginBottom: 4 }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

const subCardStyle = {
  padding: '10px 12px',
  background: '#FAFAF9',
  border: '1px solid #F0EFED',
  borderRadius: 8,
  marginBottom: 8,
}

function InputQualitySection({ iq }: { iq: PlaybookInternal['input_quality'] }) {
  return (
    <Section title="Input quality">
      <Chip tone={TIER_TONE[iq.tier] ?? 'default'}>{iq.tier}</Chip>
      <Field label="Evidence" text={iq.evidence} />
      <BulletList label="What to probe next" items={iq.what_to_probe_next} />
    </Section>
  )
}

function PersonSection({ person }: { person: PlaybookInternal['person'] }) {
  return (
    <Section title="Person">
      <Field label="Role reality" text={person.role_reality} />
      <Field label="Influence" text={person.influence} />
      <Field label="Decision rights" text={person.decision_rights} />
      <Field label="Champion potential" text={person.champion_potential} />
      <Field label="Confidence" text={person.confidence} />
    </Section>
  )
}

function PainsSection({ pains }: { pains: PlaybookInternal['pains'] }) {
  if (pains.length === 0) return null
  return (
    <Section title="Pains">
      {pains.map((p, i) => (
        <div key={i} style={subCardStyle}>
          <p style={{ fontSize: 14, fontWeight: 600, color: '#101820', margin: '0 0 6px' }}>{p.pain}</p>
          <Field label="Evidence" text={p.evidence} />
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <MiniField label="Frequency" text={p.frequency} />
            <MiniField label="Est. time cost" text={p.est_time_cost} />
            <MiniField label="Basis" text={p.basis} />
            <MiniField label="Confidence" text={p.confidence} />
          </div>
        </div>
      ))}
    </Section>
  )
}

function BlockersSection({ blockers }: { blockers: PlaybookInternal['blockers'] }) {
  const hasStated = blockers.stated.length > 0
  const hasDiagnosed = blockers.diagnosed.length > 0
  if (!hasStated && !hasDiagnosed) return null
  return (
    <Section title="Blockers">
      <BulletList label="Stated" items={blockers.stated} />
      {hasDiagnosed && (
        <div>
          <p style={s.surveyQLabel}>Diagnosed</p>
          {blockers.diagnosed.map((d, i) => (
            <div key={i} style={subCardStyle}>
              <p style={{ fontSize: 13.5, fontWeight: 600, color: '#101820', margin: '0 0 4px' }}>{d.type}</p>
              <p style={s.surveyQText}>{d.reasoning}</p>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 6 }}>
                <MiniField label="Basis" text={d.basis} />
                <MiniField label="Confidence" text={d.confidence} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function MaturitySection({ maturity }: { maturity: PlaybookInternal['maturity'] }) {
  return (
    <Section title="Maturity">
      <Field label="Placement" text={maturity.placement} />
      <Field label="Behavioural evidence" text={maturity.behavioural_evidence} />
      <Field label="Vs. self-reported" text={maturity.vs_self_reported} />
      <Field label="Trajectory" text={maturity.trajectory} />
    </Section>
  )
}

function SystemsSection({ systems }: { systems: PlaybookInternal['systems_landscape'] }) {
  if (systems.length === 0) return null
  return (
    <Section title="Systems landscape">
      {systems.map((sys, i) => (
        <div key={i} style={subCardStyle}>
          <p style={{ fontSize: 13.5, fontWeight: 600, color: '#101820', margin: '0 0 4px' }}>{sys.system}</p>
          <Field label="How used" text={sys.how_used} />
          <Field label="Implication" text={sys.implication} />
        </div>
      ))}
    </Section>
  )
}

function EngagementNotesSection({ notes }: { notes: PlaybookInternal['engagement_notes'] }) {
  const empty =
    notes.opportunities.length === 0 && notes.risks.length === 0 && notes.follow_up_questions.length === 0
  if (empty) return null
  return (
    <Section title="Engagement notes">
      <BulletList label="Opportunities" items={notes.opportunities} />
      <BulletList label="Risks" items={notes.risks} />
      <BulletList label="Follow-up questions" items={notes.follow_up_questions} />
    </Section>
  )
}

function InternalAnalysis({ internal }: { internal: PlaybookInternal }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 16, color: '#101820', margin: '0 0 16px' }}>
        Internal analysis{' '}
        <span style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 400, fontSize: 11.5, color: '#B6B6B6' }}>
          (admin-only — never shown to the learner)
        </span>
      </p>
      <InputQualitySection iq={internal.input_quality} />
      <PersonSection person={internal.person} />
      <PainsSection pains={internal.pains} />
      <BlockersSection blockers={internal.blockers} />
      <MaturitySection maturity={internal.maturity} />
      <SystemsSection systems={internal.systems_landscape} />
      {internal.company_context && (
        <Section title="Company context">
          <p style={s.surveyQText}>{internal.company_context}</p>
        </Section>
      )}
      <EngagementNotesSection notes={internal.engagement_notes} />
    </div>
  )
}

// ── Transcript (plain text — never dangerouslySetInnerHTML) ─────────────────

function TranscriptBlock({ transcript }: { transcript: AdminInterview['transcript'] }) {
  const [open, setOpen] = useState(false)
  if (transcript.length === 0) return null

  return (
    <div style={{ marginTop: 28 }}>
      <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" onClick={() => setOpen(o => !o)}>
        {open ? 'Hide' : 'Show'} transcript ({transcript.length} messages)
      </button>
      {open && (
        <div
          style={{
            marginTop: 12,
            maxHeight: 420,
            overflowY: 'auto',
            border: '1px solid #F0EFED',
            borderRadius: 8,
            background: '#FAFAF9',
            padding: '12px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {transcript.map((m, i) => (
            <div key={i}>
              <p style={{ ...s.surveyQLabel, marginBottom: 2 }}>{m.role}</p>
              {/* Plain text on purpose — content is rendered as a React child
                  (default-escaped), never via dangerouslySetInnerHTML. */}
              <div style={{ fontSize: 13, color: '#3C3C3C', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {m.content}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
