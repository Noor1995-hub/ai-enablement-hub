import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// The admin panel is a lazy chunk (review 8.4). These tests pin the wiring the
// bundle split depends on: the shell renders through Suspense, and a learner
// never triggers the admin import.
const h = vi.hoisted(() => ({
  auth: {
    session: true,
    role: 'admin',
    isPowerAdmin: true,
    adminProjectIds: [] as string[],
    passwordSet: true,
    externalLogin: false,
    loading: false,
  } as Record<string, unknown>,
  shellImports: 0,
  releaseShell: () => {},
}))

vi.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => h.auth,
}))
vi.mock('./pages/JourneyHome', () => ({ default: () => <p>Learner home</p> }))
vi.mock('./pages/admin2/AdminShell', async () => {
  h.shellImports += 1
  await new Promise<void>(resolve => { h.releaseShell = resolve })
  const { Outlet } = await import('react-router-dom')
  return { default: () => <div><p>Admin shell</p><Outlet /></div> }
})
vi.mock('./pages/admin2/DashboardPage', () => ({ default: () => <p>Admin dashboard</p> }))

import App from './App'

beforeEach(() => {
  window.scrollTo = vi.fn() // ScrollToTop; jsdom does not implement it
  h.auth.role = 'admin'
  h.auth.isPowerAdmin = true
  h.auth.adminProjectIds = []
})

describe('lazy admin routes', () => {
  // Runs first on purpose: the lazy import is cached per module registry, so
  // this must observe the admin module before any admin render has loaded it.
  it('never loads the admin chunk for a learner sent away from /admin', async () => {
    h.auth.role = 'user'
    h.auth.isPowerAdmin = false
    window.history.pushState({}, '', '/admin')
    render(<App />)
    expect(await screen.findByText('Learner home')).toBeInTheDocument()
    expect(h.shellImports).toBe(0)
  })

  it('shows a spinner while the admin chunk loads, then the shell and the section', async () => {
    window.history.pushState({}, '', '/admin')
    const { container } = render(<App />)

    expect(container.querySelector('svg')).toBeInTheDocument()
    expect(screen.queryByText('Admin shell')).not.toBeInTheDocument()
    await waitFor(() => expect(h.shellImports).toBe(1))

    h.releaseShell()
    expect(await screen.findByText('Admin shell')).toBeInTheDocument()
    expect(await screen.findByText('Admin dashboard')).toBeInTheDocument()
  })
})

describe('project admins (spec 2026-10-01, #144)', () => {
  it('lets a project admin into the panel', async () => {
    h.auth.role = 'user'
    h.auth.isPowerAdmin = false
    h.auth.adminProjectIds = ['p1']
    window.history.pushState({}, '', '/admin')
    render(<App />)
    h.releaseShell()
    expect(await screen.findByText('Admin dashboard')).toBeInTheDocument()
  })

  it('sends a project admin away from a power-only section', async () => {
    h.auth.role = 'user'
    h.auth.isPowerAdmin = false
    h.auth.adminProjectIds = ['p1']
    window.history.pushState({}, '', '/admin/setup')
    render(<App />)
    h.releaseShell()
    expect(await screen.findByText('Admin dashboard')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/admin')
  })
})
