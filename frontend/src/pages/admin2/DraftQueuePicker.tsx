import { useState } from 'react'
import { resolveTrackColor } from '../../lib/trackColors'
import type { ImprovementQueueItem } from '../../types/domain'
import { MAX_LESSONS_PER_RUN, useImprovementQueue } from './api'
import { EmptyState, ErrorState, Modal, Spinner } from './kit'

interface DraftQueuePickerProps {
  /** Fired with the picked lesson ids. The caller owns the mutation so its
   * result can outlive this modal, which closes as soon as the run starts. */
  onDraft: (lessonIds: string[]) => void
  onClose: () => void
  busy: boolean
}

/** Pick which lessons the agent should redraft.
 *
 * Explicit selection rather than "draft the oldest N": every lesson here is a
 * whole-lesson rewrite billed to the Anthropic key, and an admin who has just
 * triaged a batch of feedback knows which lessons they actually care about.
 *
 * The cap mirrors MAX_LESSONS_PER_RUN on the backend, which refuses a bigger
 * selection outright — the ceiling is the run's time budget against the
 * container ingress timeout, not a model limit. Enforced here too so the admin
 * finds out while ticking boxes rather than via a 422.
 */
export default function DraftQueuePicker({ onDraft, onClose, busy }: DraftQueuePickerProps) {
  const [picked, setPicked] = useState<string[]>([])
  const { data, isLoading, error, refetch } = useImprovementQueue(true)

  const atCap = picked.length >= MAX_LESSONS_PER_RUN

  function toggle(lessonId: string) {
    setPicked(current =>
      current.includes(lessonId)
        ? current.filter(id => id !== lessonId)
        : // Silently ignoring a tick past the cap would read as a broken
          // checkbox; the rows are disabled at the cap instead, so this is
          // only a belt-and-braces guard.
          current.length < MAX_LESSONS_PER_RUN
          ? [...current, lessonId]
          : current,
    )
  }

  const body = isLoading ? (
    <div className="adm-loading">
      <Spinner />
    </div>
  ) : error || !data ? (
    <ErrorState
      message={error?.message ?? 'Failed to load the draft queue.'}
      onRetry={() => void refetch()}
    />
  ) : data.items.length === 0 ? (
    <EmptyState
      title="Nothing is waiting for a draft."
      hint="Accept some lesson feedback on the Feedback screen first."
    />
  ) : (
    <>
      <p className="adm-subtext">
        Each lesson you pick is one full rewrite by the agent, using every accepted feedback item on
        it. Nothing reaches a learner until you approve the draft.
      </p>
      <ul className="adm-ci-picklist">
        {data.items.map(item => (
          <QueueRow
            key={item.lesson_id}
            item={item}
            checked={picked.includes(item.lesson_id)}
            // A row you have already ticked must stay clickable at the cap, or
            // there is no way to swap one choice for another.
            disabled={busy || (atCap && !picked.includes(item.lesson_id))}
            onToggle={() => toggle(item.lesson_id)}
          />
        ))}
      </ul>
    </>
  )

  return (
    <Modal
      title="Draft proposals"
      onClose={onClose}
      footer={
        <>
          <span className="adm-subtext">
            {picked.length} of {MAX_LESSONS_PER_RUN} selected
            {atCap && ' — the most one run can do'}
          </span>
          <div className="adm-modal-actions">
            <button type="button" className="adm-btn adm-btn-ghost" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button
              type="button"
              className="adm-btn adm-btn-primary"
              disabled={busy || picked.length === 0}
              onClick={() => onDraft(picked)}
            >
              {busy ? 'Drafting…' : `Draft ${picked.length || ''}`.trim()}
            </button>
          </div>
        </>
      }
    >
      {body}
    </Modal>
  )
}

interface QueueRowProps {
  item: ImprovementQueueItem
  checked: boolean
  disabled: boolean
  onToggle: () => void
}

/** One pickable lesson. Carries the same Track/Module chips as a proposal row so
 * the picker and the review queue read as one screen. */
function QueueRow({ item, checked, disabled, onToggle }: QueueRowProps) {
  const dotColor = resolveTrackColor({ required_level: item.track_level, is_introduction: false })

  return (
    <li className={`adm-ci-pickrow${disabled && !checked ? ' adm-ci-pickrow-off' : ''}`}>
      <label className="adm-ci-picklabel">
        <input type="checkbox" checked={checked} disabled={disabled} onChange={onToggle} />
        <span className="adm-ci-pickmain">
          <strong>{item.lesson_title}</strong>
          <span className="adm-ci-loc">
            <span className="adm-loc-chip">
              <span className="adm-loc-dot" style={{ background: dotColor }} />
              {item.track_name}
            </span>
            <span className="adm-loc-chip">{item.module_title}</span>
            <span className="adm-loc-chip">
              {item.feedback_count} feedback item{item.feedback_count === 1 ? '' : 's'}
            </span>
          </span>
        </span>
      </label>
    </li>
  )
}
