import type { Role } from '../contexts/AuthContext'

export type SurveyStatus = 'not_started' | 'in_progress' | 'complete'
export type InterviewStatus = 'not_started' | 'in_progress' | 'complete'
export type InterviewTile = 'locked' | 'needs_assessment' | 'available' | 'in_progress' | 'done'

/** The journey tile for the interview. Mirrors the backend gates: the project-level
 *  component lock (ComponentLockedError) first, then require_completed_assessment
 *  (admins exempt, a draft assessment is not enough). A finished playbook stays
 *  reachable regardless, because GET /api/interview/me is not assessment-gated. */
export function resolveInterviewTile(args: {
  componentLocked: boolean
  role: Role | null
  surveyStatus: SurveyStatus
  interviewStatus: InterviewStatus
}): InterviewTile {
  const { componentLocked, role, surveyStatus, interviewStatus } = args
  if (componentLocked) return 'locked'
  if (interviewStatus === 'complete') return 'done'
  if (role !== 'admin' && surveyStatus !== 'complete') return 'needs_assessment'
  return interviewStatus === 'in_progress' ? 'in_progress' : 'available'
}
