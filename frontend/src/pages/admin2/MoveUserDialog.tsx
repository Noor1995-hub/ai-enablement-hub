import { useState } from 'react'
import { useCompanies, useMoveUser } from './api'
import { Modal, Spinner } from './kit'

interface Props {
  userId: string
  currentProjectId: string | null
  /** Projects the user administers: moving into one of them drops that grant. */
  holdsGrantOn: string[]
  onClose: () => void
}

/** Move a user to another project (B6 / #111). Assignments, progress,
 * assessment and interview stay; the new project's settings apply. */
export default function MoveUserDialog({ userId, currentProjectId, holdsGrantOn, onClose }: Props) {
  const companies = useCompanies()
  const move = useMoveUser()
  const [target, setTarget] = useState('')
  const options = (companies.data ?? []).flatMap(c =>
    c.projects.filter(p => p.id !== currentProjectId).map(p => ({ id: p.id, label: `${c.name} · ${p.name}` })),
  )

  return (
    <Modal
      title="Move to another project"
      onClose={onClose}
      footer={
        <>
          <button
            type="button"
            className="adm-btn adm-btn-red"
            disabled={!target || move.isPending}
            onClick={() => move.mutate({ userId, projectId: target }, { onSuccess: onClose })}
          >
            {move.isPending && <Spinner size="sm" />}
            Move
          </button>
          <button type="button" className="adm-btn adm-btn-subtle adm-push-right" disabled={move.isPending} onClick={onClose}>
            Cancel
          </button>
        </>
      }
    >
      <div className="adm-field">
        <label className="adm-field-label" htmlFor="move-target">New project</label>
        <select id="move-target" className="adm-field-input" value={target} onChange={e => setTarget(e.target.value)}>
          <option value="">Choose a project…</option>
          {options.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
        </select>
      </div>
      <p className="adm-hint">
        Their assignments, progress, assessment and interview stay. The new project's locks, AI settings and
        email templates apply from now on.
      </p>
      {target && holdsGrantOn.includes(target) && (
        <div className="adm-note-banner" role="note">
          This person administers this project; that grant is removed, because staff aren't learners of the
          project they run.
        </div>
      )}
      {move.error && <p className="adm-form-msg adm-form-msg-err" role="alert">{move.error.message}</p>}
    </Modal>
  )
}
