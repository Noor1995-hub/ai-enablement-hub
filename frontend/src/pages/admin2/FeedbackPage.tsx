import { useEffect, useState } from 'react'
import { formatDate } from '../admin/adminHelpers'
import { resolveTrackColor } from '../../lib/trackColors'
import type { AdminFeedbackOut, FeedbackStatus } from '../../types/domain'
import { FEEDBACK_PAGE_SIZE, useFeedback, usePatchFeedback, useSuggestTriage, useTracks } from './api'
import { Chip, EmptyState, ErrorState, Spinner } from './kit'
import type { ChipTone } from './kit'
import { useScope } from './useScope'

type StatusFilter = FeedbackStatus | undefined

const STATUS_PILLS: { value: StatusFilter; label: string }[] = [
  { value: 'new', label: 'New' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: undefined, label: 'All' },
]

/** Feedback triage queue (spec §3.5, `/admin/feedback`). Carries the AI triage
 * hint from the feedback-driven content-improvement feature: "Suggest triage"
 * fills `ai_suggested_status`/`ai_rationale` on `new` items that have none, and
 * each such card then shows the suggestion + reason with the matching action
 * ringed. The suggestion never changes an item's real status — the admin still
 * clicks. Prototype: docs/design-prototypes/admin-redesign option-b.html
 * `feedback()` + common.js `mountFeedback()`. */
