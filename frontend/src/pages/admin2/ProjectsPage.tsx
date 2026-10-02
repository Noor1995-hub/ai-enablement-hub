import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import type { ComponentKey } from '../../lib/constants'
import type { ComponentState } from '../../types/domain'
import type { AiSurfaceKind } from './api'
import { useAiSettings, useComponents, useCompanies, useToggleAiSetting, useToggleComponent } from './api'
import { Card, EmptyState, ErrorState, Spinner, COMPONENT_KEYS, COMPONENT_LABELS } from './kit'
import ProjectAdminsSection from './ProjectAdminsSection'
import { useScope } from './useScope'

/** AI surfaces that get their own row below the component list. `assessment` and
 * `interview` are not here — each rides as a third toggle on its own component row
 * (Assessment / Interview), since both are also journey components. */
const AI_ROWS: { kind: AiSurfaceKind; label: string }[] = [
  { kind: 'chatbot', label: 'Chatbot' },
  { kind: 'lesson', label: 'Lesson helper' },
]

/** Projects screen (spec §3.6, `/admin/projects`) — one card per project,
 * company-first title (`Company · Project`), with the component-access
 * toggles ported from the old panel's project detail view (since removed;
 * same visible/unlocked semantics, same `PUT …/components/{component}` call)
 * plus three buttons that jump to People / Assignments / Email templates
 * pre-scoped to that project (`?project={id}`, same convention as
 * PeoplePage's row-click navigation). Prototype:
 * docs/design-prototypes/admin-redesign option-b.html `projects()` +
 * common.js `componentsHTML()`.
 *
 * Respects the top-level scope switcher (spec §3.6 parity with the other
 * screens): with `?project=` set, only that project (and its parent company)
 * renders; with no scope ("all projects"), every company/project renders,
 * same as before this filter existed. */
export default function ProjectsPage() {
  const companiesQuery = useCompanies()
  const navigate = useNavigate()
  const scope = useScope()
  const { isPowerAdmin } = useAuth()

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

  const rows = companiesQuery.data
    .flatMap(company => company.projects.map(project => ({ company, project })))
    .filter(({ project }) => scope.projectId === null || project.id === scope.projectId)

  function goTo(path: string, projectId: string) {
    navigate({ pathname: path, search: `?project=${projectId}` })
  }

  return (
    <div>
      <h1 className="adm-page-title">Projects</h1>
      <p className="adm-page-sub">
        {isPowerAdmin
          ? 'Project settings live here — day-to-day work happens in People, Assignments and Feedback with the project filter.'
          : 'Settings for your project: what learners can see and open, and who runs it. Day-to-day work happens in People and Assignments.'}
      </p>

      {rows.length === 0 ? (
        <EmptyState
          title="No projects yet"
          hint={isPowerAdmin ? 'Create one from Setup.' : 'Ask a power admin to make you an admin of a project.'}
        />
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
            <ProjectSettingsToggles projectId={project.id} showUnreleasedAi={isPowerAdmin} />
            <ProjectAdminsSection projectId={project.id} canEdit={isPowerAdmin} />
          </Card>
        ))
      )}
    </div>
  )
}

/** One project card's settings — component access AND AI surfaces. With N projects,
 * hooks can't run in a loop at the page level, so each card owns its own
 * queries/mutations via this child component (the established per-row-owns-its-query
 * pattern; c.f. Matrix.tsx at a different grain). The `assessment` and `interview` AI
 * surfaces each ride as a third toggle on their own component row; `chatbot`/`lesson`
 * get their own rows (AI_ROWS). */
/** `showUnreleasedAi`: the Chatbot and Lesson helper switches only change the
 * admin-only /dev-chat page today (no learner screen mounts them), so project
 * admins don't see them. */
function ProjectSettingsToggles({ projectId, showUnreleasedAi }: { projectId: string; showUnreleasedAi: boolean }) {
  const componentsQuery = useComponents(projectId)
  const aiQuery = useAiSettings(projectId)
  const toggleComponent = useToggleComponent()
  const toggleAiSetting = useToggleAiSetting()
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

  async function handleToggleAi(kind: AiSurfaceKind, currentEnabled: boolean) {
    setBusyKey(`ai-${kind}`)
    try {
      await toggleAiSetting.mutateAsync({ projectId, kind, enabled: !currentEnabled })
    } catch {
      // surfaced below via toggleAiSetting.isError
    }
    setBusyKey(null)
  }

  if (componentsQuery.isLoading || aiQuery.isLoading) {
    return (
      <div className="adm-loading">
        <Spinner size="sm" />
      </div>
    )
  }

  if (componentsQuery.isError || !componentsQuery.data || aiQuery.isError || !aiQuery.data) {
    return (
      <ErrorState
        message={
          componentsQuery.error?.message ?? aiQuery.error?.message ?? 'Failed to load project settings.'
        }
        onRetry={() => {
          void componentsQuery.refetch()
          void aiQuery.refetch()
        }}
      />
    )
  }

  const data = componentsQuery.data
  const aiData = aiQuery.data

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
            {(comp === 'assessment' || comp === 'interview') && (
              <label className="adm-switch-label">
                <button
                  type="button"
                  className={`adm-switch${aiData[comp]?.enabled ? ' on' : ''}`}
                  disabled={busyKey === `ai-${comp}`}
                  aria-pressed={aiData[comp]?.enabled ?? false}
                  aria-label={`${COMPONENT_LABELS[comp]} AI enabled`}
                  onClick={() => void handleToggleAi(comp, aiData[comp]?.enabled ?? false)}
                />
                AI enabled
              </label>
            )}
            <span className="adm-subtext adm-push-right">
              {current.hidden ? 'Hidden from journey page' : current.locked ? 'Shown as locked tile' : 'Fully available'}
            </span>
          </div>
        )
      })}
      {(showUnreleasedAi ? AI_ROWS : []).map(({ kind, label }) => {
        const enabled = aiData[kind]?.enabled ?? false
        return (
          <div className="adm-comp-row" key={kind}>
            <span className="adm-comp-name">{label}</span>
            <label className="adm-switch-label">
              <button
                type="button"
                className={`adm-switch${enabled ? ' on' : ''}`}
                disabled={busyKey === `ai-${kind}`}
                aria-pressed={enabled}
                aria-label={`${label} enabled for learners`}
                onClick={() => void handleToggleAi(kind, enabled)}
              />
              enabled
            </label>
            <span className="adm-subtext adm-push-right">
              {enabled ? 'Enabled for learners' : 'Off — hidden from learners'}
            </span>
          </div>
        )
      })}
      {toggleComponent.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {toggleComponent.error instanceof Error ? toggleComponent.error.message : 'Failed to update component access.'}
        </p>
      )}
      {toggleAiSetting.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {toggleAiSetting.error instanceof Error
            ? toggleAiSetting.error.message
            : 'Failed to update the AI assistant setting.'}
        </p>
      )}
    </div>
  )
}
