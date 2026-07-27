import { useMemo } from 'react'
import EmailTemplatesCard from '../admin/EmailTemplatesCard'
import { useCompanies } from './api'
import { Card, ErrorState, Spinner } from './kit'
import { useScope } from './useScope'

/** Email templates screen (spec §3.6, `/admin/templates`) — requires a
 * project scope, same as Assignments: unscoped shows a company/project
 * picker. The picker JSX below is deliberately duplicated from
 * AssignmentsPage.tsx (Task 17, already reviewed/committed) rather than
 * extracted into a shared component — it's a small, self-contained block
 * and this task's scope is the three new screens, not refactoring a sibling
 * page; it reuses the exact same `.adm-proj-grid`/`.adm-proj-card` classes
 * so there is nothing new to style.
 *
 * Scoped, this renders the existing `EmailTemplatesCard`
 * (frontend/src/pages/admin/EmailTemplatesCard.tsx) UNCHANGED — it owns its
 * own data fetching (GET/PUT/DELETE/preview against
 * `admin_email_templates`). The wrapping kit `<Card>` plus the
 * `.adm-templates-page` CSS overrides in admin.css only neutralize its own
 * outer chrome (background/border/radius/margin) so the two cards don't
 * nest visibly; every field, tab, button and preview frame inside stays
 * exactly as EmailTemplatesCard renders it (token-level restyle only, per
 * the task brief — the component itself is not edited). */
export default function TemplatesPage() {
  const scope = useScope()
  const companiesQuery = useCompanies()

  const scopedProject = useMemo(
    () =>
      companiesQuery.data
        ?.flatMap(company => company.projects.map(project => ({ id: project.id, label: `${company.name} · ${project.name}` })))
        .find(project => project.id === scope.projectId),
    [companiesQuery.data, scope.projectId],
  )

  // ── Unscoped: company/project picker ───────────────────────────────────────
  if (scope.projectId === null) {
    return (
      <div>
        <h1 className="adm-page-title">Email templates</h1>
        <p className="adm-page-sub">Pick a project — invite and reset emails are customized per project.</p>
        {companiesQuery.isLoading ? (
          <div className="adm-loading">
            <Spinner />
          </div>
        ) : companiesQuery.isError || !companiesQuery.data ? (
          <ErrorState
            message={companiesQuery.error?.message ?? 'Failed to load projects.'}
            onRetry={() => void companiesQuery.refetch()}
          />
        ) : (
          <div className="adm-proj-grid">
            {companiesQuery.data.flatMap(company =>
              company.projects.map(project => (
                <button
                  key={project.id}
                  type="button"
                  className="adm-proj-card"
                  onClick={() => scope.setProject(project.id)}
                >
                  <div className="adm-proj-card-company">{company.name}</div>
                  <h3 className="adm-proj-card-name">{project.name}</h3>
                  <div className="adm-proj-card-foot">
                    <span className="adm-proj-card-open">
                      Edit templates <ChevronIcon />
                    </span>
                  </div>
                </button>
              )),
            )}
          </div>
        )}
      </div>
    )
  }

  // ── Scoped: the existing template editor ────────────────────────────────────
  return (
    <div className="adm-templates-page">
      <div className="adm-page-head">
        <div>
          <h1 className="adm-page-title">Email templates</h1>
          <p className="adm-page-sub">{scopedProject?.label ?? 'this project'}</p>
        </div>
      </div>

      <Card>
        <EmailTemplatesCard projectId={scope.projectId} />
      </Card>
    </div>
  )
}

function ChevronIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}
