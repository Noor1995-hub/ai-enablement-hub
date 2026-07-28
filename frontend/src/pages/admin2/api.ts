// Thin typed hooks over `client` (openapi-fetch) + @tanstack/react-query for the whole admin2
// shell. Queries return caller-ready domain data (never the raw envelope-vs-error union);
// mutations invalidate the query keys they affect and otherwise stay dumb — screen-specific
// optimistic updates are a later (Phase C) concern, not this task's.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { client, errorMessage } from '../../api/client'
import type {
  AdminFeedbackListResponse,
  AdminLearningResponseEnriched,
  AdminLearningUserEnriched,
  AdminSurvey,
  AdminUsersResponseEnriched,
  AiSurfaceState,
  ApplyDefaultsResponse,
  BulkAssignmentRequest,
  CompanyOut,
  CompanyWithProjects,
  ComponentState,
  DashboardResponse,
  DefaultsResponse,
  DefaultsUpdateRequest,
  FeedbackStatus,
  FeedbackStatusUpdateRequest,
  LinkResponse,
  ProjectOut,
  ReminderResponse,
  SuggestTriageResponse,
  Track,
} from '../../types/domain'

// ── Interim raw-fetch escape hatch ─────────────────────────────────────────────────────────
// openapi-fetch's client.GET/PUT/POST/PATCH are typed strictly against the generated `paths`
// map (src/api/schema.d.ts). Endpoints not yet regenerated into that schema — defaults,
// defaults/apply, the multi-user bulk-assignment endpoint, feedback, and the reminder/dashboard
// routes (see the INTERIM block atop src/types/domain.ts) — fail to typecheck through it. This
// is the ONE `as` cast for all of them; every hook below that needs one of these routes calls
// through `rawRequest` instead of casting at its own call site.
interface RawInit {
  params?: { query?: Record<string, string | number | boolean | undefined> }
  body?: unknown
}
interface RawResult<T> {
  data?: T
  error?: unknown
}
type RawMethod = 'GET' | 'PUT' | 'POST' | 'PATCH'
type RawClient = Record<RawMethod, (url: string, init?: RawInit) => Promise<RawResult<unknown>>>

async function rawRequest<T>(method: RawMethod, url: string, init?: RawInit): Promise<RawResult<T>> {
  const raw = client as unknown as RawClient
  return (await raw[method](url, init)) as RawResult<T>
}

// ── Queries ─────────────────────────────────────────────────────────────────────────────────

export interface AdminUsersParams {
  project: string | null
  q?: string
  status?: 'active' | 'invited' | 'attention'
  page?: number
}

// Matches the People screen's own PAGE_SIZE (PeoplePage.tsx) — kept as a local constant here
// since `AdminUsersParams` carries a page number, not a limit.
const ADMIN_USERS_PAGE_SIZE = 50

