import { useAuth } from '../../contexts/AuthContext'
import { useCompanies } from './api'
import { useScope } from './useScope'

interface ProjectOption {
  id: string
  label: string // "Company · Project", matching the prototype's orgFull()
}

/** The scope switcher is the navigation anchor of the new admin shell: pick a
 * project once (or clear back to "All projects") and every section that
 * reads useScope() follows — see docs/design-prototypes/admin-redesign
 * option-b.html's scope-switch. Lives in the topbar, goes red-tinted when
 * scoped so it's never ambiguous what's being viewed. */
export default function ScopeSwitcher() {
  const { projectId, setProject } = useScope()
  // Project admins only ever get their own projects back from /companies, and
  // have no "All projects" view (AdminShell pins them to one).
  const { isPowerAdmin } = useAuth()
  const { data: companies, isLoading, error } = useCompanies()
  const options: ProjectOption[] | undefined = companies?.flatMap(company =>
    company.projects.map(project => ({ id: project.id, label: `${company.name} · ${project.name}` })),
  )

  const scoped = projectId !== null
  const selectValue = projectId ?? 'all'
  // A deep-linked/reloaded ?project= id has nowhere to match until the
  // options load (or if the load fails outright) — without a stand-in
  // <option>, the browser just renders the <select> blank/deselected even
  // though the pill is styled as scoped. Render one so the value always
  // has somewhere to land.
  const matched = scoped ? options?.some(o => o.id === projectId) : true
  const syntheticLabel = isLoading ? 'Loading project…' : error ? 'Project (details unavailable)' : projectId

  return (
    <div className="adm-scope-switch">
      <span className="adm-scope-viewing">Viewing</span>
      <span className={`adm-scope-pill${scoped ? ' scoped' : ''}`}>
        <FolderIcon />
        <select
          className="adm-scope-select"
          value={selectValue}
          disabled={isLoading}
          onChange={e => setProject(e.target.value === 'all' ? null : e.target.value)}
        >
          {isPowerAdmin && <option value="all">All projects</option>}
          {scoped && !matched && <option value={projectId ?? ''}>{syntheticLabel}</option>}
          {options?.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
        </select>
        {scoped && isPowerAdmin && (
          <button
            type="button"
            className="adm-scope-clear"
            title="Back to all projects"
            onClick={() => setProject(null)}
          >
            ✕
          </button>
        )}
      </span>
      {error && <span className="adm-scope-error" title={error.message}>Couldn't load projects</span>}
    </div>
  )
}

function FolderIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  )
}
