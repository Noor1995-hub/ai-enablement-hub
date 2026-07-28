import { useEffect, useState } from 'react'
import { formatDate } from '../admin/adminHelpers'
import type { CalibrationNoteOut, CalibrationNoteStatus } from '../../types/domain'
import {
  CALIBRATION_NOTE_PAGE_SIZE,
  useCalibrationNotes,
  useGraduateCalibrationNote,
  useReviewCalibrationNote,
} from './api'
import { Chip, ConfirmButton, EmptyState, ErrorState, Spinner } from './kit'
import type { ChipTone } from './kit'

type StatusFilter = CalibrationNoteStatus | undefined

const STATUS_PILLS: { value: StatusFilter; label: string }[] = [
  { value: 'suggested', label: 'Suggested' },
  { value: 'approved', label: 'Approved' },
  { value: 'retired', label: 'Graduated' },
  { value: 'rejected', label: 'Rejected' },
  { value: undefined, label: 'All' },
]

/** The human gate between the agent's self-critique and its own prompt. The
 * agent suggests a note after an admin edits one of its drafts; nothing here
 * influences a future draft until it is approved. Rendered as a tab of
 * ContentImprovementPage — it is a sub-view of Content AI, not its own route. */
export default function CalibrationNotesQueue() {
  const [status, setStatus] = useState<StatusFilter>('suggested')
  const [page, setPage] = useState(1)
  const review = useReviewCalibrationNote()
  const graduate = useGraduateCalibrationNote()

  useEffect(() => setPage(1), [status])

  const { data, isLoading, error, refetch } = useCalibrationNotes({ status, page })
  const totalPages = data ? Math.max(1, Math.ceil(data.total / CALIBRATION_NOTE_PAGE_SIZE)) : 1

  // Reviewing the last item on the final page can drop the server's total by a
  // whole page; clamp back into range (same idiom as the proposals queue).
  useEffect(() => {
    if (page > totalPages) setPage(totalPages)
  }, [page, totalPages])

  const actionError = review.error ?? graduate.error

  if (isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (error || !data) {
    return <ErrorState message={error?.message ?? 'Failed to load calibration notes.'} onRetry={() => void refetch()} />
  }

  return (
    <div>
      <p className="adm-page-sub">
        Guidance the agent suggested about its own drafting, after comparing a draft with the
        version you accepted. A note changes nothing until you approve it, and an approved note
        is guidance for the agent, never a rule the validator enforces.
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
            </button>
          ))}
        </div>
      </div>

      {graduate.isSuccess && (
        <p className="adm-subtext">
          Retired. Paste this into the calibration section of <code>backend/prompts/house_style.md</code> and commit it —
          the app never writes that file:
          <br />
          <code>{graduate.data.paste_ready}</code>
        </p>
      )}
      {actionError && (
        <p className="adm-form-msg adm-form-msg-err">
          {actionError instanceof Error ? actionError.message : 'Failed to update the note.'}
        </p>
      )}

      {data.items.length === 0 ? (
        <EmptyState title="No notes here." hint="Notes appear after you accept a draft you edited." />
      ) : (
        data.items.map(item => (
          <NoteRow
            key={item.id}
            item={item}
            onReview={decision => review.mutate({ noteId: item.id, decision })}
            onGraduate={() => graduate.mutate(item.id)}
            busy={review.isPending || graduate.isPending}
          />
        ))
      )}

      <div className="adm-pager">
        <span className="adm-pager-info">
          Page {page} of {totalPages} · {data.total} total
        </span>
        <div className="adm-pager-actions">
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm"
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
          >
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

interface NoteRowProps {
  item: CalibrationNoteOut
  onReview: (decision: 'approve' | 'reject') => void
  onGraduate: () => void
  busy: boolean
}

/** One suggested note. `suggested` is the only status an admin can approve or
 * reject — every other status is terminal server-side, so those rows show no
 * actions beyond graduating an approved note. */
function NoteRow({ item, onReview, onGraduate, busy }: NoteRowProps) {
  const done = item.status !== 'suggested'

  return (
    <div className={`adm-ci-card${done ? ' adm-ci-card-done' : ''}`}>
      <div className="adm-ci-head">
        <Chip tone={statusTone(item.status)}>{statusLabel(item.status)}</Chip>
        <span className="adm-ci-when">{formatDate(item.created_at)}</span>
      </div>

      {/* Agent output — plain text, never HTML or markdown. */}
      <p className="adm-ci-summary">{item.note}</p>

      <div className="adm-ci-loc">
        <span className="adm-loc-chip">
          <span className="adm-loc-label">From</span>
          {item.source_lesson_title ?? '(lesson since deleted)'}
        </span>
      </div>

      <div className="adm-ci-foot">
        {item.status === 'suggested' && (
          <div className="adm-ci-actions">
            <button
              type="button"
              className="adm-btn adm-btn-ghost adm-btn-sm"
              disabled={busy}
              onClick={() => onReview('reject')}
            >
              Reject
            </button>
            <ConfirmButton
              label="Approve"
              confirmLabel="Yes, approve"
              tone="neutral"
              busy={busy}
              onConfirm={() => onReview('approve')}
            />
          </div>
        )}
        {item.status === 'approved' && (
          <div className="adm-ci-actions">
            <ConfirmButton
              label="Mark as graduated"
              confirmLabel="Yes, retire it"
              tone="neutral"
              busy={busy}
              onConfirm={onGraduate}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function statusTone(status: CalibrationNoteStatus): ChipTone {
  if (status === 'approved') return 'good'
  if (status === 'retired') return 'warn'
  return 'default'
}

function statusLabel(status: CalibrationNoteStatus): string {
  const labels: Record<CalibrationNoteStatus, string> = {
    suggested: 'Awaiting review',
    approved: 'In the prompt',
    rejected: 'Rejected',
    retired: 'Graduated to house style',
  }
  return labels[status]
}
