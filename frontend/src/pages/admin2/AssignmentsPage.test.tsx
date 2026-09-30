import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AssignmentsPage from './AssignmentsPage'

// Integration-style: the REAL query hooks and the REAL optimistic `onMutate`
// cache patch run; only the HTTP client is stubbed. Responses are fresh JSON
// copies each time, like a real fetch, so only TanStack's structural sharing can
// keep references stable across a refetch.
const server = vi.hoisted(() => ({
  learning: {} as Record<string, unknown>,
  puts: [] as string[],
}))
const clientMock = vi.hoisted(() => ({ GET: vi.fn(), PUT: vi.fn() }))
vi.mock('../../api/client', async importOriginal => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, client: clientMock }
})

// Spy on the per-cell derivation: it runs once per cell each time a row renders.
const derive = vi.hoisted(() => vi.fn())
vi.mock('./matrixCells', async importOriginal => {
  const actual = await importOriginal<typeof import('./matrixCells')>()
  derive.mockImplementation(actual.deriveCellState)
  return { ...actual, deriveCellState: derive }
})

const json = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function user(id: string) {
  return {
    id,
    first_name: id,
    last_name: 'Tester',
    project_name: null,
    company_name: null,
    assigned_track_ids: [] as string[],
    assigned_module_ids: [] as string[],
    assigned_lesson_ids: [] as string[],
    default_track_ids: [] as string[],
    default_module_ids: [] as string[],
    default_lesson_ids: [] as string[],
  }
}

function track(id: string, sort_order: number) {
  return {
    id,
    name: `Track ${id}`,
    sort_order,
    track_type: 'general',
    color: null,
    required_level: 'explore',
    is_introduction: false,
  }
}

describe('AssignmentsPage', () => {
  beforeEach(() => {
    derive.mockClear()
    server.puts = []
    server.learning = {
      modules: [{ id: 'm1', track_id: 't1', title: 'M1', sort_order: 1 }],
      lessons: [{ id: 'l1', module_id: 'm1', title: 'L1', sort_order: 1 }],
      users: [user('a'), user('b'), user('c')],
      total: 3,
    }
    clientMock.GET.mockImplementation((path: string, opts?: { params: { path: Record<string, string> } }) => {
      if (path === '/api/tracks') return Promise.resolve({ data: json([track('t1', 1), track('t2', 2)]) })
      if (path === '/api/admin/learning') return Promise.resolve({ data: json(server.learning) })
      if (path === '/api/admin/companies') return Promise.resolve({ data: { companies: [] } })
      if (path === '/api/admin/projects/p1/defaults') return Promise.resolve({ data: { track_ids: [] } })
      // Template path for the typed client (phase E, E15)
      if (path === '/api/admin/projects/{project_id}/defaults' && opts?.params.path.project_id === 'p1') return Promise.resolve({ data: { track_ids: [] } })
      return Promise.reject(new Error(`unexpected GET ${path}`))
    })
    clientMock.PUT.mockImplementation((path: string, opts: { params: { path: Record<string, string> } }) => {
      server.puts.push(`${path} ${JSON.stringify(opts.params.path)}`)
      // The server applies the toggle, so the post-mutation refetch agrees with the optimistic patch.
      const users = server.learning.users as ReturnType<typeof user>[]
      users.find(u => u.id === opts.params.path.user_id)!.assigned_track_ids.push(opts.params.path.track_id)
      return Promise.resolve({ error: undefined })
    })
  })

  it('a cell click re-derives only the toggled user, even through the refetch', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin/assignments?project=p1']}>
          <AssignmentsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const rowB = (await screen.findByText('b Tester')).closest('tr')!
    // 3 users x 2 track columns.
    await waitFor(() => expect(derive).toHaveBeenCalledTimes(6))
    derive.mockClear()
    const learningGets = () => clientMock.GET.mock.calls.filter(call => call[0] === '/api/admin/learning').length
    const before = learningGets()

    fireEvent.click(within(rowB).getAllByRole('button')[0])

    // Optimistic patch, PUT, then the invalidation refetch all complete.
    await waitFor(() => expect(learningGets()).toBeGreaterThan(before))
    await waitFor(() => expect(server.puts).toHaveLength(1))
    await waitFor(() => expect(within(rowB).getAllByRole('button')[0]).toHaveClass('adm-cell-yes'))
    await new Promise(resolve => setTimeout(resolve, 50))

    expect(derive).toHaveBeenCalled()
    expect(derive.mock.calls.every(call => call[2].id === 'b')).toBe(true)
  })
})
