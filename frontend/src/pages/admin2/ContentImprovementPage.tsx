import { useEffect, useState } from 'react'
import { formatDate } from '../admin/adminHelpers'
import { resolveTrackColor } from '../../lib/trackColors'
import type { CalibrationNoteBrief, ProposalStatus, ProposalSummaryOut } from '../../types/domain'
import LessonEditor from '../../components/lesson/LessonEditor'
import ProposalDiff from './ProposalDiff'
import { PROPOSAL_PAGE_SIZE, useGenerateLearnCard, useProposal, useProposals, useReviewProposal, useRunImprovement } from './api'
import { Chip, ConfirmButton, EmptyState, ErrorState, Spinner } from './kit'
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
  // Owned by the PAGE, not by the row that triggers it. Accepting a proposal
  // flips it to `approved`, which drops it from the default `pending` filter as
  // soon as the invalidated list refetches — the row unmounts, taking any
  // row-local mutation state with it. Held here, the "generating…" line and a
  // failure (a 502 from /critique) outlive the row that started them.
  const learnCard = useGenerateLearnCard()

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
          <ConfirmButton
            label="Draft proposals"
            confirmLabel="Yes, draft"
            busy={run.isPending}
            onConfirm={() => run.mutate(3)}
            tone="neutral"
          />
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

      {/* Learn-card state lives here rather than in the row, which is usually
          gone by the time any of this resolves (see useGenerateLearnCard above). */}
      {learnCard.isPending && (
        <p className="adm-subtext">Asking the agent what it can learn from your edits…</p>
      )}
      {learnCard.isSuccess && (
        <p className="adm-subtext">
          The agent wrote a learn card from your edits — open that proposal on the Approved tab to read it.
        </p>
      )}
      {learnCard.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {learnCard.error instanceof Error ? learnCard.error.message : 'Failed to generate the learn card.'}
        </p>
      )}

      {data.items.length === 0 ? (
        <EmptyState
          title="No proposals here."
          hint="Accept some lesson feedback, then use “Draft proposals”."
        />
      ) : (
        data.items.map(item => <ProposalRow key={item.id} item={item} learnCard={learnCard} />)
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
  /** The page's single learn-card mutation, shared by every row: a row cannot
   * own this one, because accepting is exactly what unmounts it. */
  learnCard: ReturnType<typeof useGenerateLearnCard>
}

/** One proposal in the queue. The diff payload carries two whole
 * content_blocks arrays, so it is fetched only once the admin expands the row
 * (`useProposal(null)` is disabled). Approve is a two-step ConfirmButton
 * because it overwrites live lesson content — never a native window.confirm.
 *
 * Compare and edit are separate modes, not a hybrid: the diff's row-level
 * alignment cannot survive inside the block editor's own layout, so "Edit the
 * draft" swaps the comparison out for the real block editor rather than
 * blending them. `workingBlocks` is the single source of truth for what
 * Accept submits — seeded from the fetched draft, and updated live by the
 * editor while in edit mode. */
function ProposalRow({ item, learnCard }: ProposalRowProps) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  // The working copy of the draft. null until the detail loads; thereafter it
  // is what Accept submits, so it is the single source of truth for what lands.
  const [workingBlocks, setWorkingBlocks] = useState<unknown[] | null>(null)
  const detail = useProposal(expanded ? item.id : null)
  const review = useReviewProposal()
  // The learn-card mutation is shared across rows, so "Generating…" belongs to
  // whichever row actually asked for it (`variables` is the proposal id); any
  // in-flight call disables the button everywhere, since a second one would
  // overwrite the first's state.
  const cardPending = learnCard.isPending && learnCard.variables === item.id
  const done = item.status !== 'pending'
  const dotColor = resolveTrackColor({ required_level: item.track_level, is_introduction: false })

  // Seed the working copy once the detail arrives.
  useEffect(() => {
    if (detail.data && workingBlocks === null) setWorkingBlocks(detail.data.proposed_blocks)
  }, [detail.data, workingBlocks])

  // Collapsing the row drops the working copy so re-expanding starts fresh
  // from whatever the server now has (and leaves edit mode).
  useEffect(() => {
    if (!expanded) {
      setWorkingBlocks(null)
      setEditing(false)
    }
  }, [expanded])

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
          <ExternalIcon /> open lesson
        </a>
      </div>

      {/* Agent output — rendered as plain text, never as HTML or markdown. */}
      <p className="adm-ci-summary">{item.summary}</p>

      {expanded && (
        <>
          {detail.isLoading && (
            <div className="adm-loading">
              <Spinner />
            </div>
          )}
          {detail.error && (
            <ErrorState
              message={detail.error.message}
              onRetry={() => void detail.refetch()}
            />
          )}
          {detail.data && (
            <>
              <ul className="adm-ci-feedback">
                {detail.data.source_feedback.map(feedback => (
                  <li key={feedback.id}>“{feedback.message}”</li>
                ))}
              </ul>

              {/* A `failed` proposal stores no blocks at all, so diffing it
                  against the lesson would list every existing block as
                  `removed` and read as "the agent proposes to wipe this
                  lesson" — when it actually means nothing was drafted. The
                  summary above already carries the reason. */}
              {detail.data.status === 'failed' || detail.data.proposed_blocks.length === 0 ? (
                <p className="adm-subtext">
                  No revision was drafted for this lesson, so there is nothing to compare.
                </p>
              ) : editing ? (
                <div className="adm-ci-editor">
                  <p className="adm-subtext">
                    Editing the draft. Accept applies what is here, and the agent gets a learn card
                    from whatever you changed.
                  </p>
                  <p className="adm-subtext">
                    Images and videos cannot be added here — media is managed in the lesson editor.
                  </p>
                  <LessonEditor
                    embedded
                    lesson={{
                      id: detail.data.lesson_id,
                      title: detail.data.lesson_title,
                      content_blocks: workingBlocks ?? detail.data.proposed_blocks,
                    }}
                    onLiveChange={next => setWorkingBlocks(next.content_blocks)}
                  />
                </div>
              ) : (
                <ProposalDiff
                  base={detail.data.base_blocks}
                  proposed={workingBlocks ?? detail.data.proposed_blocks}
                />
              )}

              {detail.data.status === 'pending' && detail.data.proposed_blocks.length > 0 && (
                <button
                  type="button"
                  className="adm-btn adm-btn-subtle adm-btn-sm"
                  onClick={() => setEditing(open => !open)}
                >
                  {editing ? 'Back to comparison' : 'Edit the draft'}
                </button>
              )}

              {detail.data.critiqued_at && (
                <LearnCard
                  agentWrong={detail.data.critique_agent_wrong ?? ''}
                  adminPreferred={detail.data.critique_admin_preferred ?? ''}
                  notes={detail.data.calibration_notes ?? []}
                />
              )}
            </>
          )}
        </>
      )}

      <div className="adm-ci-foot">
        <button
          type="button"
          className="adm-btn adm-btn-subtle adm-btn-sm"
          onClick={() => setExpanded(open => !open)}
        >
          {expanded ? 'Hide changes' : 'Review changes'}
        </button>
        {item.status === 'pending' && (
          <div className="adm-ci-actions">
            <button
              type="button"
              className="adm-btn adm-btn-ghost adm-btn-sm"
              disabled={review.isPending}
              onClick={() => review.mutate({ proposalId: item.id, decision: 'reject' })}
            >
              Discard
            </button>
            <ConfirmButton
              label="Accept"
              confirmLabel="Yes, accept"
              busy={review.isPending}
              onConfirm={() => {
                const edited =
                  workingBlocks !== null &&
                  JSON.stringify(workingBlocks) !== JSON.stringify(detail.data?.proposed_blocks)
                    ? workingBlocks
                    : undefined
                review.mutate(
                  { proposalId: item.id, decision: 'approve', editedBlocks: edited },
                  // Only ask for a learn card when there is actually a
                  // difference to learn from. The backend refuses otherwise.
                  { onSuccess: () => { if (edited) learnCard.mutate(item.id) } },
                )
              }}
            />
          </div>
        )}
        {item.status === 'failed' && (
          <div className="adm-ci-actions">
            <button
              type="button"
              className="adm-btn adm-btn-ghost adm-btn-sm"
              disabled={review.isPending}
              onClick={() => review.mutate({ proposalId: item.id, decision: 'reject' })}
            >
              Dismiss and retry later
            </button>
          </div>
        )}
        {item.status === 'approved' && detail.data?.edited_blocks && !detail.data.critiqued_at && (
          <div className="adm-ci-actions">
            <button
              type="button"
              className="adm-btn adm-btn-subtle adm-btn-sm"
              disabled={learnCard.isPending}
              onClick={() => learnCard.mutate(item.id)}
            >
              {cardPending ? 'Generating…' : 'Generate learn card'}
            </button>
          </div>
        )}
      </div>
      {/* A learn-card failure is reported by the PAGE, not here — this row is
          usually already unmounted by then. `review` stays row-local: a failed
          review leaves the proposal `pending`, so the row is still on screen. */}
      {review.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {review.error instanceof Error ? review.error.message : 'Failed to review this proposal.'}
        </p>
      )}
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

function ExternalIcon() {
  return (
    <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <path d="M15 3h6v6" />
      <path d="M10 14 21 3" />
    </svg>
  )
}

interface LearnCardProps {
  agentWrong: string
  adminPreferred: string
  notes: CalibrationNoteBrief[]
}

/** What the agent concluded from the difference between its draft and what you
 * accepted. Every string here is model output, so it renders as plain text.
 * The notes are SUGGESTIONS: they change nothing until they are approved. */
function LearnCard({ agentWrong, adminPreferred, notes }: LearnCardProps) {
  return (
    <div className="adm-ci-learn">
      <span className="adm-ci-block-kind">What the agent learned</span>
      <p className="adm-ci-block-text">{agentWrong}</p>
      <p className="adm-ci-block-text">{adminPreferred}</p>
      {notes.length > 0 && (
        <>
          <span className="adm-ci-block-kind">Suggested calibration notes</span>
          <ul className="adm-ci-feedback">
            {notes.map(note => (
              <li key={note.id}>{note.note}</li>
            ))}
          </ul>
          <p className="adm-subtext">
            These are suggestions. They do not affect future drafts until they are approved.
          </p>
        </>
      )}
    </div>
  )
}
