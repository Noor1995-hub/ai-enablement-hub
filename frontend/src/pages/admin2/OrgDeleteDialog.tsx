import { impactSentence } from '../../lib/orgImpact'
import { type OrgKind, useDeleteOrg, useOrgImpact } from './api'
import { ConfirmButton, ErrorState, Modal, Spinner } from './kit'

interface Props {
  kind: OrgKind
  id: string
  name: string
  onClose: () => void
  onDeleted: () => void
}

/** Delete a project or a company (B6): the impact first, then a two-step
 * confirm. Its users are deleted with it; power admins keep their accounts. */
export default function OrgDeleteDialog({ kind, id, name, onClose, onDeleted }: Props) {
  const impact = useOrgImpact(kind, id)
  const remove = useDeleteOrg()

  return (
    <Modal title={`Delete ${kind}`} onClose={onClose}>
      {impact.isFetching ? (
        <div className="adm-loading"><Spinner /></div>
      ) : impact.error || !impact.data ? (
        <ErrorState message={impact.error?.message ?? 'Failed to load what this deletes.'} onRetry={() => void impact.refetch()} />
      ) : (
        <>
          <p className="adm-form-msg adm-form-msg-err">{impactSentence(kind, name, impact.data)}</p>
          <p className="adm-hint">This can't be undone; only the nightly backup can bring it back.</p>
          <ConfirmButton
            label={`Delete ${kind}`}
            confirmLabel="Yes, delete"
            busy={remove.isPending}
            onConfirm={() => remove.mutate({ kind, id }, { onSuccess: onDeleted })}
          />
          {remove.error && <p className="adm-form-msg adm-form-msg-err" role="alert">{remove.error.message}</p>}
        </>
      )}
    </Modal>
  )
}
