// Aliases over the generated OpenAPI types so pages never spell out the
// components['schemas'][...] indexing. Grows as Batches 5–6 port more pages.
import type { components } from '../api/schema'

export type UserProfile = components['schemas']['UserProfileResponse']
export type TokenPair = components['schemas']['TokenPairResponse']
export type InviteInfo = components['schemas']['InviteInfoResponse']

// Batch 5 — learner pages
export type JourneyResponse = components['schemas']['JourneyResponse']
export type SurveyResponse = components['schemas']['SurveyResponseOut']
export type LearningGraph = components['schemas']['LearningGraphResponse']
export type TrackNode = components['schemas']['TrackNode']
export type ModuleNode = components['schemas']['ModuleNode']
export type ModuleLessonItem = components['schemas']['ModuleLessonItem']
export type LessonDetail = components['schemas']['LessonDetailResponse']

// Batch 6 — admin pages
export type CompanyWithProjects = components['schemas']['CompanyWithProjects']
export type ProjectOut = components['schemas']['ProjectOut']
export type AdminUser = components['schemas']['AdminUserOut']
export type AdminLearning = components['schemas']['AdminLearningResponse']
export type AdminLearningUser = components['schemas']['AdminLearningUserOut']
export type AdminLearningLesson = components['schemas']['AdminLearningLessonOut']
export type AdminSurvey = components['schemas']['AdminSurveyOut']
export type ComponentState = components['schemas']['ComponentState']
export type Track = components['schemas']['TrackOut']
export type TrackModule = components['schemas']['TrackModuleOut']
export type ModuleOut = components['schemas']['ModuleOut']

// Invite/reset emails (auto-sent via ACS when configured server-side)
export type EmailStatus = components['schemas']['LinkResponse']['email_status']
