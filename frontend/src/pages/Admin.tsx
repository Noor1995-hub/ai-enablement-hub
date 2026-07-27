import { useState, useEffect, useCallback } from 'react'
import { client, errorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import type { ComponentKey } from '../lib/constants'
import type {
  AdminLearning,
  AdminSurvey,
  AdminUser,
  CompanyWithProjects,
  ComponentState,
  EmailStatus,
  ProjectOut,
  Track,
} from '../types/domain'
import { s } from './admin/adminStyles'
import ProjectsView from './admin/ProjectsView'
import ProjectDetailView, { type SelectedProject } from './admin/ProjectDetailView'
import SetupView from './admin/SetupView'

// God-component structure kept for parity (A1 noted, deferred). The old file's
// two hand-rolled `authH` header patterns are gone — the typed api client
// attaches the Bearer token and drives the refresh path (fixes A2).

export interface ResetLinkEntry {
  link: string
  copied: boolean
  emailStatus: EmailStatus
}

export default function Admin() {
  const { user } = useAuth()

  const [view, setView] = useState<'projects' | 'setup'>('projects')
  // null = list view, otherwise the opened project + its company name
  const [selectedProject, setSelectedProject] = useState<SelectedProject | null>(null)
  // user detail panel
  const [panelUserId, setPanelUserId] = useState<string | null>(null)
  const [panelSurvey, setPanelSurvey] = useState<AdminSurvey | null | undefined>(undefined) // undefined=not loaded, null=no survey
  const [loadingPanel, setLoadingPanel] = useState(false)

  /* ── companies & projects data ── */
  const [companiesData, setCompaniesData] = useState<CompanyWithProjects[]>([])
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [companiesError, setCompaniesError] = useState<string | null>(null)

  const loadCompanies = useCallback(async () => {
    setLoadingCompanies(true)
    setCompaniesError(null)
    try {
      const { data, error } = await client.GET('/api/admin/companies')
      if (data) setCompaniesData(data.companies)
      else setCompaniesError(errorMessage(error, 'Failed to load companies.'))
    } catch { setCompaniesError('Network error.') }
    setLoadingCompanies(false)
  }, [])

  /* ── project view data ── */
  const [projectUsers, setProjectUsers] = useState<AdminUser[]>([])
  const [loadingProjectUsers, setLoadingProjectUsers] = useState(false)
  const [projectUsersError, setProjectUsersError] = useState<string | null>(null)
  const [surveyLevels, setSurveyLevels] = useState<Record<string, string>>({}) // userId → score_level
  const [projectComponents, setProjectComponents] = useState<Record<string, ComponentState>>({})
  const [loadingComponents, setLoadingComponents] = useState(false)
  const [togglingComponent, setTogglingComponent] = useState<string | null>(null)
  const [componentError, setComponentError] = useState<string | null>(null)

  /* ── tracks ── */
  const [tracks, setTracks] = useState<Track[]>([])
  useEffect(() => {
    let cancelled = false
    client.GET('/api/tracks')
      .then(({ data }) => {
        if (!cancelled && data) setTracks([...data].sort((a, b) => a.sort_order - b.sort_order))
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  /* ── learning data (all users) ──
   * The old file also tracked loadingLearning; it was destructured but never
   * rendered anywhere (dead, same class as D3) — not ported. */
  const [learningData, setLearningData] = useState<AdminLearning>({ modules: [], lessons: [], users: [], total: 0 })
  const [togglingItem, setTogglingItem] = useState<string | null>(null)

  /* ── global errors ── */
  const [actionError, setActionError] = useState<string | null>(null)

  /* ── users table state (for project view) ── */
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [togglingRole, setTogglingRole] = useState<string | null>(null)
  const [generatingReset, setGeneratingReset] = useState<string | null>(null)
  const [resetLinks, setResetLinks] = useState<Record<string, ResetLinkEntry>>({})
  const [savingMaturity, setSavingMaturity] = useState(false)

  useEffect(() => { loadCompanies() }, [loadCompanies])

  /* ── load project users + components when a project is selected ── */
  const loadProjectData = useCallback(async (projectId: string) => {
    setLoadingProjectUsers(true)
    setLoadingComponents(true)
    setProjectUsersError(null)
    setComponentError(null)

    try {
      const [usersRes, compRes, learningRes] = await Promise.all([
        client.GET('/api/admin/users', { params: { query: { project_id: projectId } } }),
        client.GET('/api/admin/projects/{project_id}/components', { params: { path: { project_id: projectId } } }),
        client.GET('/api/admin/learning'),
      ])

      if (usersRes.data) {
        const users = usersRes.data.users
        setProjectUsers(users)
        if (users.length > 0) {
          client.GET('/api/admin/surveys', {
            params: { query: { user_ids: users.map(u => u.id).join(',') } },
          })
            .then(({ data }) => { if (data) setSurveyLevels(data.levels) })
            .catch(() => {})
        }
      } else {
        setProjectUsersError(errorMessage(usersRes.error, 'Failed to load users.'))
      }

      if (compRes.data) setProjectComponents(compRes.data.components)
      else setComponentError(errorMessage(compRes.error, 'Failed to load component settings.'))

      if (learningRes.data) setLearningData(learningRes.data)
    } catch {
      setProjectUsersError('Network error.')
    }
    setLoadingProjectUsers(false)
    setLoadingComponents(false)
  }, [])

  function openProject(project: ProjectOut, companyName: string) {
    setSelectedProject({ ...project, company_name: companyName })
    setPanelUserId(null)
    setPanelSurvey(undefined)
    setResetLinks({})
    setActionError(null)
    loadProjectData(project.id)
  }

  function closeProject() {
    setSelectedProject(null)
    setPanelUserId(null)
  }

  /* ── user detail panel ── */
  async function toggleUserPanel(panelUser: AdminUser) {
    if (panelUserId === panelUser.id) {
      setPanelUserId(null)
      return
    }
    setPanelUserId(panelUser.id)
    setPanelSurvey(undefined)
    setLoadingPanel(true)
    try {
      const { data } = await client.GET('/api/admin/surveys/{user_id}', {
        params: { path: { user_id: panelUser.id } },
      })
      setPanelSurvey(data ? data.survey : null)
    } catch { setPanelSurvey(null) }
    setLoadingPanel(false)
  }

  /* ── component toggles ── */
  async function toggleComponent(comp: ComponentKey, current: ComponentState, field: 'hidden' | 'locked') {
    if (!selectedProject) return
    const key = `${comp}-${field}`
    const next = { ...current, [field]: !current[field] }
    setTogglingComponent(key)
    setComponentError(null)
    try {
      const { error } = await client.PUT('/api/admin/projects/{project_id}/components/{component}', {
        params: { path: { project_id: selectedProject.id, component: comp } },
        body: { hidden: next.hidden, locked: next.locked },
      })
      if (error) {
        setComponentError(errorMessage(error, 'Failed to update component access.'))
      } else {
        setProjectComponents(prev => ({ ...prev, [comp]: next }))
      }
    } catch { setComponentError('Network error.') }
    setTogglingComponent(null)
  }

  /* ── track/module/lesson assignment ── */
  const LIST_FIELDS = {
    track: 'assigned_track_ids',
    module: 'assigned_module_ids',
    lesson: 'assigned_lesson_ids',
  } as const

  async function refetchLearningData() {
    const { data } = await client.GET('/api/admin/learning')
    if (data) setLearningData(data)
  }

  async function toggleLearningItem(action: 'track' | 'module' | 'lesson', userId: string, itemId: string, currentlyAssigned: boolean) {
    const key = `${action}-${userId}-${itemId}`
    setTogglingItem(key)
    const listField = LIST_FIELDS[action]
    try {
      const { error } = action === 'track'
        ? await client.PUT('/api/admin/users/{user_id}/tracks/{track_id}', {
            params: { path: { user_id: userId, track_id: itemId } },
            body: { assigned: !currentlyAssigned },
          })
        : action === 'module'
        ? await client.PUT('/api/admin/users/{user_id}/modules/{module_id}', {
            params: { path: { user_id: userId, module_id: itemId } },
            body: { assigned: !currentlyAssigned },
          })
        : await client.PUT('/api/admin/users/{user_id}/lessons/{lesson_id}', {
            params: { path: { user_id: userId, lesson_id: itemId } },
            body: { assigned: !currentlyAssigned },
          })
      if (error) {
        setActionError(errorMessage(error, `Failed to update ${action} assignment.`))
      } else if (action === 'lesson') {
        setLearningData(prev => ({
          ...prev,
          users: prev.users.map(u => {
            if (u.id !== userId) return u
            const ids = currentlyAssigned
              ? u[listField].filter(id => id !== itemId)
              : [...u[listField], itemId]
            return { ...u, [listField]: ids }
          }),
        }))
      } else {
        // Track/module toggles now cascade to modules/lessons server-side —
        // refetch rather than re-deriving the cascade client-side.
        await refetchLearningData()
      }
    } catch { setActionError('Network error.') }
    setTogglingItem(null)
  }

  /* ── "add all" / "unassign all" for tracks, modules and lessons (one bulk call) ── */
  async function bulkAssignLearningItems(kind: 'tracks' | 'modules' | 'lessons', userId: string, groupId: string, ids: string[], assigned: boolean) {
    if (ids.length === 0) return
    const key = `bulk-${kind}-${userId}-${groupId}`
    setTogglingItem(key)
    const listField = kind === 'tracks' ? LIST_FIELDS.track : kind === 'modules' ? LIST_FIELDS.module : LIST_FIELDS.lesson
    try {
      const { error } = kind === 'tracks'
        ? await client.PUT('/api/admin/users/{user_id}/tracks', {
            params: { path: { user_id: userId } },
            body: { track_ids: ids, assigned },
          })
        : kind === 'modules'
        ? await client.PUT('/api/admin/users/{user_id}/modules', {
            params: { path: { user_id: userId } },
            body: { module_ids: ids, assigned },
          })
        : await client.PUT('/api/admin/users/{user_id}/lessons', {
            params: { path: { user_id: userId } },
            body: { lesson_ids: ids, assigned },
          })
      if (error) {
        setActionError(errorMessage(error, `Failed to update ${kind} assignments.`))
      } else if (kind === 'lessons') {
        setLearningData(prev => ({
          ...prev,
          users: prev.users.map(u => {
            if (u.id !== userId) return u
            const next = assigned
              ? Array.from(new Set([...u[listField], ...ids]))
              : u[listField].filter(id => !ids.includes(id))
            return { ...u, [listField]: next }
          }),
        }))
      } else {
        // Track/module bulk toggles now cascade to modules/lessons server-side —
        // refetch rather than re-deriving the cascade client-side.
        await refetchLearningData()
      }
    } catch { setActionError('Network error.') }
    setTogglingItem(null)
  }

  /* ── role / delete / reset ── */
  // Role is picked from a dropdown (user / user+ / admin). 'user+' bypasses
  // learning-path locks like an admin but has no admin powers (backend
  // require_admin still gates on == 'admin').
  async function handleRoleChange(userId: string, newRole: string) {
    const role = newRole as 'admin' | 'user+' | 'user'
    setTogglingRole(userId)
    try {
      const { error } = await client.PATCH('/api/admin/users/{user_id}', {
        params: { path: { user_id: userId } },
        body: { role },
      })
      if (error) {
        setActionError(errorMessage(error, 'Failed to update role.'))
      } else {
        setProjectUsers(prev => prev.map(u => u.id !== userId ? u : { ...u, role }))
      }
    } catch { setActionError('Network error.') }
    setTogglingRole(null)
  }

  /* ── maturity override (modelled on handleRoleToggle) ── */
  async function handleSetMaturity(userId: string, level: string | null) {
    const prevUsers = projectUsers
    setSavingMaturity(true)
    // Optimistically reflect the pin (effective follows on the reconcile below).
    const applyOverride = (u: AdminUser): AdminUser => ({
      ...u, maturity_override: level, effective_maturity: level ?? u.effective_maturity,
    })
    setProjectUsers(prev => prev.map(u => (u.id === userId ? applyOverride(u) : u)))
    try {
      const { error } = await client.PUT('/api/admin/users/{user_id}/maturity', {
        params: { path: { user_id: userId } },
        body: { level: level as 'explore' | 'practitioner' | 'integrator' | 'multiplier' | null },
      })
      if (error) {
        setProjectUsers(prevUsers)
        setActionError(errorMessage(error, 'Failed to update maturity level.'))
      } else if (selectedProject) {
        // Reconcile effective_maturity authoritatively — completion can raise it
        // above the pin, and clearing falls back to assessment + earned progression.
        const { data } = await client.GET('/api/admin/users', {
          params: { query: { project_id: selectedProject.id } },
        })
        if (data) setProjectUsers(data.users)
      }
    } catch {
      setProjectUsers(prevUsers)
      setActionError('Network error.')
    }
    setSavingMaturity(false)
  }

  async function handleDelete(userId: string) {
    setDeleting(userId)
    setConfirmDelete(null)
    try {
      const { error } = await client.DELETE('/api/admin/users/{user_id}', {
        params: { path: { user_id: userId } },
      })
      if (error) {
        setActionError(errorMessage(error, 'Failed to delete user.'))
      } else {
        setProjectUsers(prev => prev.filter(u => u.id !== userId))
        if (panelUserId === userId) setPanelUserId(null)
      }
    } catch { setActionError('Network error.') }
    setDeleting(null)
  }

  async function handleGenerateResetLink(userId: string) {
    setGeneratingReset(userId)
    try {
      const { data, error } = await client.POST('/api/admin/users/{user_id}/reset-link', {
        params: { path: { user_id: userId } },
      })
      if (data) setResetLinks(prev => ({ ...prev, [userId]: { link: data.link, copied: false, emailStatus: data.email_status } }))
      else setActionError(errorMessage(error, 'Failed to generate reset link.'))
    } catch { setActionError('Network error.') }
    setGeneratingReset(null)
  }

  function copyResetLink(userId: string) {
    const entry = resetLinks[userId]
    if (!entry) return
    navigator.clipboard.writeText(entry.link)
    setResetLinks(prev => ({ ...prev, [userId]: { ...prev[userId], copied: true } }))
    setTimeout(() => setResetLinks(prev => ({ ...prev, [userId]: { ...prev[userId], copied: false } })), 2000)
  }

  if (!user) return null

  const panelLearningUser = learningData.users.find(u => u.id === panelUserId) ?? null

  return (
    <div style={s.page}>
      <AppNav
        backTo="/"
        leftExtra={<>
          <span style={s.navBadge}>Admin</span>
          <div style={s.navDivider} />
          <div style={s.navTabs}>
            {(['projects', 'setup'] as const).map(v => (
              <button
                key={v} type="button"
                style={{ ...s.navTab, ...(view === v ? s.navTabActive : s.navTabInactive) }}
                onClick={() => { setView(v); setSelectedProject(null); setPanelUserId(null) }}
              >
                {v === 'projects' ? 'Projects' : 'Setup'}
              </button>
            ))}
          </div>
        </>}
      />

      <main style={s.main}>
        {actionError && (
          <div style={s.errorBanner}>
            {actionError}
            <button style={s.errorBannerClose} onClick={() => setActionError(null)}>×</button>
          </div>
        )}

        {/* ── PROJECTS view ── */}
        {view === 'projects' && !selectedProject && (
          <ProjectsView
            companiesData={companiesData}
            loadingCompanies={loadingCompanies}
            companiesError={companiesError}
            onOpenProject={openProject}
          />
        )}

        {/* ── PROJECT detail view ── */}
        {view === 'projects' && selectedProject && (
          <ProjectDetailView
            project={selectedProject}
            participants={{
              users: projectUsers,
              loading: loadingProjectUsers,
              error: projectUsersError,
              surveyLevels,
              togglingRole,
              generatingReset,
              resetLinks,
              confirmDelete,
              deleting,
            }}
            componentAccess={{
              data: projectComponents,
              loading: loadingComponents,
              error: componentError,
              toggling: togglingComponent,
            }}
            panel={{
              expandedUserId: panelUserId,
              survey: panelSurvey,
              loading: loadingPanel,
              learningUser: panelLearningUser,
              tracks,
              learningData,
              togglingItem,
              savingMaturity,
              onToggleLearning: toggleLearningItem,
              onBulkAssign: bulkAssignLearningItems,
              onSetMaturity: handleSetMaturity,
            }}
            handlers={{
              onBack: closeProject,
              onToggleComponent: toggleComponent,
              onRoleChange: handleRoleChange,
              onDelete: handleDelete,
              onSetConfirmDelete: setConfirmDelete,
              onGenerateResetLink: handleGenerateResetLink,
              onCopyResetLink: copyResetLink,
              onDismissResetLink: userId => setResetLinks(prev => { const n = { ...prev }; delete n[userId]; return n }),
              onToggleUserPanel: toggleUserPanel,
              onProjectRefresh: () => loadProjectData(selectedProject.id),
            }}
          />
        )}

        {/* ── SETUP view ── */}
        {view === 'setup' && (
          <SetupView
            companiesData={companiesData}
            onCompaniesChanged={loadCompanies}
          />
        )}
      </main>
    </div>
  )
}
