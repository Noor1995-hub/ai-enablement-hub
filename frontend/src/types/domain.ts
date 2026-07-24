// Aliases over the generated OpenAPI types so pages never spell out the
// components['schemas'][...] indexing. Grows as Batches 5–6 port more pages.
import type { components } from '../api/schema'

export type UserProfile = components['schemas']['UserProfileResponse']
export type InviteInfo = components['schemas']['InviteInfoResponse']

// Batch 5 — learner pages
export type TrackNode = components['schemas']['TrackNode']
export type ModuleNode = components['schemas']['ModuleNode']
export type ModuleLessonItem = components['schemas']['ModuleLessonItem']
export type LessonDetail = components['schemas']['LessonDetailResponse']

// Batch 6 — admin pages
export type CompanyWithProjects = components['schemas']['CompanyWithProjects']
export type CompanyOut = components['schemas']['CompanyOut']
export type ProjectOut = components['schemas']['ProjectOut']
export type LinkResponse = components['schemas']['LinkResponse']
export type AdminUser = components['schemas']['AdminUserOut']
export type AdminLearning = components['schemas']['AdminLearningResponse']
export type AdminLearningUser = components['schemas']['AdminLearningUserOut']
export type AdminSurvey = components['schemas']['AdminSurveyOut']
export type ComponentState = components['schemas']['ComponentState']
export type Track = components['schemas']['TrackOut']
export type TrackModule = components['schemas']['TrackModuleOut']
export type ModuleOut = components['schemas']['ModuleOut']

// Invite/reset emails (auto-sent via ACS when configured server-side)
export type EmailStatus = components['schemas']['LinkResponse']['email_status']

// Per-project email templates (admin editor)
export type EmailTemplate = components['schemas']['EmailTemplateOut']
export type EmailTemplatePurpose = EmailTemplate['purpose']
export type EmailTemplatePreview = components['schemas']['EmailTemplatePreviewResponse']

// --- INTERIM admin-redesign types: replace with generated schema aliases after gen:api (plan Task 11) ---
// The admin-panel-redesign plan's backend Phase A ships these endpoints ahead of a schema
// regen (dashboard + pagination/enrichment specifically aren't wired into the live backend on
// this branch yet — see docs/superpowers/plans/2026-07-23-admin-panel-redesign.md). Field
// names/types below are copied verbatim from that plan's schema definitions (§Task 3/4
// DefaultsResponse/DefaultsUpdateRequest/ApplyDefaultsResponse, §Task 5 BulkAssignmentRequest,
// §Task 6 AdminFeedbackOut/AdminFeedbackListResponse/FeedbackStatusUpdateRequest, §Task 7
// ReminderResponse, §Task 8 AdminUserOut additive fields, §Task 10 DashboardResponse block).
// Once Task 11 (the plan's Phase A checkpoint) regenerates schema.d.ts, delete this block and
// replace each alias below with the real `components['schemas'][...]` one.

// §Task 3/4 — project default tracks
export interface DefaultsResponse {
  track_ids: string[]
}
export interface DefaultsUpdateRequest {
  track_ids: string[]
}
export interface ApplyDefaultsResponse {
  users_updated: number
}

// §Task 5 — multi-user bulk assignment
export interface BulkAssignmentRequest {
  user_ids: string[]
  track_ids?: string[] | null
  module_ids?: string[] | null
  lesson_ids?: string[] | null
  assigned: boolean
}

// §Task 6 — feedback triage
export type FeedbackStatus = 'new' | 'accepted' | 'dismissed'

export interface AdminFeedbackOut {
  id: string
  user_id: string
  user_name: string
  company_name: string | null
  project_name: string | null
  lesson_id: string
  lesson_title: string
  module_id: string
  module_title: string
  track_id: string
  track_name: string
  track_level: string
  message: string
  status: FeedbackStatus
  created_at: string
  reviewed_at: string | null
}

export interface AdminFeedbackListResponse {
  items: AdminFeedbackOut[]
  total: number
  limit: number
  offset: number
}

export interface FeedbackStatusUpdateRequest {
  status: FeedbackStatus
}

// §Task 7 — reminder email
export interface ReminderResponse {
  email_status: EmailStatus
}

// §Task 10 — dashboard aggregates
export interface DashboardTiles {
  learners: number
  active_week: number
  attention: number
  new_feedback: number
}

export type AttentionKind = 'never_activated' | 'not_assessed' | 'stalled'

export interface AttentionItemOut {
  user_id: string
  name: string
  email: string
  project_id: string | null
  project_name: string | null
  company_name: string | null
  kind: AttentionKind
  reason: string
}

export interface FunnelOut {
  project_id: string
  project_name: string
  company_name: string
  invited: number
  activated: number
  assessed: number
  started: number
  completed_track: number
}

export interface MaturityDistributionOut {
  explore: number
  practitioner: number
  integrator: number
  multiplier: number
}

export interface DashboardResponse {
  tiles: DashboardTiles
  attention: AttentionItemOut[]
  funnels: FunnelOut[]
  maturity: MaturityDistributionOut
}

// §Task 8 — AdminUserOut's coming enrichment fields + §Task 9's `total` envelope field.
// Extension types over the generated shape rather than redefining it whole.
export type AdminUserEnriched = AdminUser & {
  last_active_at: string | null
  activated: boolean
  assigned_lesson_count: number
  completed_lesson_count: number
  needs_attention: boolean
  attention_reason: string | null
  default_track_ids: string[]
  default_module_ids: string[]
  default_lesson_ids: string[]
}

export type AdminLearningUserEnriched = AdminLearningUser & {
  default_track_ids: string[]
  default_module_ids: string[]
  default_lesson_ids: string[]
}

export type AdminUsersResponseEnriched = {
  users: AdminUserEnriched[]
  total: number
}

export type AdminLearningResponseEnriched = Omit<AdminLearning, 'users'> & {
  users: AdminLearningUserEnriched[]
  total: number
}
// --- end INTERIM admin-redesign types ---
