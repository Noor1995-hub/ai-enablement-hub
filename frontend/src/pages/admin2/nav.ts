// Sidebar section registry — one entry per top-level admin route. Kept as
// plain data (no JSX) so it stays a trivial import for any future consumer
// (e.g. Task 17's feedback badge count); AdminShell owns rendering + icons.
//
// `path` is relative to the /admin index (mirrors the nested routes added in
// App.tsx) so NavLink can build the actual href by prefixing '/admin'.

export type NavIconKey = 'home' | 'users' | 'grid' | 'inbox' | 'edit' | 'folder' | 'mail' | 'terminal' | 'settings'

export interface NavItem {
  key: string
  label: string
  icon: NavIconKey
  path: string
}

export const NAV_ITEMS: NavItem[] = [
  { key: 'dashboard',   label: 'Dashboard',       icon: 'home',     path: '' },
  { key: 'people',      label: 'People',          icon: 'users',    path: 'people' },
  { key: 'assignments', label: 'Assignments',     icon: 'grid',     path: 'assignments' },
  { key: 'feedback',    label: 'Feedback',        icon: 'inbox',    path: 'feedback' },
  { key: 'content-ai',  label: 'Content AI',      icon: 'edit',     path: 'content-improvement' },
  { key: 'projects',    label: 'Projects',        icon: 'folder',   path: 'projects' },
  { key: 'templates',   label: 'Email templates', icon: 'mail',     path: 'templates' },
  { key: 'prompts',     label: 'System prompts',  icon: 'terminal', path: 'prompts' },
  { key: 'setup',       label: 'Setup',           icon: 'settings', path: 'setup' },
]
