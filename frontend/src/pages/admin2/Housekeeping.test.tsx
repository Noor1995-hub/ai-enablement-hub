// B6 housekeeping UI: the Move dialog, the delete dialog, and the Projects page
// scope reset after deleting the scoped project.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MoveUserDialog from './MoveUserDialog'
import OrgDeleteDialog from './OrgDeleteDialog'
import ProjectsPage from './ProjectsPage'

const h = vi.hoisted(() => ({ auth: { isPowerAdmin: true, adminProjectIds: [] as string[], user: { id: 'me' } } }))
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => h.auth }))

const clientMock = vi.hoisted(() => ({ GET: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn(), POST: vi.fn() }))
vi.mock('../../api/client', async importOriginal => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, client: clientMock }
})

const COMPANIES = [
  {
    id: 'c1',
    name: 'Acme',
    projects: [
      { id: 'p1', name: 'Rollout', company_id: 'c1', created_at: '2026-01-01T00:00:00Z' },
      { id: 'p2', name: 'Pilot', company_id: 'c1', created_at: '2026-01-01T00:00:00Z' },
    ],
  },
]
const IMPACT = { projects: 0, users_deleted: 14, power_admins_kept: 1, project_admin_grants: 2, users_with_progress: 12, other_project_admins_deleted: 0 }

function wrap(node: ReactNode, url = '/admin/projects') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>{node}</MemoryRouter>
    </QueryClientProvider>,
  )
}

function LocationProbe() {
  return <span data-testid="search">{useLocation().search}</span>
}

describe('B6 housekeeping', () => {
  beforeEach(() => {
    for (const fn of Object.values(clientMock)) fn.mockReset()
    clientMock.GET.mockImplementation((path: string) => {
      if (path === '/api/admin/companies') return Promise.resolve({ data: { companies: structuredClone(COMPANIES) } })
      if (path.endsWith('/impact')) return Promise.resolve({ data: IMPACT })
      // Project card children (settings toggles, admins) — any harmless empty answer.
      return Promise.resolve({ data: { components: {}, settings: {}, admins: [] } })
    })
    for (const fn of [clientMock.PUT, clientMock.PATCH, clientMock.DELETE]) {
      fn.mockResolvedValue({ data: undefined, error: undefined })
    }
  })

  it('moves a user and warns about a grant on the destination', async () => {
    const onClose = vi.fn()
    wrap(<MoveUserDialog userId="u1" currentProjectId="p1" holdsGrantOn={['p2']} onClose={onClose} />)

    await screen.findByRole('option', { name: 'Acme · Pilot' })
    fireEvent.change(screen.getByLabelText('New project'), { target: { value: 'p2' } })
    expect(screen.getByText(/administers this project/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    await waitFor(() =>
      expect(clientMock.PUT).toHaveBeenCalledWith('/api/admin/users/{user_id}/project', {
        params: { path: { user_id: 'u1' } },
        body: { project_id: 'p2' },
      }),
    )
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  it('shows the impact and needs two clicks to delete', async () => {
    const onDeleted = vi.fn()
    wrap(<OrgDeleteDialog kind="project" id="p1" name="Rollout" onClose={vi.fn()} onDeleted={onDeleted} />)

    expect(
      await screen.findByText(
        'Deletes Rollout, its 14 users (12 with progress) with their assessments and interviews, its settings and email templates, and 2 project-admin grants. 1 power admin in it keeps their account.',
      ),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Delete project' }))
    expect(clientMock.DELETE).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))

    await waitFor(() =>
      expect(clientMock.DELETE).toHaveBeenCalledWith('/api/admin/projects/{project_id}', {
        params: { path: { project_id: 'p1' } },
      }),
    )
    await waitFor(() => expect(onDeleted).toHaveBeenCalled())
  })

  it('resets the scope when the scoped project is deleted', async () => {
    wrap(<><ProjectsPage /><LocationProbe /></>, '/admin/projects?project=p1')

    // [0] is the Companies card's; [1] is the (scoped) project card's.
    fireEvent.click((await screen.findAllByRole('button', { name: 'Delete…' }))[1])
    fireEvent.click(await screen.findByRole('button', { name: 'Delete project' }))
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))

    await waitFor(() => expect(screen.getByTestId('search').textContent).not.toContain('project=p1'))
  })
  it('re-fetches the impact every time the delete dialog opens', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30_000 } } })
    const dialog = (key: string) => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <OrgDeleteDialog key={key} kind="project" id="p1" name="Rollout" onClose={vi.fn()} onDeleted={vi.fn()} />
        </MemoryRouter>
      </QueryClientProvider>
    )
    const { rerender, unmount } = render(dialog('a'))
    expect(await screen.findByText(/its 14 users/)).toBeInTheDocument()
    unmount()

    clientMock.GET.mockImplementation((path: string) =>
      Promise.resolve({ data: path.endsWith('/impact') ? { ...IMPACT, users_deleted: 40 } : { companies: [] } }),
    )
    render(dialog('b'))
    expect(await screen.findByText(/its 40 users/)).toBeInTheDocument()
    expect(screen.queryByText(/its 14 users/)).toBeNull()
    void rerender
  })
})
