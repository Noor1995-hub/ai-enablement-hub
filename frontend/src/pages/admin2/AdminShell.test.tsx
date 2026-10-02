import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminShell from './AdminShell'
import { useScope } from './useScope'

// Scope pinning for project admins (spec 2026-10-01, #144): the API has no
// "all projects" view for them, so no section may ever render unscoped or on
// someone else's project — and the automatic pin must not trap the back button.
const h = vi.hoisted(() => ({
  auth: { isPowerAdmin: false, adminProjectIds: ['p1', 'p2'] as string[], user: { first_name: 'C', last_name: 'A' } },
  seen: [] as (string | null)[],
}))

vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => h.auth }))
vi.mock('./api', () => ({
  useCompanies: () => ({ data: [], isLoading: false, error: null }),
  useFeedback: () => ({ data: undefined }),
  useProposals: () => ({ data: undefined }),
}))

function Section() {
  const { projectId } = useScope()
  h.seen.push(projectId)
  const location = useLocation()
  const navigate = useNavigate()
  return (
    <div>
      <p data-testid="where">{`${location.pathname}${location.search}`}</p>
      <button type="button" onClick={() => navigate(-1)}>back</button>
    </div>
  )
}

function renderAt(entries: string[]) {
  return render(
    <MemoryRouter initialEntries={entries} initialIndex={entries.length - 1}>
      <Routes>
        <Route path="/before" element={<p data-testid="where">/before</p>} />
        <Route path="/admin" element={<AdminShell />}>
          <Route index element={<Section />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  h.seen = []
  h.auth = { isPowerAdmin: false, adminProjectIds: ['p1', 'p2'], user: { first_name: 'C', last_name: 'A' } }
})

describe('AdminShell scope pin', () => {
  it('pins a project admin to their first project before any section renders', async () => {
    renderAt(['/admin'])
    expect(await screen.findByTestId('where')).toHaveTextContent('/admin?project=p1')
    expect(h.seen.every(id => id === 'p1')).toBe(true)
  })

  it('corrects a deep link to someone else\'s project', async () => {
    renderAt(['/admin?project=foreign'])
    expect(await screen.findByTestId('where')).toHaveTextContent('/admin?project=p1')
    expect(h.seen).not.toContain('foreign')
  })

  it('keeps a project admin on their own second project', async () => {
    renderAt(['/admin?project=p2'])
    expect(await screen.findByTestId('where')).toHaveTextContent('/admin?project=p2')
    expect(h.seen.every(id => id === 'p2')).toBe(true)
  })

  it('replaces the history entry, so Back leaves the panel', async () => {
    renderAt(['/before', '/admin'])
    await screen.findByText('back')
    fireEvent.click(screen.getByText('back'))
    expect(await screen.findByTestId('where')).toHaveTextContent('/before')
  })

  it('never pins a power admin', async () => {
    h.auth = { isPowerAdmin: true, adminProjectIds: [], user: { first_name: 'P', last_name: 'A' } }
    renderAt(['/admin'])
    expect(await screen.findByTestId('where')).toHaveTextContent(/^\/admin$/)
    expect(h.seen.every(id => id === null)).toBe(true)
  })
})
