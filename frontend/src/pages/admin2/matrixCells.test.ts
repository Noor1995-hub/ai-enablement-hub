import { describe, expect, it } from 'vitest'
import type { AdminLearningUserEnriched } from '../../types/domain'
import { buildChildIdIndex, deriveCellState } from './matrixCells'
import type { LearningLesson, LearningModule } from './matrixCells'

const modules: LearningModule[] = [
  { id: 'm1', track_id: 't1', title: 'M1', sort_order: 1 },
  { id: 'm2', track_id: 't1', title: 'M2', sort_order: 2 },
  { id: 'm3', track_id: 't2', title: 'M3', sort_order: 1 },
]
const lessons: LearningLesson[] = [
  { id: 'l1', module_id: 'm1', title: 'L1', sort_order: 1 },
  { id: 'l2', module_id: 'm1', title: 'L2', sort_order: 2 },
]

function user(overrides: Partial<AdminLearningUserEnriched> = {}): AdminLearningUserEnriched {
  return {
    id: 'u1',
    first_name: 'Ada',
    last_name: 'Lovelace',
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

describe('buildChildIdIndex', () => {
  it('groups module ids by track and lesson ids by module, in input order', () => {
    const index = buildChildIdIndex(modules, lessons)
    expect(index.byTrack.get('t1')).toEqual(['m1', 'm2'])
    expect(index.byTrack.get('t2')).toEqual(['m3'])
    expect(index.byModule.get('m1')).toEqual(['l1', 'l2'])
    expect(index.byModule.get('m2')).toBeUndefined()
  })
})

describe('deriveCellState', () => {
  const index = buildChildIdIndex(modules, lessons)

  it('is yes when explicitly assigned, def when also a project default', () => {
    const u = user({ assigned_track_ids: ['t1', 't2'], default_track_ids: ['t2'] })
    expect(deriveCellState('track', 't1', u, index)).toBe('yes')
    expect(deriveCellState('track', 't2', u, index)).toBe('def')
  })

  it('is part for a track with some but not all modules assigned', () => {
    expect(deriveCellState('track', 't1', user({ assigned_module_ids: ['m1'] }), index)).toBe('part')
  })

  it('is empty for a track with no or all modules assigned but the track itself not', () => {
    expect(deriveCellState('track', 't1', user(), index)).toBe('')
    expect(deriveCellState('track', 't1', user({ assigned_module_ids: ['m1', 'm2'] }), index)).toBe('')
  })

  it('is part for a module with some but not all lessons assigned', () => {
    expect(deriveCellState('module', 'm1', user({ assigned_lesson_ids: ['l2'] }), index)).toBe('part')
  })

  it('is empty for a module without lessons, and lessons never show part', () => {
    expect(deriveCellState('module', 'm2', user({ assigned_lesson_ids: ['l1'] }), index)).toBe('')
    expect(deriveCellState('lesson', 'l1', user(), index)).toBe('')
  })

  it('reads the arrays matching the kind', () => {
    const u = user({ assigned_module_ids: ['m1'], default_module_ids: ['m1'], assigned_lesson_ids: ['l1'] })
    expect(deriveCellState('module', 'm1', u, index)).toBe('def')
    expect(deriveCellState('lesson', 'l1', u, index)).toBe('yes')
    expect(deriveCellState('lesson', 'l2', u, index)).toBe('')
  })
})
