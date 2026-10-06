import { describe, expect, it } from 'vitest'
import { canManageUser, canOpenAdmin, resolveAdminProject, visibleNavItems } from './adminAccess'

const power = { isPowerAdmin: true, adminProjectIds: [] }
const coach = { isPowerAdmin: false, adminProjectIds: ['p1', 'p2'] }
const learner = { isPowerAdmin: false, adminProjectIds: [] }

describe('canOpenAdmin', () => {
  it('lets power admins and project admins in, not learners', () => {
    expect(canOpenAdmin(power)).toBe(true)
    expect(canOpenAdmin(coach)).toBe(true)
    expect(canOpenAdmin(learner)).toBe(false)
  })
})

describe('visibleNavItems', () => {
  it('shows a project admin only the project-level pages', () => {
    expect(visibleNavItems(coach).map(i => i.key)).toEqual([
      'dashboard',
      'people',
      'assignments',
      'content',
      'projects',
      'templates',
    ])
  })

  it('shows a power admin everything', () => {
    expect(visibleNavItems(power).map(i => i.key)).toContain('content-ai')
    expect(visibleNavItems(power)).toHaveLength(11)
  })
})

describe('resolveAdminProject', () => {
  it('keeps a power admin on "all projects" or their pick', () => {
    expect(resolveAdminProject(power, null)).toBeNull()
    expect(resolveAdminProject(power, 'px')).toBe('px')
  })

  it('pins a project admin to one of their own projects', () => {
    expect(resolveAdminProject(coach, null)).toBe('p1')
    expect(resolveAdminProject(coach, 'p2')).toBe('p2')
    expect(resolveAdminProject(coach, 'someone-elses')).toBe('p1')
  })
})

describe('canManageUser', () => {
  const learnerTarget = { id: 'u1', role: 'user', admin_project_ids: [] }
  const coachTarget = { id: 'u2', role: 'user', admin_project_ids: ['p1'] }
  const powerTarget = { id: 'u3', role: 'admin', admin_project_ids: [] }

  it('lets a project admin manage learners only', () => {
    const viewer = { ...coach, userId: 'me' }
    expect(canManageUser(viewer, learnerTarget)).toBe(true)
    expect(canManageUser(viewer, coachTarget)).toBe(false)
    expect(canManageUser(viewer, powerTarget)).toBe(false)
  })

  it('lets a power admin manage anyone but themselves', () => {
    const viewer = { ...power, userId: 'u3' }
    expect(canManageUser(viewer, coachTarget)).toBe(true)
    expect(canManageUser(viewer, powerTarget)).toBe(false)
  })
})
