import { useEffect, useState } from 'react'
import { useAdminUsers, useGrantProjectAdmin, useProjectAdmins, useRevokeProjectAdmin } from './api'
import { ConfirmButton, ErrorState, Spinner } from './kit'

/** "Admins" block on a project card (spec 2026-10-01-project-scoped-admin, #144).
 * Everyone who can see the card sees who runs the project; only power admins
 * can add (any user, also people outside the project) or remove one. */
export default function ProjectAdminsSection({ projectId, canEdit }: { projectId: string; canEdit: boolean }) {
  const admins = useProjectAdmins(projectId)
  const revoke = useRevokeProjectAdmin()
  const [adding, setAdding] = useState(false)

  return (
    <div className="adm-modal-section">
      <div className="adm-acct-row">
        <span className="adm-acct-label">Admins</span>
        {admins.isLoading && <Spinner size="sm" />}
        {admins.data?.length === 0 && <span className="adm-subtext">No project admins yet</span>}
        {canEdit && !adding && (
          <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm adm-push-right" onClick={() => setAdding(true)}>
            Add admin
          </button>
        )}
      </div>
      {admins.isError && (
        <ErrorState message={admins.error.message} onRetry={() => void admins.refetch()} />
      )}
      {admins.data?.map(admin => (
        <div className="adm-acct-row" key={admin.user_id}>
          <span>
            {admin.first_name} {admin.last_name}
          </span>
          <span className="adm-subtext">{admin.email}</span>
          {canEdit && (
            <span className="adm-push-right">
              <ConfirmButton
                label="Remove"
                confirmLabel="Confirm remove"
                busy={revoke.isPending && revoke.variables?.userId === admin.user_id}
                onConfirm={() => revoke.mutate({ projectId, userId: admin.user_id })}
              />
            </span>
          )}
        </div>
      ))}
      {revoke.isError && <p className="adm-form-msg adm-form-msg-err">{revoke.error.message}</p>}
      {canEdit && adding && (
        <AddAdmin
          projectId={projectId}
          existing={new Set(admins.data?.map(a => a.user_id))}
          onDone={() => setAdding(false)}
        />
      )}
    </div>
  )
}

function AddAdmin({ projectId, existing, onDone }: { projectId: string; existing: Set<string>; onDone: () => void }) {
  const [q, setQ] = useState('')
  // Debounced like the People search: each call enriches the whole directory.
  const [debounced, setDebounced] = useState('')
  useEffect(() => {
    const id = setTimeout(() => setDebounced(q.trim()), 300)
    return () => clearTimeout(id)
  }, [q])
  const trimmed = debounced
  return (
    <div className="adm-field">
      <label className="adm-field-label" htmlFor={`add-admin-${projectId}`}>
        Find a person by name or email
      </label>
      <div className="adm-acct-row">
        <input
          id={`add-admin-${projectId}`}
          className="adm-field-input"
          placeholder="Name or email…"
          value={q}
          autoFocus
          onChange={e => setQ(e.target.value)}
        />
        <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" onClick={onDone}>
          Cancel
        </button>
      </div>
      {trimmed.length >= 2 && (
        <AdminCandidates projectId={projectId} q={trimmed} existing={existing} onDone={onDone} />
      )}
    </div>
  )
}

function AdminCandidates({
  projectId,
  q,
  existing,
  onDone,
}: {
  projectId: string
  q: string
  existing: Set<string>
  onDone: () => void
}) {
  // Power admins only reach this, and their GET /users with no project_id
  // searches everyone — so a delaware coach outside the project is findable.
  const users = useAdminUsers({ project: null, q, page: 1 })
  const grant = useGrantProjectAdmin()

  if (users.isLoading) return <Spinner size="sm" />
  if (users.isError) return <p className="adm-form-msg adm-form-msg-err">{users.error.message}</p>
  const found = users.data?.users ?? []
  const candidates = found.filter(u => u.role !== 'admin' && !existing.has(u.id))
  if (found.length === 0) return <p className="adm-hint">Nobody found.</p>
  if (candidates.length === 0) {
    return <p className="adm-hint">Everyone found is already an admin here, or a power admin (they manage every project).</p>
  }

  return (
    <div>
      {candidates.slice(0, 8).map(user => (
        <div className="adm-acct-row" key={user.id}>
          <span>
            {user.first_name} {user.last_name}
          </span>
          <span className="adm-subtext">
            {user.email}
            {user.project_name ? ` · ${user.project_name}` : ''}
          </span>
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm adm-push-right"
            disabled={grant.isPending}
            onClick={() => grant.mutate({ projectId, userId: user.id }, { onSuccess: onDone })}
          >
            Make admin
          </button>
        </div>
      ))}
      {grant.isError && <p className="adm-form-msg adm-form-msg-err">{grant.error.message}</p>}
    </div>
  )
}
