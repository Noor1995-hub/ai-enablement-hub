import { useEffect, useState } from 'react'
import { formatDate } from '../admin/adminHelpers'
import { resolveTrackColor } from '../../lib/trackColors'
import type { ProposalStatus, ProposalSummaryOut } from '../../types/domain'
import { PROPOSAL_PAGE_SIZE, useProposals, useRunImprovement } from './api'
import { Chip, EmptyState, ErrorState, Spinner } from './kit'
import type { ChipTone } from './kit'

type StatusFilter = ProposalStatus | undefined

const STATUS_PILLS: { value: StatusFilter; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'failed', label: 'Failed' },
  { value: 'approved', label: 'Approved' },
  { value: undefined, label: 'All' },
]

/** Content AI (`/admin/content-improvement`) — the review queue for AI-drafted
 * lesson revisions. "Draft proposals" asks the agent to revise lessons that
 * have accepted, not-yet-incorporated feedback; each draft lands here as
 * `pending` and only reaches a learner when an admin approves it. Not
 * project-scoped: lessons are shared catalogue content. */
export default function ContentImprovementPage() {
  const [status, setStatus] = useState<StatusFilter>('pending')
  const [page, setPage] = useState(1)
  const run = useRunImprovement()

  useEffect(() => setPage(1), [status])

  const { data, isLoading, error, refetch } = useProposals({ status, page })
  const pendingCountQuery = useProposals({ status: 'pending', limit: 1 })

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PROPOSAL_PAGE_SIZE)) : 1

  // Reviewing the last item on the final page can drop the server's total by a
  // whole page; clamp back into range (same idiom as FeedbackPage).
  useEffect(() => {
    if (page > totalPages) setPage(totalPages)
  }, [page, totalPages])

  if (isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (error || !data) {
    return <ErrorState message={error?.message ?? 'Failed to load content proposals.'} onRetry={() => void refetch()} />
  }

  return (
    <div>
      <h1 className="adm-page-title">Content AI</h1>
      <p className="adm-page-sub">
        AI-drafted lesson revisions built from accepted feedback. Nothing here reaches a learner until you approve it.
      </p>

      <div className="adm-toolbar">
        <div className="adm-pills">
          {STATUS_PILLS.map(pill => (
            <button
              key={pill.label}
              type="button"
              className={status === pill.value ? 'adm-pill active' : 'adm-pill'}
              onClick={() => setStatus(pill.value)}
            >
              {pill.label}
              {pill.value === 'pending' && <span className="adm-pill-n">{pendingCountQuery.data?.total ?? 0}</span>}
            </button>
          ))}
        </div>
        <div className="adm-push-right">
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm"
            disabled={run.isPending}
            onClick={() => run.mutate(3)}
          >
            {run.isPending ? 'Drafting…' : 'Draft proposals'}
          </button>
        </div>
      </div>

      {run.isSuccess && (
        <p className="adm-subtext">
          Drafted {run.data.proposed} proposal{run.data.proposed === 1 ? '' : 's'}
          {run.data.skipped > 0 && ` · ${run.data.skipped} lesson${run.data.skipped === 1 ? '' : 's'} could not be drafted (see the Failed tab)`}
          {run.data.remaining > 0 && ` · ${run.data.remaining} lesson${run.data.remaining === 1 ? '' : 's'} still waiting — run again`}
          {run.data.proposed === 0 && run.data.skipped === 0 && run.data.remaining === 0 && ' — nothing was waiting'}
        </p>
      )}
      {run.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {run.error instanceof Error ? run.error.message : 'Failed to run the improvement pass.'}
        </p>
      )}

      {data.items.length === 0 ? (
        <EmptyState
          title="No proposals here."
          hint="Accept some lesson feedback, then use “Draft proposals”."
        />
      ) : (
        data.items.map(item => <ProposalRow key={item.id} item={item} />)
      )}

      <div className="adm-pager">
        <span className="adm-pager-info">
          Page {page} of {totalPages} · {data.total} total
        </span>
        <div className="adm-pager-actions">
          <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            Previous
          </button>
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}

interface ProposalRowProps {
  item: ProposalSummaryOut
}

/** One proposal in the queue. Task 8 adds the expandable diff and the
 * approve/reject actions to this component. */
function ProposalRow({ item }: ProposalRowProps) {
  const done = item.status !== 'pending'
  const dotColor = resolveTrackColor({ required_level: item.track_level, is_introduction: false })

  return (
    <div className={`adm-ci-card${done ? ' adm-ci-card-done' : ''}`}>
      <div className="adm-ci-head">
        <strong>{item.lesson_title}</strong>
        <Chip tone={statusTone(item.status)}>{statusLabel(item.status)}</Chip>
        <span className="adm-ci-when">{formatDate(item.created_at)}</span>
      </div>

      <div className="adm-ci-loc">
        <span className="adm-loc-chip">
          <span className="adm-loc-label">Track</span>
          <span className="adm-loc-dot" style={{ background: dotColor }} />
          {item.track_name}
        </span>
        <span className="adm-loc-chip">
          <span className="adm-loc-label">Module</span>
          {item.module_title}
        </span>
        <span className="adm-loc-chip">
          <span className="adm-loc-label">Feedback</span>
          {item.source_feedback_count} item{item.source_feedback_count === 1 ? '' : 's'}
        </span>
        <a
          className="adm-btn adm-btn-subtle adm-btn-sm"
          href={`/learning/lesson/${item.lesson_id}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          open lesson
        </a>
      </div>

      {/* Agent output — rendered as plain text, never as HTML or markdown. */}
      <p className="adm-ci-summary">{item.summary}</p>
    </div>
  )
}

function statusTone(status: ProposalStatus): ChipTone {
  if (status === 'approved') return 'good'
  if (status === 'failed') return 'warn'
  return 'default'
}

function statusLabel(status: ProposalStatus): string {
  const labels: Record<ProposalStatus, string> = {
    pending: 'Pending review',
    approved: 'Applied',
    rejected: 'Discarded',
    superseded: 'Superseded',
    failed: 'Could not draft',
  }
  return labels[status]
}
