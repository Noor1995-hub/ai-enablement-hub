import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ContentPage from './ContentPage'

const h = vi.hoisted(() => ({ auth: { isPowerAdmin: true } }))
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => h.auth }))

const clientMock = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }))
vi.mock('../../api/client', async importOriginal => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, client: clientMock }
})

const TREE = [
  {
    id: 't1', name: 'General I', color: null, track_type: 'general', required_level: 'explore',
    is_introduction: false, sort_order: 0,
    modules: [
      { id: 'm1', title: 'Why AI now', description: null, sort_order: 0, prerequisite_ids: [], lesson_count: 0, lessons: [] },
      { id: 'm2', title: 'Prompting basics', description: null, sort_order: 1, prerequisite_ids: ['m1'], lesson_count: 1,
        lessons: [{ id: 'l1', title: 'Ask clearly', sort_order: 0 }] },
    ],
  },
  { id: 't2', name: 'Empty track', color: null, track_type: 'tool', required_level: 'integrator', is_introduction: false, sort_order: 1, modules: [] },
]

function renderPage(search = '') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/admin/content${search}`]}>
        <ContentPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ContentPage', () => {
  beforeEach(() => {
    h.auth = { isPowerAdmin: true }
    for (const fn of Object.values(clientMock)) fn.mockReset()
    clientMock.GET.mockImplementation((path: string) => {
      if (path === '/api/admin/content/tree') return Promise.resolve({ data: { tracks: structuredClone(TREE) } })
      if (path.endsWith('/assignment-gap')) return Promise.resolve({ data: { lesson_ids: ['l1'], learner_count: 14, missing_pairs: 14 } })
      if (path.endsWith('/impact')) return Promise.resolve({ data: { modules: 0, lessons: 1, learners_assigned: 3, learners_with_progress: 2 } })
      return Promise.resolve({ data: undefined, error: { error: { code: 'x', message: 'unexpected' } } })
    })
    for (const fn of [clientMock.POST, clientMock.PUT, clientMock.PATCH, clientMock.DELETE]) {
      fn.mockResolvedValue({ data: {}, error: undefined })
    }
  })

  it('renders an empty track', async () => {
    renderPage()
    expect(await screen.findByText('Empty track')).toBeInTheDocument()
    expect(screen.getByText('0 · 0')).toBeInTheDocument()
  })

  it('moves a module down with one reorder call', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByRole('button', { name: 'Move Why AI now down' }))
    await waitFor(() =>
      expect(clientMock.PUT).toHaveBeenCalledWith('/api/admin/tracks/{track_id}/modules/order', {
        params: { path: { track_id: 't1' } },
        body: { module_ids: ['m2', 'm1'] },
      }),
    )
  })

  it('renames a module from the detail panel', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    const title = await screen.findByLabelText('Title')
    fireEvent.change(title, { target: { value: 'Prompting 101' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(clientMock.PATCH).toHaveBeenCalledWith('/api/admin/modules/{module_id}', {
        params: { path: { module_id: 'm2' } },
        body: { title: 'Prompting 101', description: null },
      }),
    )
  })

  it('shows the impact before a two-step delete', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    expect(await screen.findByText('Deletes 1 lesson and the progress of 2 learners.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Delete module' }))
    expect(clientMock.DELETE).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))
    await waitFor(() =>
      expect(clientMock.DELETE).toHaveBeenCalledWith('/api/admin/modules/{module_id}', { params: { path: { module_id: 'm2' } } }),
    )
  })

  it('gives a project admin a read-only tree plus the project-scoped assign button', async () => {
    h.auth = { isPowerAdmin: false }
    renderPage('?project=p1')
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    const panel = await screen.findByRole('region', { name: 'Prompting basics' })
    expect(within(panel).queryByLabelText('Title')).toBeNull()
    expect(screen.queryByRole('button', { name: /^Move / })).toBeNull()
    expect(screen.queryByRole('button', { name: '+ Track' })).toBeNull()
    fireEvent.click(await within(panel).findByRole('button', { name: 'Assign to the 14 learners' }))
    await waitFor(() =>
      expect(clientMock.POST).toHaveBeenCalledWith(
        '/api/admin/projects/{project_id}/modules/{module_id}/assign-new-lessons',
        { params: { path: { project_id: 'p1', module_id: 'm2' } } },
      ),
    )
  })
  it('shows a refused prerequisite save in the panel', async () => {
    clientMock.PUT.mockImplementation((path: string) =>
      path === '/api/admin/modules/{module_id}/prerequisites'
        ? Promise.resolve({ data: undefined, error: { error: { code: 'invalid_request', message: 'This would make "Why AI now" depend on itself.' } } })
        : Promise.resolve({ data: {}, error: undefined }),
    )
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Why AI now'))
    fireEvent.click(await screen.findByRole('button', { name: 'Save prerequisites' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This would make "Why AI now" depend on itself.')
  })

  it('does not offer the lesson editor to a project admin', async () => {
    h.auth = { isPowerAdmin: false }
    renderPage('?project=p1')
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    fireEvent.click(await screen.findByText('Ask clearly'))
    const panel = await screen.findByRole('region', { name: 'Ask clearly' })
    expect(within(panel).queryByRole('link', { name: 'Edit content' })).toBeNull()
  })

  it('keeps a selected track open when its name is clicked again; the arrow collapses it', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('General I'))
    expect(screen.getByText('Why AI now')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Collapse General I' }))
    expect(screen.queryByText('Why AI now')).toBeNull()
  })

  it('keeps unsaved typing when the tree refetches', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    const title = await screen.findByLabelText('Title')
    fireEvent.change(title, { target: { value: 'Half-typed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Move Why AI now down' }))
    await waitFor(() => expect(clientMock.GET.mock.calls.filter(c => c[0] === '/api/admin/content/tree').length).toBeGreaterThan(1))
    expect(screen.getByLabelText('Title')).toHaveValue('Half-typed')
  })
})
