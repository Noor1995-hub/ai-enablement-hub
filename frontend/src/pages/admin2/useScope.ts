import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

export interface Scope {
  /** null = "All projects"; otherwise the scoped project's id. */
  projectId: string | null
  /** `replace` swaps the current history entry instead of pushing one — for
   * automatic corrections the back button must not undo. */
  setProject: (id: string | null, options?: { replace?: boolean }) => void
}

/** Reads/writes the `?project=` query param so the admin's project scope
 * persists across sidebar navigation (NavLinks carry the current search
 * string — see AdminShell) and survives reload/deep-link/back-button, all
 * for free via the URL. */
export function useScope(): Scope {
  const [searchParams, setSearchParams] = useSearchParams()
  // useSearchParams rebuilds its URLSearchParams instance on every render tied
  // to the location (even when ?project= itself hasn't changed), so memoizing
  // on searchParams itself would defeat the memo. Derive the one value we
  // actually care about first and memoize on that instead — the returned
  // object is then referentially stable across navigations that don't touch
  // the project scope.
  const projectId = searchParams.get('project')

  const setProject = useCallback((id: string | null, options?: { replace?: boolean }) => {
    setSearchParams(
      prev => {
        const next = new URLSearchParams(prev)
        if (id) next.set('project', id)
        else next.delete('project')
        return next
      },
      { replace: options?.replace ?? false },
    )
  }, [setSearchParams])

  return useMemo(() => ({ projectId, setProject }), [projectId, setProject])
}
