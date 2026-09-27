import { describe, expect, it } from 'vitest'
import { resolveInterviewTile } from './interviewAccess'

const base = {
  componentLocked: false,
  role: 'user' as const,
  surveyStatus: 'complete' as const,
  interviewStatus: 'not_started' as const,
}

describe('resolveInterviewTile', () => {
  it('a project-level lock wins over everything', () => {
    expect(resolveInterviewTile({ ...base, componentLocked: true, surveyStatus: 'not_started' })).toBe('locked')
  })

  it('a learner without a completed assessment must do it first', () => {
    expect(resolveInterviewTile({ ...base, surveyStatus: 'not_started' })).toBe('needs_assessment')
    expect(resolveInterviewTile({ ...base, surveyStatus: 'in_progress' })).toBe('needs_assessment')
  })

  it('user+ is not exempt, admin is', () => {
    expect(resolveInterviewTile({ ...base, role: 'user+', surveyStatus: 'not_started' })).toBe('needs_assessment')
    expect(resolveInterviewTile({ ...base, role: 'admin', surveyStatus: 'not_started' })).toBe('available')
  })

  it('an existing playbook stays reachable even without an assessment', () => {
    expect(resolveInterviewTile({ ...base, surveyStatus: 'not_started', interviewStatus: 'complete' })).toBe('done')
  })

  it('reflects interview progress once the assessment is done', () => {
    expect(resolveInterviewTile({ ...base, interviewStatus: 'in_progress' })).toBe('in_progress')
    expect(resolveInterviewTile(base)).toBe('available')
  })
})