async function fetchAdminUsers(params: AdminUsersParams): Promise<AdminUsersResponseEnriched> {
  const offset = ((params.page ?? 1) - 1) * ADMIN_USERS_PAGE_SIZE
  const { data, error } = await client.GET('/api/admin/users', {
    params: {
      query: {
        project_id: params.project ?? undefined,
        q: params.q,
        status: params.status,
        limit: ADMIN_USERS_PAGE_SIZE,
        offset,
      },
    },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load users.'))
  return data
}

export function useAdminUsers(params: AdminUsersParams) {
  return useQuery({
    queryKey: [
      'admin',
      'users',
      { project: params.project, q: params.q, status: params.status, page: params.page },
    ] as const,
    queryFn: () => fetchAdminUsers(params),
  })
}

async function fetchLearning(projectId: string | null): Promise<AdminLearningResponseEnriched> {
  // No page params here — useLearning's callers (Matrix/Assignments) don't carry a page number,
  // so only project_id is forwarded; modules/lessons always come back complete regardless of
  // scope (the backend filters `users` only), matching what the matrix needs to build columns.
  const { data, error } = await client.GET('/api/admin/learning', {
    params: { query: { project_id: projectId ?? undefined } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load the learning overview.'))
  return data
}

export function useLearning(projectId: string | null) {
  return useQuery({
    queryKey: ['admin', 'learning', { project: projectId }] as const,
    queryFn: () => fetchLearning(projectId),
  })
}

async function fetchCompanies(): Promise<CompanyWithProjects[]> {
  const { data, error } = await client.GET('/api/admin/companies')
  if (!data) throw new Error(errorMessage(error, 'Failed to load companies.'))
  return data.companies
}

export function useCompanies() {
  return useQuery({
    queryKey: ['admin', 'companies'] as const,
    queryFn: fetchCompanies,
  })
}

async function fetchTracks(): Promise<Track[]> {
  const { data, error } = await client.GET('/api/tracks')
  if (!data) throw new Error(errorMessage(error, 'Failed to load tracks.'))
  return data
}

export function useTracks() {
  return useQuery({
    queryKey: ['admin', 'tracks'] as const,
    queryFn: fetchTracks,
  })
}

async function fetchDashboard(projectId: string | null): Promise<DashboardResponse> {
  const { data, error } = await rawRequest<DashboardResponse>('GET', '/api/admin/dashboard', {
    params: { query: { project_id: projectId ?? undefined } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load the dashboard.'))
  return data
}

export function useDashboard(projectId: string | null) {
  return useQuery({
    queryKey: ['admin', 'dashboard', projectId] as const,
    queryFn: () => fetchDashboard(projectId),
  })
}

export interface FeedbackParams {
  status?: FeedbackStatus
  track?: string
  project: string | null
  page?: number
  /** Defaults to FEEDBACK_PAGE_SIZE. The sidebar badge overrides this to 1 —
   * carried in the query key (below) so that call never collides with a
   * paginated list's cache entry. */
  limit?: number
}

export const FEEDBACK_PAGE_SIZE = 50

async function fetchFeedback(params: FeedbackParams): Promise<AdminFeedbackListResponse> {
  const limit = params.limit ?? FEEDBACK_PAGE_SIZE
  const offset = ((params.page ?? 1) - 1) * limit
  const { data, error } = await rawRequest<AdminFeedbackListResponse>('GET', '/api/admin/feedback', {
    params: {
      query: {
        status: params.status,
        track_id: params.track,
        project_id: params.project ?? undefined,
        limit,
        offset,
      },
    },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load feedback.'))
  return data
}

export function useFeedback(params: FeedbackParams) {
  return useQuery({
    queryKey: [
      'admin',
      'feedback',
      { status: params.status, track: params.track, project: params.project, page: params.page, limit: params.limit },
    ] as const,
    queryFn: () => fetchFeedback(params),
  })
}

async function fetchDefaults(projectId: string): Promise<DefaultsResponse> {
  const { data, error } = await rawRequest<DefaultsResponse>('GET', `/api/admin/projects/${projectId}/defaults`)
  if (!data) throw new Error(errorMessage(error, 'Failed to load default tracks.'))
  return data
}

/** Defaults are inherently project-scoped — `enabled` guards the "all projects" (null) case,
 * so the `projectId!` inside `queryFn` never actually runs unscoped. */
export function useDefaults(projectId: string | null) {
  return useQuery({
    queryKey: ['admin', 'defaults', projectId] as const,
    queryFn: () => fetchDefaults(projectId as string),
    enabled: projectId !== null,
  })
}

async function fetchComponents(projectId: string): Promise<Record<string, ComponentState>> {
  const { data, error } = await client.GET('/api/admin/projects/{project_id}/components', {
    params: { path: { project_id: projectId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load component access.'))
  return data.components
}

export function useComponents(projectId: string | null) {
  return useQuery({
    queryKey: ['admin', 'components', projectId] as const,
    queryFn: () => fetchComponents(projectId as string),
    enabled: projectId !== null,
  })
}

async function fetchAiSettings(projectId: string): Promise<Record<string, AiSurfaceState>> {
  const { data, error } = await client.GET('/api/admin/projects/{project_id}/ai', {
    params: { path: { project_id: projectId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load AI assistant settings.'))
  return data.settings
}

export function useAiSettings(projectId: string | null) {
  return useQuery({
    queryKey: ['admin', 'ai', projectId] as const,
    queryFn: () => fetchAiSettings(projectId as string),
    enabled: projectId !== null,
  })
}

async function fetchSurvey(userId: string): Promise<AdminSurvey | null> {
  const { data, error } = await client.GET('/api/admin/surveys/{user_id}', {
    params: { path: { user_id: userId } },
  })
  if (!data) throw new Error(errorMessage(error, "Failed to load the user's survey."))
  return data.survey
}

export function useSurvey(userId: string | null) {
  return useQuery({
    queryKey: ['admin', 'survey', userId] as const,
    queryFn: () => fetchSurvey(userId as string),
    enabled: userId !== null,
  })
}

// ── Mutations ───────────────────────────────────────────────────────────────────────────────
// Every mutation below just invalidates the query keys it can affect; optimistic patches are a
// screen-level concern for later Phase C tasks.

export type AssignmentKind = 'track' | 'module' | 'lesson'

export interface ToggleAssignmentInput {
  userId: string
  kind: AssignmentKind
  id: string
  assigned: boolean
}

async function toggleAssignment({ userId, kind, id, assigned }: ToggleAssignmentInput): Promise<void> {
  const body = { assigned }
  const { error } =
    kind === 'track'
      ? await client.PUT('/api/admin/users/{user_id}/tracks/{track_id}', {
          params: { path: { user_id: userId, track_id: id } },
          body,
        })
      : kind === 'module'
        ? await client.PUT('/api/admin/users/{user_id}/modules/{module_id}', {
            params: { path: { user_id: userId, module_id: id } },
            body,
          })
        : await client.PUT('/api/admin/users/{user_id}/lessons/{lesson_id}', {
            params: { path: { user_id: userId, lesson_id: id } },
            body,
          })
  if (error) throw new Error(errorMessage(error, 'Failed to update assignment.'))
}

/** Add ids to (or remove them from) an assignment array, deduped. Returns the
 * original reference untouched when there is nothing to change. */
function mergeAssignmentIds(current: string[], delta: string[], assigned: boolean): string[] {
  if (delta.length === 0) return current
  if (assigned) return [...new Set([...current, ...delta])]
  const remove = new Set(delta)
  return current.filter(id => !remove.has(id))
}

/** Mirror the server's FULL-RESYNC cascade (the cascading-assignment feature)
 * onto one cached learning-user so the optimistic matrix matches what a refetch
 * returns: toggling a track patches the track + ALL its module + ALL their
 * lesson ids; a module patches the module + its lesson ids; a lesson only
 * itself. `default_*_ids` are intentionally left untouched — a user-cell toggle
 * never rewrites default provenance (the cell stops reading the default arrays
 * once the id leaves `assigned_*_ids`, and `onSettled` reconciles the exact
 * provenance on refetch). */
function cascadeToggleUser(
  user: AdminLearningUserEnriched,
  kind: AssignmentKind,
  targetId: string,
  assigned: boolean,
  modules: AdminLearningResponseEnriched['modules'],
  lessons: AdminLearningResponseEnriched['lessons'],
): AdminLearningUserEnriched {
  let trackIds: string[] = []
  let moduleIds: string[] = []
  let lessonIds: string[] = []
  if (kind === 'track') {
    trackIds = [targetId]
    moduleIds = modules.filter(m => m.track_id === targetId).map(m => m.id)
    const moduleIdSet = new Set(moduleIds)
    lessonIds = lessons.filter(l => moduleIdSet.has(l.module_id)).map(l => l.id)
  } else if (kind === 'module') {
    moduleIds = [targetId]
    lessonIds = lessons.filter(l => l.module_id === targetId).map(l => l.id)
  } else {
    lessonIds = [targetId]
  }
  return {
    ...user,
    assigned_track_ids: mergeAssignmentIds(user.assigned_track_ids, trackIds, assigned),
    assigned_module_ids: mergeAssignmentIds(user.assigned_module_ids, moduleIds, assigned),
    assigned_lesson_ids: mergeAssignmentIds(user.assigned_lesson_ids, lessonIds, assigned),
  }
}

/** Single track/module/lesson toggle for one user — optimistic (Phase C /
 * Assignments matrix). `onMutate` patches every cached `['admin','learning']`
 * response with the local cascade mirror above; `onError` rolls the snapshots
 * back; `onSettled` invalidates users/learning/dashboard (preserving the prior
 * invalidation set) so the server's authoritative resync always wins. */
export function useToggleAssignment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: toggleAssignment,
    onMutate: async ({ userId, kind, id, assigned }) => {
      await queryClient.cancelQueries({ queryKey: ['admin', 'learning'] })
      const snapshots = queryClient.getQueriesData<AdminLearningResponseEnriched>({
        queryKey: ['admin', 'learning'],
      })
      for (const [key, data] of snapshots) {
        if (!data) continue
        queryClient.setQueryData<AdminLearningResponseEnriched>(key, {
          ...data,
          users: data.users.map(u =>
            u.id === userId ? cascadeToggleUser(u, kind, id, assigned, data.modules, data.lessons) : u,
          ),
        })
      }
      return { snapshots }
    },
    onError: (_error, _variables, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data))
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'learning'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

async function bulkAssignUsers(body: BulkAssignmentRequest): Promise<void> {
  const { error } = await rawRequest<void>('POST', '/api/admin/assignments/bulk', { body })
  if (error) throw new Error(errorMessage(error, 'Failed to update assignments.'))
}

/** Many-users x one-content-kind assignment (or unassignment) — `user_ids` can be a single id,
 * so this also covers the "assign to just this one user" case via the same endpoint. */
export function useBulkAssignUsers() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: bulkAssignUsers,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'learning'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

export interface SetDefaultsInput {
  projectId: string
  trackIds: string[]
}

async function setDefaults({ projectId, trackIds }: SetDefaultsInput): Promise<void> {
  const body: DefaultsUpdateRequest = { track_ids: trackIds }
  const { error } = await rawRequest<void>('PUT', `/api/admin/projects/${projectId}/defaults`, { body })
  if (error) throw new Error(errorMessage(error, 'Failed to save default tracks.'))
}

/** Full-replace of a project's default tracks — optimistic on
 * `['admin','defaults',projectId]` so the matrix's defaults prop advances at
 * click time (successive toggles then compose from fresh state instead of a
 * stale pre-refetch snapshot); `onError` rolls the snapshot back and the caller
 * surfaces the failure via `isError`. Only the defaults key is touched — the
 * PUT does not retro-apply to participants (that is the separate apply action),
 * so no users/learning invalidation here. */
export function useSetDefaults() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: setDefaults,
    onMutate: async ({ projectId, trackIds }) => {
      const key = ['admin', 'defaults', projectId] as const
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<DefaultsResponse>(key)
      queryClient.setQueryData<DefaultsResponse>(key, { track_ids: trackIds })
      return { key, previous }
    },
    onError: (_error, _variables, context) => {
      if (context) queryClient.setQueryData(context.key, context.previous)
    },
    onSettled: (_data, _error, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'defaults', variables.projectId] })
    },
  })
}

async function applyDefaults(projectId: string): Promise<ApplyDefaultsResponse> {
  const { data, error } = await rawRequest<ApplyDefaultsResponse>(
    'POST',
    `/api/admin/projects/${projectId}/defaults/apply`,
  )
  if (!data) throw new Error(errorMessage(error, 'Failed to apply default tracks.'))
  return data
}

/** Backfills the project's current defaults onto every existing participant (additive-only on
 * the backend); affects users/learning/dashboard the same way a bulk assignment would. */
export function useApplyDefaults() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: applyDefaults,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'learning'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

async function sendReminder(userId: string): Promise<ReminderResponse> {
  const { data, error } = await rawRequest<ReminderResponse>('POST', `/api/admin/users/${userId}/reminder`)
  if (!data) throw new Error(errorMessage(error, 'Failed to send the reminder.'))
  return data
}

/** No query key to invalidate — sending a reminder doesn't change any cached admin data. */
export function useSendReminder() {
  return useMutation({ mutationFn: sendReminder })
}

export interface PatchFeedbackInput {
  id: string
  status: FeedbackStatus
}

async function patchFeedback({ id, status }: PatchFeedbackInput): Promise<void> {
  const body: FeedbackStatusUpdateRequest = { status }
  const { error } = await rawRequest<void>('PATCH', `/api/admin/feedback/${id}`, { body })
  if (error) throw new Error(errorMessage(error, 'Failed to update the feedback status.'))
}

/** Optimistic status flip (Task 18 / Feedback queue) — mirrors
 * `useToggleAssignment`/`useSetDefaults`'s onMutate-snapshot-onError-rollback
 * shape. Patches the item's `status` in EVERY cached `['admin','feedback']`
 * page it appears in (the list query and the New-count/badge query share the
 * same prefix), but never removes it from a list — a card whose status no
 * longer matches the active pill stays visible (dimmed) until `onSettled`'s
 * invalidation brings back the server's authoritative page, which also
 * refreshes the sidebar badge for free (same query key prefix). */
export function usePatchFeedback() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: patchFeedback,
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ['admin', 'feedback'] })
      const snapshots = queryClient.getQueriesData<AdminFeedbackListResponse>({
        queryKey: ['admin', 'feedback'],
      })
      for (const [key, data] of snapshots) {
        if (!data) continue
        queryClient.setQueryData<AdminFeedbackListResponse>(key, {
          ...data,
          items: data.items.map(item => (item.id === id ? { ...item, status } : item)),
        })
      }
      return { snapshots }
    },
    onError: (_error, _variables, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data))
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'feedback'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

export interface SuggestTriageInput {
  project: string | null
  limit?: number
}

async function suggestTriage({ project, limit }: SuggestTriageInput): Promise<SuggestTriageResponse> {
  const { data, error } = await rawRequest<SuggestTriageResponse>('POST', '/api/admin/feedback/suggest-triage', {
    params: { query: { project_id: project ?? undefined, limit } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to generate triage suggestions.'))
  return data
}

/** Fills the AI triage hints on `new` feedback that has none yet. Deliberately
 * admin-triggered (a button), not fired on page mount: every run costs model
 * tokens, and the backend bounds it per call. Invalidates `['admin','feedback']`
 * so the queue (and the sidebar badge, same key prefix) re-renders with the
 * suggestions; the item `status` is untouched by the run, so nothing moves
 * between pills. */
export function useSuggestTriage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: suggestTriage,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'feedback'] })
    },
  })
}

export interface SetRoleInput {
  userId: string
  role: 'admin' | 'user+' | 'user'
}

async function setRole({ userId, role }: SetRoleInput): Promise<void> {
  const { error } = await client.PATCH('/api/admin/users/{user_id}', {
    params: { path: { user_id: userId } },
    body: { role },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to update the role.'))
}

export function useSetRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: setRole,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'learning'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

export interface SetMaturityInput {
  userId: string
  level: 'explore' | 'practitioner' | 'integrator' | 'multiplier' | null
}

async function setMaturity({ userId, level }: SetMaturityInput): Promise<void> {
  const { error } = await client.PUT('/api/admin/users/{user_id}/maturity', {
    params: { path: { user_id: userId } },
    body: { level },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to update the maturity level.'))
}

export function useSetMaturity() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: setMaturity,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'learning'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

async function resetLink(userId: string): Promise<LinkResponse> {
  const { data, error } = await client.POST('/api/admin/users/{user_id}/reset-link', {
    params: { path: { user_id: userId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to generate a reset link.'))
  return data
}

/** No query key to invalidate — the link is one-shot data, not part of the cached user list. */
export function useResetLink() {
  return useMutation({ mutationFn: resetLink })
}

async function deleteUser(userId: string): Promise<void> {
  const { error } = await client.DELETE('/api/admin/users/{user_id}', {
    params: { path: { user_id: userId } },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to delete the user.'))
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'learning'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

export interface InviteInput {
  email: string
  firstName: string
  lastName: string
  projectId: string
  sendEmail: boolean
}

async function invite({ email, firstName, lastName, projectId, sendEmail }: InviteInput): Promise<LinkResponse> {
  const { data, error } = await client.POST('/api/admin/invites', {
    body: {
      email,
      first_name: firstName,
      last_name: lastName,
      project_id: projectId,
      send_email: sendEmail,
    },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to create the invite.'))
  return data
}

export function useInvite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: invite,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'learning'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] })
    },
  })
}

export interface ToggleComponentInput {
  projectId: string
  component: 'assessment' | 'learning' | 'interview'
  hidden?: boolean
  locked?: boolean
}

async function toggleComponent({ projectId, component, hidden, locked }: ToggleComponentInput): Promise<void> {
  const { error } = await client.PUT('/api/admin/projects/{project_id}/components/{component}', {
    params: { path: { project_id: projectId, component } },
    body: { hidden, locked },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to update component access.'))
}

/** Optimistic on `['admin','components',projectId]` — mirrors
 * `useSetDefaults`'s onMutate-snapshot-onError-rollback shape (same family as
 * `useToggleAssignment`/`usePatchFeedback`). Needed because `onSettled`'s
 * `invalidateQueries` is fire-and-forget: a caller whose "busy" flag clears as
 * soon as `mutateAsync` resolves (ProjectsPage's per-component toggle rows)
 * would otherwise read the stale pre-mutation cache on a second rapid toggle
 * and silently revert the first one (Task 19 review finding — e.g. unlock
 * Learning, then immediately toggle its visibility: the second PUT's `locked`
 * field must see the already-unlocked value, not the value from before the
 * first click). The optimistic patch lands synchronously at click time
 * (onMutate runs before the network call), so it composes correctly across
 * rapid sequential toggles on the same or different fields; `hidden`/`locked`
 * are optional on the input, so only the field(s) the caller actually passed
 * are merged into the cached component's state. */
export function useToggleComponent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: toggleComponent,
    onMutate: async ({ projectId, component, hidden, locked }) => {
      const key = ['admin', 'components', projectId] as const
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<Record<string, ComponentState>>(key)
      if (previous) {
        const current = previous[component] ?? { hidden: false, locked: false }
        queryClient.setQueryData<Record<string, ComponentState>>(key, {
          ...previous,
          [component]: {
            hidden: hidden ?? current.hidden,
            locked: locked ?? current.locked,
          },
        })
      }
      return { key, previous }
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(context.key, context.previous)
    },
    onSettled: (_data, _error, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'components', variables.projectId] })
    },
  })
}

export type AiSurfaceKind = 'chatbot' | 'assessment' | 'lesson' | 'interview'

export interface ToggleAiSettingInput {
  projectId: string
  kind: AiSurfaceKind
  enabled: boolean
}

async function toggleAiSetting({ projectId, kind, enabled }: ToggleAiSettingInput): Promise<void> {
  const { error } = await client.PUT('/api/admin/projects/{project_id}/ai/{kind}', {
    params: { path: { project_id: projectId, kind } },
    body: { enabled },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to update the AI assistant setting.'))
}

/** Optimistic on `['admin','ai',projectId]` — same onMutate-snapshot-onError-rollback shape
 * as `useToggleComponent` (and for the same reason: a caller whose "busy" flag clears when
 * `mutateAsync` resolves would otherwise read the stale pre-invalidation cache on a rapid
 * second toggle and silently revert the first). Each AI surface has a single `enabled` flag,
 * so the patch replaces the whole surface state. */
export function useToggleAiSetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: toggleAiSetting,
    onMutate: async ({ projectId, kind, enabled }) => {
      const key = ['admin', 'ai', projectId] as const
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<Record<string, AiSurfaceState>>(key)
      if (previous) {
        queryClient.setQueryData<Record<string, AiSurfaceState>>(key, {
          ...previous,
          [kind]: { enabled },
        })
      }
      return { key, previous }
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(context.key, context.previous)
    },
    onSettled: (_data, _error, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'ai', variables.projectId] })
    },
  })
}

async function createCompany(name: string): Promise<CompanyOut> {
  const { data, error } = await client.POST('/api/admin/companies', { body: { name } })
  if (!data) throw new Error(errorMessage(error, 'Failed to create the company.'))
  return data
}

export function useCreateCompany() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCompany,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'companies'] })
    },
  })
}

export interface CreateProjectInput {
  name: string
  companyId: string
}

async function createProject({ name, companyId }: CreateProjectInput): Promise<ProjectOut> {
  const { data, error } = await client.POST('/api/admin/projects', {
    body: { name, company_id: companyId },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to create the project.'))
  return data
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'companies'] })
    },
  })
}