export default function FeedbackPage() {
  const scope = useScope()
  const unscoped = scope.projectId === null

  const [status, setStatus] = useState<StatusFilter>('new')
  const [track, setTrack] = useState<string | undefined>(undefined)
  const [page, setPage] = useState(1)

  // A filter/scope change invalidates the current page (same idiom as
  // PeoplePage).
  useEffect(() => setPage(1), [status, track, scope.projectId])

  const { data, isLoading, error, refetch } = useFeedback({
    status,
    track,
    project: scope.projectId,
    page,
  })

  // Independent of the active pill — always "how many are new right now" —
  // and deliberately the SAME query the sidebar badge (AdminShell) fires, so
  // the two share one cache entry and one number.
  const newCountQuery = useFeedback({ status: 'new', project: scope.projectId, limit: 1 })

  const suggestTriage = useSuggestTriage()

  const tracksQuery = useTracks()
  const sortedTracks = [...(tracksQuery.data ?? [])].sort((a, b) => a.sort_order - b.sort_order)

  // `data ? … : 1` keeps this computed every render (including while loading,
  // before data exists) so the clamp effect right below — a hook — can stay
  // above the early returns and never skip a render's worth of hook calls.
  const totalPages = data ? Math.max(1, Math.ceil(data.total / FEEDBACK_PAGE_SIZE)) : 1

  // A triage action can shrink the CURRENT filter's result set out from under
  // whatever page the admin is sitting on — e.g. accepting the last "new"
  // item on page 2 of 2 drops the server's total to exactly one page.
  // usePatchFeedback's onSettled refetch then comes back with 0 items for a
  // now out-of-range offset even though total > 0 elsewhere (page 1). Clamp
  // back into range whenever the data we have says the current page no
  // longer exists. Deliberately a separate effect from the filter-change
  // reset above (different trigger, different target value — clamping to
  // `totalPages` here would fight that effect's unconditional reset to `1`
  // on every filter change if they were merged) — harmless if both fire in
  // the same commit, since a same-value setState is a no-op.
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
    return <ErrorState message={error?.message ?? 'Failed to load feedback.'} onRetry={() => void refetch()} />
  }

  return (
    <div>
      <h1 className="adm-page-title">Feedback</h1>
      <p className="adm-page-sub">Review what learners report; accepted items land on the content backlog.</p>

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
              {pill.value === 'new' && <span className="adm-pill-n">{newCountQuery.data?.total ?? 0}</span>}
            </button>
          ))}
        </div>
        <div className="adm-push-right">
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm"
            disabled={suggestTriage.isPending}
            onClick={() => suggestTriage.mutate({ project: scope.projectId })}
          >
            {suggestTriage.isPending ? 'Suggesting…' : 'Suggest triage'}
          </button>
        </div>
      </div>
      {suggestTriage.isSuccess && (
        <p className="adm-subtext">
          Suggested {suggestTriage.data.suggested} item{suggestTriage.data.suggested === 1 ? '' : 's'}
          {suggestTriage.data.remaining > 0 && ` · ${suggestTriage.data.remaining} still without a suggestion — run again`}
        </p>
      )}
      {suggestTriage.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {suggestTriage.error instanceof Error ? suggestTriage.error.message : 'Failed to generate triage suggestions.'}
        </p>
      )}

      <div className="adm-toolbar adm-filter-row">
        <span className="adm-filter-label">
          <SearchIcon /> Filter
        </span>
        <span className="adm-select-look">
          <GridIcon />
          <select value={track ?? 'all'} onChange={e => setTrack(e.target.value === 'all' ? undefined : e.target.value)}>
            <option value="all">All tracks</option>
            {sortedTracks.map(t => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </span>
        <span className="adm-subtext adm-push-right">
          {data.total} item{data.total === 1 ? '' : 's'}
        </span>
      </div>

      {data.items.length === 0 ? (
        <EmptyState title="Nothing matches these filters." />
      ) : (
        data.items.map(item => <FeedbackCard key={item.id} item={item} unscoped={unscoped} onSelectTrack={setTrack} />)
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

function initials(name: string): string {
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

interface FeedbackCardProps {
  item: AdminFeedbackOut
  unscoped: boolean
  onSelectTrack: (trackId: string) => void
}

/** One card's worth of state — its own `usePatchFeedback()` instance so a
 * pending/error state on one card's Dismiss/Accept/Mark-as-new never bleeds
 * into any other card. */
function FeedbackCard({ item, unscoped, onSelectTrack }: FeedbackCardProps) {
  const patch = usePatchFeedback()
  const done = item.status !== 'new'
  const dotColor = resolveTrackColor({ required_level: item.track_level, is_introduction: false })

  return (
    <div className={`adm-fb-card${done ? ' adm-fb-card-done' : ''}`}>
      <div className="adm-fb-head">
        <span className="adm-user-cell">
          <span className="adm-user-avatar">{initials(item.user_name)}</span>
          <span>
            <span className="adm-user-name">{item.user_name}</span>
            {unscoped && (
              <>
                <br />
                <span className="adm-user-email">{item.company_name ?? item.project_name ?? '—'}</span>
              </>
            )}
          </span>
        </span>
        {done && <Chip tone={statusTone(item.status)}>{statusLabel(item.status)}</Chip>}
        <span className="adm-fb-when">{formatDate(item.created_at)}</span>
      </div>

      <div className="adm-fb-loc">
        <button type="button" className="adm-loc-chip" title="Filter on this track" onClick={() => onSelectTrack(item.track_id)}>
          <span className="adm-loc-label">Track</span>
          <span className="adm-loc-dot" style={{ background: dotColor }} />
          {item.track_name}
        </button>
        <span className="adm-loc-chip">
          <span className="adm-loc-label">Module</span>
          {item.module_title}
        </span>
        <span className="adm-loc-chip">
          <span className="adm-loc-label">Lesson</span>
          {item.lesson_title}
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

      <p className="adm-fb-quote">“{item.message}”</p>

      {item.status === 'new' && item.ai_suggested_status && (
        <div className="adm-fb-ai">
          <span className="adm-fb-ai-label">
            AI suggests {item.ai_suggested_status === 'accepted' ? 'accept' : 'dismiss'}
          </span>
          <span className="adm-fb-ai-reason">{item.ai_rationale}</span>
        </div>
      )}

      <div className="adm-fb-foot">
        <div className="adm-fb-actions">
          {item.status === 'new' ? (
            <>
              <button
                type="button"
                className={`adm-btn adm-btn-ghost adm-btn-sm${item.ai_suggested_status === 'dismissed' ? ' adm-btn-suggested' : ''}`}
                disabled={patch.isPending}
                onClick={() => patch.mutate({ id: item.id, status: 'dismissed' })}
              >
                Dismiss
              </button>
              <button
                type="button"
                className={`adm-btn adm-btn-red adm-btn-sm${item.ai_suggested_status === 'accepted' ? ' adm-btn-suggested' : ''}`}
                disabled={patch.isPending}
                onClick={() => patch.mutate({ id: item.id, status: 'accepted' })}
              >
                <CheckIcon /> Accept
              </button>
            </>
          ) : (
            <button
              type="button"
              className="adm-btn adm-btn-subtle adm-btn-sm"
              disabled={patch.isPending}
              onClick={() => patch.mutate({ id: item.id, status: 'new' })}
            >
              Mark as new
            </button>
          )}
        </div>
      </div>
      {patch.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {patch.error instanceof Error ? patch.error.message : 'Failed to update this item.'}
        </p>
      )}
    </div>
  )
}

function statusTone(status: FeedbackStatus): ChipTone {
  return status === 'accepted' ? 'good' : 'default'
}

function statusLabel(status: FeedbackStatus): string {
  return status === 'accepted' ? 'Accepted' : 'Dismissed'
}

function SearchIcon() {
  return (
    <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx={11} cy={11} r={8} />
      <path d="m21 21-4.35-4.35" />
    </svg>
  )
}

function GridIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x={3} y={3} width={7} height={7} rx={1} />
      <rect x={14} y={3} width={7} height={7} rx={1} />
      <rect x={14} y={14} width={7} height={7} rx={1} />
      <rect x={3} y={14} width={7} height={7} rx={1} />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
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
