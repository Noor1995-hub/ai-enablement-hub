import { describe, expect, it } from 'vitest'
import { impactSentence } from './orgImpact'

describe('impactSentence', () => {
  it('spells out a project delete', () => {
    expect(impactSentence('project', 'Rollout 2025', { projects: 0, users_deleted: 14, power_admins_kept: 1, project_admin_grants: 2, users_with_progress: 12, other_project_admins_deleted: 0 }))
      .toBe('Deletes Rollout 2025, its 14 users (12 with progress) with their assessments and interviews, its settings and email templates, and 2 project-admin grants. 1 power admin in it keeps their account.')
  })
  it('spells out a company delete with no users', () => {
    expect(impactSentence('company', 'Acme', { projects: 2, users_deleted: 0, power_admins_kept: 0, project_admin_grants: 0, users_with_progress: 0, other_project_admins_deleted: 0 }))
      .toBe('Deletes Acme and its 2 projects. No users are affected.')
  })
  it('names members who run another project', () => {
    expect(impactSentence('project', 'Rollout', { projects: 0, users_deleted: 3, power_admins_kept: 0, project_admin_grants: 0, users_with_progress: 1, other_project_admins_deleted: 1 }))
      .toBe('Deletes Rollout, its 3 users (1 with progress) with their assessments and interviews, including 1 admin of another project, and its settings and email templates.')
  })
})
