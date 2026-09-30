import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AdminLearningUserEnriched, Track } from '../../types/domain'
import Matrix from './Matrix'
import type { LearningLesson, LearningModule } from './matrixCells'

// TanStack v5 hands back a NEW result object on every render; only `mutate` is
// stable. The mock reproduces that (fresh object per call) so these tests fail
// if the row click handler depends on the whole mutation object.
const mutate = vi.hoisted(() => vi.fn())
vi.mock('./api', () => ({
  useToggleAssignment: () => ({ mutate, isError: false, error: null }),
  useSetDefaults: () => ({ mutate: vi.fn(), isError: false, isPending: false, error: null }),
  useApplyDefaults: () => ({ mutate: vi.fn(), isError: false, isPending: false, error: null }),
}))

// Spy on the per-cell derivation: it runs once per cell each time a row renders.
const derive = vi.hoisted(() => vi.fn())
vi.mock('./matrixCells', async importOriginal => {
  const actual = await importOriginal<typeof import('./matrixCells')>()
  derive.mockImplementation(actual.deriveCellState)
  return { ...actual, deriveCellState: derive }
})

const tracks: Track[] = [
  { id: 't1', name: 'Track One', sort_order: 1, track_type: 'general', color: null, required_level: 'explore', is_introduction: false },
  { id: 't2', name: 'Track Two', sort_order: 2, track_type: 'general', color: null, required_level: 'explore', is_introduction: false },
]
const modules: LearningModule[] = []
const lessons: LearningLesson[] = []
const level = { level: 'tracks' } as const
const defaultTrackIds: string[] = []

function makeUser(id: string, overrides: Partial<AdminLearningUserEnriched> = {}): AdminLearningUserEnriched {
  return {
    id,
    first_name: id,
    last_name: 'Tester',
    project_name: null,
    company_name: null,
    assigned_track_ids: [],
    assigned_module_ids: [],
    assigned_lesson_ids: [],
    default_track_ids: [],
    default_module_ids: [],
    default_lesson_ids: [],
    ...overrides,
  }
}

function matrix(users: AdminLearningUserEnriched[]) {
  return (
    <Matrix
      projectId="p1"
      level={level}
      onSelect={vi.fn()}
      tracks={tracks}
      modules={modules}
      lessons={lessons}
      users={users}
      defaultTrackIds={defaultTrackIds}
    />
  )
}

describe('Matrix', () => {
  beforeEach(() => {
    mutate.mockClear()
    derive.mockClear()
  })

  it('derives every cell once on first render', () => {
    render(matrix([makeUser('a'), makeUser('b'), makeUser('c')]))
    expect(derive).toHaveBeenCalledTimes(3 * tracks.length)
  })

  it('re-derives only the changed row when one user object is replaced', () => {
    const a = makeUser('a')
    const c = makeUser('c')
    const { rerender } = render(matrix([a, makeUser('b'), c]))
    derive.mockClear()

    // What the optimistic patch does: a new object for the toggled user only.
    rerender(matrix([a, makeUser('b', { assigned_track_ids: ['t1'] }), c]))

    expect(derive).toHaveBeenCalledTimes(tracks.length)
    expect(derive.mock.calls.every(call => call[2].id === 'b')).toBe(true)
  })

  it('re-derives nothing when Matrix re-renders with unchanged data', () => {
    const users = [makeUser('a'), makeUser('b')]
    const { rerender } = render(matrix(users))
    derive.mockClear()
    rerender(matrix(users))
    expect(derive).not.toHaveBeenCalled()
  })

  it('a click toggles the right user, item and direction', () => {
    render(matrix([makeUser('a'), makeUser('b', { assigned_track_ids: ['t2'] })]))
    const rows = screen.getAllByRole('row')
    const rowA = rows.find(r => within(r).queryByText('a Tester'))!
    const rowB = rows.find(r => within(r).queryByText('b Tester'))!

    fireEvent.click(within(rowA).getAllByRole('button')[0]) // empty cell: assign t1
    expect(mutate).toHaveBeenLastCalledWith({ userId: 'a', kind: 'track', id: 't1', assigned: true })

    fireEvent.click(within(rowB).getAllByRole('button')[1]) // assigned cell: unassign t2
    expect(mutate).toHaveBeenLastCalledWith({ userId: 'b', kind: 'track', id: 't2', assigned: false })
  })
})
