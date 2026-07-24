import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

export interface Scope {
  /** null = "All projects"; otherwise the scoped project's id. */
  projectId: string | null
  setProject: (id: string | null) => void
}

/** Reads/writes the `?project=` query param so the admin's project scope
 * persists across sidebar navigation (NavLinks carry the current search
 * string — see AdminShell) and survives reload/deep-link/back-button, all
 * for free via the URL. */
export function useScope(): Scope {
  const [searchParams, setSearchParams] = useSearchParams()

  const setProject = useCallback((id: string | null) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      if (id) next.set('project', id)
      else next.delete('project')
      return next
    })
  }, [setSearchParams])

  return useMemo(() => ({ projectId: searchParams.get('project'), setProject }), [searchParams, setProject])
}
