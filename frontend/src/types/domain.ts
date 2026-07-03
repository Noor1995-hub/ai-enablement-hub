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
