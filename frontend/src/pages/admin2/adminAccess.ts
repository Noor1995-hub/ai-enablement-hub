// What each kind of admin may see in the panel (spec
// 2026-10-01-project-scoped-admin-design.md, issue #144). The backend enforces
// every rule; this only keeps the UI from offering what the API would refuse.
import { NAV_ITEMS, type NavItem } from './nav'

export interface AdminViewer {
  isPowerAdmin: boolean
  adminProjectIds: string[]
}

/** Power admins, and anyone who administers at least one project. */
export function canOpenAdmin(viewer: AdminViewer): boolean {
  return viewer.isPowerAdmin || viewer.adminProjectIds.length > 0
}

export function visibleNavItems(viewer: AdminViewer): NavItem[] {
  return NAV_ITEMS.filter(item => viewer.isPowerAdmin || !item.powerOnly)
}

/** The project a project admin should be looking at: the requested one when it
 * is theirs, otherwise their first. Power admins keep whatever they picked
 * (null = all projects). */
export function resolveAdminProject(viewer: AdminViewer, requested: string | null): string | null {
  if (viewer.isPowerAdmin) return requested
  if (requested !== null && viewer.adminProjectIds.includes(requested)) return requested
  return viewer.adminProjectIds[0] ?? null
}

export interface ManagedUser {
  id: string
  role: string
  admin_project_ids: string[]
}

/** Remove/role actions on a person. A project admin manages learners only;
 * nobody removes themselves (the API answers 403/409 otherwise). */
export function canManageUser(viewer: AdminViewer & { userId: string | null }, target: ManagedUser): boolean {
  if (target.id === viewer.userId) return false
  if (viewer.isPowerAdmin) return true
  return target.role !== 'admin' && target.admin_project_ids.length === 0
}
