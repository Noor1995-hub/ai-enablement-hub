import { Link } from 'react-router-dom'
import { LEVELS } from '../../lib/levels'
import type { AttentionItemOut, FunnelOut, MaturityDistributionOut } from '../../types/domain'
import { useDashboard, useSendReminder } from './api'
import { Card, Chip, EmptyState, ErrorState, Spinner, Tile } from './kit'
import { useScope } from './useScope'

type FunnelStepKey = 'invited' | 'activated' | 'assessed' | 'started' | 'completed_track'

const FUNNEL_STEPS: { key: FunnelStepKey; label: string }[] = [
  { key: 'invited', label: 'Invited' },
  { key: 'activated', label: 'Activated' },
  { key: 'assessed', label: 'Assessed' },
  { key: 'started', label: 'Learning started' },
  { key: 'completed_track', label: 'Completed a track' },
]

// Single-hue ordinal ramp, light -> dark (one color per funnel step) — every
// step also renders its count/conversion as text, so the ramp is never the
// only signal. Lifted verbatim from docs/design-prototypes/admin-redesign
// common.js FUNNEL_RAMP.
const FUNNEL_RAMP = ['#EE9089', '#EA6A60', '#EF463C', '#C42828', '#941914']

/** Dashboard screen (spec §3.1, `/admin` index route). One `useDashboard` call
 * drives the whole page; scope (all-projects vs one project) comes from the
 * URL via `useScope()`. Prototype: docs/design-prototypes/admin-redesign
 * option-b.html `dashboard()` + common.js `tile()` / `funnelHTML()` /
 * `levelRowsHTML()` / `attentionRowsHTML()`. */
export default function DashboardPage() {
  const scope = useScope()
  const { data, isLoading, error, refetch } = useDashboard(scope.projectId)

  if (isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (error || !data) {
    return <ErrorState message={error?.message ?? 'Failed to load the dashboard.'} onRetry={() => void refetch()} />
  }

  // Unscoped ("All projects") is the only view where a learner's company
  // needs calling out — scoped views already show the one company via the
  // topbar's scope switcher.
  const unscoped = scope.projectId === null

  return (
    <div>
      <h1 className="adm-page-title">Dashboard</h1>
      <p className="adm-page-sub">
        {unscoped ? 'Learner activity across all projects.' : 'Learner activity for this project.'}
      </p>

      <div className="adm-tiles">
        <Tile label="Learners" value={data.tiles.learners} />
        <Tile label="Active this week" value={data.tiles.active_week} />
        <Tile label="Need attention" value={data.tiles.attention} alert={data.tiles.attention > 0} />
        <Tile label="New feedback" value={data.tiles.new_feedback} />
      </div>

      <Card title="Needs attention">
        <AttentionList items={data.attention} unscoped={unscoped} />
      </Card>

      <div className="adm-grid-2">
        {data.funnels.map(funnel => (
          <Card key={funnel.project_id} title={`${funnel.company_name} · ${funnel.project_name}`}>
            <Funnel funnel={funnel} />
          </Card>
        ))}
      </div>

      <Card title="Maturity distribution">
        <MaturityDistribution maturity={data.maturity} />
      </Card>
    </div>
  )
}

function AttentionList({ items, unscoped }: { items: AttentionItemOut[]; unscoped: boolean }) {
  if (items.length === 0) {
    return <EmptyState title="All learners on track" />
  }
  return (
    <div className="adm-attn">
      {items.map(item => (
        <AttentionRow key={item.user_id} item={item} unscoped={unscoped} />
      ))}
    </div>
  )
}

function AttentionRow({ item, unscoped }: { item: AttentionItemOut; unscoped: boolean }) {
  const sendReminder = useSendReminder()

  const status = sendReminder.data?.email_status
  const feedback = sendReminder.isError
    ? 'Failed to send'
    : status === 'sent'
      ? 'Reminder sent'
      : status === 'failed'
        ? 'Failed to send'
        : status === 'disabled'
          ? 'Email not configured'
          : status === 'skipped'
            ? 'Reminder skipped'
            : null

  const search = item.project_id ? `?project=${item.project_id}` : ''

  return (
    <div className="adm-attn-row">
      <span className="adm-attn-who">{item.name}</span>
      {unscoped && item.company_name && <Chip>{item.company_name}</Chip>}
      <span className="adm-attn-why">{item.reason}</span>
      <span className="adm-attn-act">
        {feedback && <span className="adm-attn-feedback">{feedback}</span>}
        <button
          type="button"
          className="adm-btn adm-btn-ghost adm-btn-sm"
          onClick={() => sendReminder.mutate(item.user_id)}
          disabled={sendReminder.isPending}
        >
          {sendReminder.isPending ? <Spinner size="sm" /> : <MailIcon />}
          Remind
        </button>
        <Link className="adm-btn adm-btn-subtle adm-btn-sm" to={{ pathname: `/admin/people/${item.user_id}`, search }}>
          View
        </Link>
      </span>
    </div>
  )
}

function Funnel({ funnel }: { funnel: FunnelOut }) {
  const max = funnel.invited || 1
  let previous: number | null = null

  return (
    <>
      {FUNNEL_STEPS.map((step, i) => {
        const value = funnel[step.key]
        const conversion = previous === null ? null : Math.round((value / (previous || 1)) * 100)
        previous = value
        return (
          <div className="adm-funnel-row" key={step.key}>
            <div className="adm-funnel-stage">{step.label}</div>
            <div className="adm-funnel-bar-track">
              <div className="adm-funnel-bar" style={{ width: `${(value / max) * 100}%`, background: FUNNEL_RAMP[i] }} />
            </div>
            <div className="adm-funnel-meta">
              <b>{value}</b>
              {conversion !== null && <span> · {conversion}%</span>}
            </div>
          </div>
        )
      })}
    </>
  )
}

function MaturityDistribution({ maturity }: { maturity: MaturityDistributionOut }) {
  const max = Math.max(...LEVELS.map(level => maturity[level.code]), 1)

  return (
    <>
      {LEVELS.map(level => {
        const value = maturity[level.code]
        return (
          <div className="adm-level-row" key={level.code}>
            <span className="adm-level-badge">
              <span className="adm-level-swatch" style={{ background: level.color }} />
              {level.name}
            </span>
            <div className="adm-level-bar-track">
              <div className="adm-level-bar" style={{ width: `${(value / max) * 100}%`, background: level.color }} />
            </div>
            <span className="adm-level-n">{value}</span>
          </div>
        )
      })}
    </>
  )
}

function MailIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x={2} y={4} width={20} height={16} rx={2} />
      <path d="m22 7-10 6L2 7" />
    </svg>
  )
}
