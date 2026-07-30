import { useState } from 'react'
import { resolveTrackColor } from '../../lib/trackColors'
import type { ImprovementQueueItem } from '../../types/domain'
import { MAX_LESSONS_PER_RUN, useImprovementQueue } from './api'
import { EmptyState, ErrorState, Spinner } from './kit'

interface DraftQueuePickerProps {
  /** Fired with the picked lesson ids. The caller owns the mutation so its
   * result can outlive this panel, which closes as soon as the run starts. */
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
 * An INLINE panel, not a modal: the queue is as long as the catalogue has
 * un-drafted feedback, and a dialog sized to that covered the whole screen
 * (and the proposal list the admin is picking against). The list scrolls inside
 * a fixed-height box instead, so the panel's height is constant no matter how
 * long the queue is.
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
    // Only the LIST scrolls — the header and the actions stay put, so the
    // Draft button never scrolls out of reach on a long queue. adm-check-list
    // is the shared scroll box (see the assign-content picker on PeoplePage).
    <ul className="adm-check-list adm-ci-picklist">
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
  )

  return (
    <div className="adm-ci-pickpanel">
      <div className="adm-ci-pickhead">
        <strong>Pick the lessons to redraft</strong>
        <span className="adm-subtext">
          {picked.length} of {MAX_LESSONS_PER_RUN} selected
          {atCap && ' — the most one run can do'}
        </span>
      </div>

      {body}

      <div className="adm-ci-pickfoot">
        <span className="adm-subtext">
          Each one is a full rewrite using every accepted feedback item on that lesson. Nothing
          reaches a learner until you approve the draft.
        </span>
        <div className="adm-ci-pickactions">
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm"
            onClick={onClose}
            disabled={busy}
          >
            Cancel
          </button>
          <button
            type="button"
            className="adm-btn adm-btn-primary adm-btn-sm"
            disabled={busy || picked.length === 0}
            onClick={() => onDraft(picked)}
          >
            {busy ? 'Drafting…' : `Draft ${picked.length || ''}`.trim()}
          </button>
        </div>
      </div>
    </div>
  )
}

interface QueueRowProps {
  item: ImprovementQueueItem
  checked: boolean
  disabled: boolean
  onToggle: () => void
}

/** One pickable lesson: title, then track / module / feedback count on a single
 * line. Everything the proposal cards show is kept — the line is allowed to
 * truncate rather than wrap, so every row is the same height and the scroll box
 * holds a predictable number of them. */
function QueueRow({ item, checked, disabled, onToggle }: QueueRowProps) {
  const dotColor = resolveTrackColor({ required_level: item.track_level, is_introduction: false })

  return (
    <li className={disabled && !checked ? 'adm-ci-pickrow-off' : undefined}>
      <label className="adm-check-row">
        <input type="checkbox" checked={checked} disabled={disabled} onChange={onToggle} />
        <span className="adm-ci-pickmain">
          <span className="adm-ci-picktitle">{item.lesson_title}</span>
          <span className="adm-ci-pickmeta">
            <span className="adm-loc-dot" style={{ background: dotColor }} />
            {item.track_name}
            <span className="adm-ci-picksep">·</span>
            {item.module_title}
            <span className="adm-ci-picksep">·</span>
            {item.feedback_count} feedback item{item.feedback_count === 1 ? '' : 's'}
          </span>
        </span>
      </label>
    </li>
  )
}
