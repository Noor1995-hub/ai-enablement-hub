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

// --- Admin-redesign types: aliased onto the generated schema (plan Task 11 gen:api swap) ---
// These used to be hand-written interim types (copied verbatim from the plan's schema
// definitions) predating the backend's Phase A endpoints. Now that schema.d.ts is regenerated,
// every one of them has a real `components['schemas'][...]` counterpart — the zero-drift
// cross-check done during Task 13 held, so this is a pure aliasing swap, not a redefinition.

// §Task 3/4 — project default tracks
export type DefaultsResponse = components['schemas']['DefaultsResponse']
export type DefaultsUpdateRequest = components['schemas']['DefaultsUpdateRequest']
export type ApplyDefaultsResponse = components['schemas']['ApplyDefaultsResponse']

// §Task 5 — multi-user bulk assignment
export type BulkAssignmentRequest = components['schemas']['BulkAssignmentRequest']

// §Task 6 — feedback triage
export type AdminFeedbackOut = components['schemas']['AdminFeedbackOut']
export type FeedbackStatus = AdminFeedbackOut['status']
export type AdminFeedbackListResponse = components['schemas']['AdminFeedbackListResponse']
export type FeedbackStatusUpdateRequest = components['schemas']['FeedbackStatusUpdateRequest']

// §Task 7 — reminder email
export type ReminderResponse = components['schemas']['ReminderResponse']

// §Task 10 — dashboard aggregates
export type DashboardTiles = components['schemas']['DashboardTiles']
export type AttentionItemOut = components['schemas']['AttentionItemOut']
export type AttentionKind = AttentionItemOut['kind']
export type FunnelOut = components['schemas']['FunnelOut']
export type MaturityDistributionOut = components['schemas']['MaturityDistributionOut']
export type DashboardResponse = components['schemas']['DashboardResponse']

// §Task 8 — AdminUserOut's enrichment fields (last_active_at, activated, assigned/completed
// lesson counts, needs_attention/attention_reason, default_*_ids) and AdminLearningUserOut's
// default_*_ids are now real generated fields (not client-only extensions), and §Task 9's
// `total` envelope field is real on both AdminUsersResponse and AdminLearningResponse — so
// these "*Enriched" names are now plain aliases onto the base generated types, kept only so
// existing screen imports don't churn.
export type AdminUserEnriched = AdminUser
export type AdminLearningUserEnriched = AdminLearningUser
export type AdminUsersResponseEnriched = components['schemas']['AdminUsersResponse']
export type AdminLearningResponseEnriched = components['schemas']['AdminLearningResponse']
// --- end admin-redesign types ---
