import { useEffect, useMemo, useState } from 'react'
import { useCompanies, useDefaults, useLearning, useTracks } from './api'
import ContentTree from './ContentTree'
import Matrix from './Matrix'
import { Card, ErrorState, Spinner } from './kit'
import { useScope } from './useScope'

/** Scope tree / matrix column level. Held by the page; the tree and the
 * breadcrumb both mirror it. */
export type Level =
  | { level: 'tracks' }
  | { level: 'modules'; trackId: string }
  | { level: 'lessons'; trackId: string; moduleId: string }

/** Assignments matrix screen (spec §3.4, `/admin/assignments`) — the headline
 * redesign. Unscoped shows a company/project picker; scoped shows the content
 * scope tree + users×content matrix with a project-defaults row. Prototype:
 * docs/design-prototypes/admin-redesign option-b.html `assignments()` +
 * common.js `mountMatrix()`. */
export default function AssignmentsPage() {
  const scope = useScope()
  const projectId = scope.projectId

  // All hooks run every render (never behind the unscoped early-return) so hook
  // order stays stable when the scope flips between null and a project.
  const [level, setLevel] = useState<Level>({ level: 'tracks' })
  const companiesQuery = useCompanies()
  const tracksQuery = useTracks()
  const learningQuery = useLearning(projectId)
  const defaultsQuery = useDefaults(projectId)

  // A scope change resets the drill-down (the old track/module ids belong to a
  // different project's context — start back at the top).
  useEffect(() => setLevel({ level: 'tracks' }), [projectId])

  const assignableTracks = useMemo(
    () => [...(tracksQuery.data ?? [])].filter(t => !t.is_introduction).sort((a, b) => a.sort_order - b.sort_order),
    [tracksQuery.data],
  )
  // Depend on the slices, not `learningQuery.data`: the optimistic toggle patch rebuilds
  // the top-level object (only `users` changes) while structural sharing keeps
  // `.modules`/`.lessons` stable, so a cell click must not re-sort them and invalidate
  // Matrix's memoized index, columns and rows.
  const learningModules = learningQuery.data?.modules
  const learningLessons = learningQuery.data?.lessons
  const sortedModules = useMemo(
    () => [...(learningModules ?? [])].sort((a, b) => a.sort_order - b.sort_order),
    [learningModules],
  )
  const sortedLessons = useMemo(
    () => [...(learningLessons ?? [])].sort((a, b) => a.sort_order - b.sort_order),
    [learningLessons],
  )

  const scopedProject = useMemo(
    () =>
      companiesQuery.data
        ?.flatMap(company => company.projects.map(project => ({ id: project.id, label: `${company.name} · ${project.name}` })))
        .find(project => project.id === projectId),
    [companiesQuery.data, projectId],
  )

  // ── Unscoped: company/project picker ───────────────────────────────────────
  if (projectId === null) {
    return (
      <div>
        <h1 className="adm-page-title">Assignments</h1>
        <p className="adm-page-sub">Pick a project — assignments are managed per project.</p>
        {companiesQuery.isLoading ? (
          <div className="adm-loading">
            <Spinner />
          </div>
        ) : companiesQuery.error || !companiesQuery.data ? (
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
                      Manage <ChevronIcon />
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

  // ── Scoped: content tree + matrix ──────────────────────────────────────────
  const isLoading = tracksQuery.isLoading || learningQuery.isLoading || defaultsQuery.isLoading
  const error = tracksQuery.error ?? learningQuery.error ?? defaultsQuery.error

  if (isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (error || !learningQuery.data || !defaultsQuery.data) {
    return (
      <ErrorState
        message={error?.message ?? 'Failed to load assignments.'}
        onRetry={() => {
          void tracksQuery.refetch()
          void learningQuery.refetch()
          void defaultsQuery.refetch()
        }}
      />
    )
  }

  return (
    <div>
      <div className="adm-page-head">
        <div>
          <h1 className="adm-page-title">Assignments</h1>
          <p className="adm-page-sub">{scopedProject?.label ?? 'this project'}</p>
        </div>
      </div>

      <div className="adm-note-banner">
        Top row sets <b>project defaults</b> — what every new participant gets automatically. Cells below
        override per person. Use the content scope tree on the left to switch between track, module and lesson
        level.
      </div>

      <Card className="adm-matrix-card">
        <div className="adm-assign-layout">
          <ContentTree tracks={assignableTracks} modules={sortedModules} level={level} onSelect={setLevel} />
          <Matrix
            key={projectId}
            projectId={projectId}
            level={level}
            onSelect={setLevel}
            tracks={assignableTracks}
            modules={sortedModules}
            lessons={sortedLessons}
            users={learningQuery.data.users}
            defaultTrackIds={defaultsQuery.data.track_ids}
          />
        </div>
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
