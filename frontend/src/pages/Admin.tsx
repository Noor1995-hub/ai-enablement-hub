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
  ProjectOut,
  Track,
} from '../types/domain'
import { s } from './admin/adminStyles'
import ProjectsView from './admin/ProjectsView'
import ProjectDetailView, { type SelectedProject } from './admin/ProjectDetailView'
import UserPanel from './admin/UserPanel'
import SetupView from './admin/SetupView'

// God-component structure kept for parity (A1 noted, deferred). The old file's
// two hand-rolled `authH` header patterns are gone — the typed api client
// attaches the Bearer token and drives the refresh path (fixes A2).

export interface ResetLinkEntry {
  link: string
  copied: boolean
}

export default function Admin() {
  const { user } = useAuth()

  const [view, setView] = useState<'projects' | 'setup'>('projects')
  // null = list view, otherwise the opened project + its company name
  const [selectedProject, setSelectedProject] = useState<SelectedProject | null>(null)
  // user detail panel
  const [panelUserId, setPanelUserId] = useState<string | null>(null)
  const [panelUserData, setPanelUserData] = useState<AdminUser | null>(null)
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
  const [learningData, setLearningData] = useState<AdminLearning>({ modules: [], users: [] })
  const [togglingItem, setTogglingItem] = useState<string | null>(null)

  /* ── global errors ── */
  const [actionError, setActionError] = useState<string | null>(null)

  /* ── users table state (for project view) ── */
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [togglingRole, setTogglingRole] = useState<string | null>(null)
  const [generatingReset, setGeneratingReset] = useState<string | null>(null)
  const [resetLinks, setResetLinks] = useState<Record<string, ResetLinkEntry>>({})

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
    setPanelUserData(null)
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
  async function openUserPanel(panelUser: AdminUser) {
    setPanelUserId(panelUser.id)
    setPanelUserData(panelUser)
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

  /* ── track/module assignment ── */
  async function toggleLearningItem(action: 'track' | 'module', userId: string, itemId: string, currentlyAssigned: boolean) {
    const key = `${action}-${userId}-${itemId}`
    setTogglingItem(key)
    const listField = action === 'track' ? 'assigned_track_ids' : 'assigned_module_ids'
    try {
      const { error } = action === 'track'
        ? await client.PUT('/api/admin/users/{user_id}/tracks/{track_id}', {
            params: { path: { user_id: userId, track_id: itemId } },
            body: { assigned: !currentlyAssigned },
          })
        : await client.PUT('/api/admin/users/{user_id}/modules/{module_id}', {
            params: { path: { user_id: userId, module_id: itemId } },
            body: { assigned: !currentlyAssigned },
          })
      if (error) {
        setActionError(errorMessage(error, `Failed to update ${action} assignment.`))
      } else {
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
      }
    } catch { setActionError('Network error.') }
    setTogglingItem(null)
  }

  /* ── role / delete / reset ── */
  async function handleRoleToggle(userId: string, currentRole: string) {
    setTogglingRole(userId)
    const newRole = currentRole === 'admin' ? 'user' : 'admin'
    try {
      const { error } = await client.PATCH('/api/admin/users/{user_id}', {
        params: { path: { user_id: userId } },
        body: { role: newRole },
      })
      if (error) {
        setActionError(errorMessage(error, 'Failed to update role.'))
      } else {
        setProjectUsers(prev => prev.map(u => u.id !== userId ? u : { ...u, role: newRole }))
      }
    } catch { setActionError('Network error.') }
    setTogglingRole(null)
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
      if (data) setResetLinks(prev => ({ ...prev, [userId]: { link: data.link, copied: false } }))
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
            handlers={{
              onBack: closeProject,
              onToggleComponent: toggleComponent,
              onRoleToggle: handleRoleToggle,
              onDelete: handleDelete,
              onSetConfirmDelete: setConfirmDelete,
              onGenerateResetLink: handleGenerateResetLink,
              onCopyResetLink: copyResetLink,
              onDismissResetLink: userId => setResetLinks(prev => { const n = { ...prev }; delete n[userId]; return n }),
              onOpenUserPanel: openUserPanel,
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

      {/* ── User detail panel ── */}
      {panelUserId && (
        <UserPanel
          user={panelUserData}
          survey={panelSurvey}
          loadingPanel={loadingPanel}
          learningUser={panelLearningUser}
          tracks={tracks}
          learningData={learningData}
          togglingItem={togglingItem}
          onToggleLearning={toggleLearningItem}
          onClose={() => setPanelUserId(null)}
        />
      )}
    </div>
  )
}
