import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ComponentKey } from '../../lib/constants'
import type { ComponentState } from '../../types/domain'
import { COMPONENT_KEYS, COMPONENT_LABELS } from '../admin/adminStyles'
import { useComponents, useCompanies, useToggleComponent } from './api'
import { Card, EmptyState, ErrorState, Spinner } from './kit'

/** Projects screen (spec §3.6, `/admin/projects`) — one card per project,
 * company-first title (`Company · Project`), with the component-access
 * toggles ported from the old panel's ProjectDetailView
 * (frontend/src/pages/admin/ProjectDetailView.tsx ~440-470: same
 * visible/unlocked semantics, same `PUT …/components/{component}` call)
 * plus three buttons that jump to People / Assignments / Email templates
 * pre-scoped to that project (`?project={id}`, same convention as
 * PeoplePage's row-click navigation). Prototype:
 * docs/design-prototypes/admin-redesign option-b.html `projects()` +
 * common.js `componentsHTML()`. */
export default function ProjectsPage() {
  const companiesQuery = useCompanies()
  const navigate = useNavigate()

  if (companiesQuery.isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (companiesQuery.isError || !companiesQuery.data) {
    return (
      <ErrorState
        message={companiesQuery.error?.message ?? 'Failed to load projects.'}
        onRetry={() => void companiesQuery.refetch()}
      />
    )
  }

  const rows = companiesQuery.data.flatMap(company => company.projects.map(project => ({ company, project })))

  function goTo(path: string, projectId: string) {
    navigate({ pathname: path, search: `?project=${projectId}` })
  }

  return (
    <div>
      <h1 className="adm-page-title">Projects</h1>
      <p className="adm-page-sub">
        Project settings live here — day-to-day work happens in People, Assignments and Feedback with the project
        filter.
      </p>

      {rows.length === 0 ? (
        <EmptyState title="No projects yet" hint="Create one from Setup." />
      ) : (
        rows.map(({ company, project }) => (
          <Card
            key={project.id}
            title={`${company.name} · ${project.name}`}
            actions={
              <>
                <button
                  type="button"
                  className="adm-btn adm-btn-ghost adm-btn-sm"
                  onClick={() => goTo('/admin/people', project.id)}
                >
                  People
                </button>
                <button
                  type="button"
                  className="adm-btn adm-btn-ghost adm-btn-sm"
                  onClick={() => goTo('/admin/assignments', project.id)}
                >
                  Assignments
                </button>
                <button
                  type="button"
                  className="adm-btn adm-btn-ghost adm-btn-sm"
                  onClick={() => goTo('/admin/templates', project.id)}
                >
                  Email templates
                </button>
              </>
            }
          >
            <ProjectComponentToggles projectId={project.id} />
          </Card>
        ))
      )}
    </div>
  )
}

/** One `useComponents`/`useToggleComponent` pair per project card — with N
 * projects, hooks can't run in a loop at the page level, so each card owns
 * its own query/mutation via this child component (the established
 * per-row-owns-its-query pattern; c.f. Matrix.tsx at a different grain). */
function ProjectComponentToggles({ projectId }: { projectId: string }) {
  const componentsQuery = useComponents(projectId)
  const toggleComponent = useToggleComponent()
  const [busyKey, setBusyKey] = useState<string | null>(null)

  async function handleToggle(comp: ComponentKey, current: ComponentState, field: 'hidden' | 'locked') {
    const key = `${comp}-${field}`
    setBusyKey(key)
    try {
      await toggleComponent.mutateAsync({
        projectId,
        component: comp,
        hidden: field === 'hidden' ? !current.hidden : current.hidden,
        locked: field === 'locked' ? !current.locked : current.locked,
      })
    } catch {
      // surfaced below via toggleComponent.isError
    }
    setBusyKey(null)
  }

  if (componentsQuery.isLoading) {
    return (
      <div className="adm-loading">
        <Spinner size="sm" />
      </div>
    )
  }

  if (componentsQuery.isError || !componentsQuery.data) {
    return (
      <ErrorState
        message={componentsQuery.error?.message ?? 'Failed to load component access.'}
        onRetry={() => void componentsQuery.refetch()}
      />
    )
  }

  const data = componentsQuery.data

  return (
    <div className="adm-comp-list">
      {COMPONENT_KEYS.map(comp => {
        const current = data[comp] ?? { hidden: false, locked: false }
        const visible = !current.hidden
        const unlocked = !current.locked
        const busy = busyKey === `${comp}-hidden` || busyKey === `${comp}-locked`
        return (
          <div className="adm-comp-row" key={comp}>
            <span className="adm-comp-name">{COMPONENT_LABELS[comp]}</span>
            <label className="adm-switch-label">
              <button
                type="button"
                className={`adm-switch${visible ? ' on' : ''}`}
                disabled={busy}
                aria-pressed={visible}
                aria-label={`${COMPONENT_LABELS[comp]} visible to learners`}
                onClick={() => void handleToggle(comp, current, 'hidden')}
              />
              visible to learners
            </label>
            <label className="adm-switch-label">
              <button
                type="button"
                className={`adm-switch${unlocked ? ' on' : ''}`}
                disabled={busy}
                aria-pressed={unlocked}
                aria-label={`${COMPONENT_LABELS[comp]} unlocked`}
                onClick={() => void handleToggle(comp, current, 'locked')}
              />
              unlocked
            </label>
            <span className="adm-subtext adm-push-right">
              {current.hidden ? 'Hidden from journey page' : current.locked ? 'Shown as locked tile' : 'Fully available'}
            </span>
          </div>
        )
      })}
      {toggleComponent.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {toggleComponent.error instanceof Error ? toggleComponent.error.message : 'Failed to update component access.'}
        </p>
      )}
    </div>
  )
}
