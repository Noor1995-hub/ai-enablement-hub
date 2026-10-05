import { describe, expect, it } from 'vitest'
import { filterTree, gapLabel, impactLabel, moveInList, type TreeTrack } from './contentTree'

const tree: TreeTrack[] = [
  {
    id: 't1', name: 'General I', color: null, track_type: 'general', required_level: 'explore',
    is_introduction: false, sort_order: 0,
    modules: [
      { id: 'm1', title: 'Prompting basics', description: null, sort_order: 0, prerequisite_ids: [], lesson_count: 1,
        lessons: [{ id: 'l1', title: 'Ask clearly', sort_order: 0 }] },
      { id: 'm2', title: 'Checking output', description: null, sort_order: 1, prerequisite_ids: [], lesson_count: 0, lessons: [] },
    ],
  },
  {
    id: 't2', name: 'Copilot I', color: null, track_type: 'tool', required_level: 'integrator',
    is_introduction: false, sort_order: 1, modules: [],
  },
]

describe('filterTree', () => {
  it('returns everything for an empty query', () => {
    expect(filterTree(tree, '  ')).toBe(tree)
  })
  it('keeps a matching lesson with its module and track only', () => {
    const result = filterTree(tree, 'ASK')
    expect(result.map(t => t.id)).toEqual(['t1'])
    expect(result[0].modules.map(m => m.id)).toEqual(['m1'])
    expect(result[0].modules[0].lessons.map(l => l.id)).toEqual(['l1'])
  })
  it('keeps a matching track whole', () => {
    expect(filterTree(tree, 'copilot').map(t => t.id)).toEqual(['t2'])
  })
})

describe('moveInList', () => {
  it('swaps with the neighbour', () => {
    expect(moveInList(['a', 'b', 'c'], 'b', -1)).toEqual(['b', 'a', 'c'])
    expect(moveInList(['a', 'b', 'c'], 'b', 1)).toEqual(['a', 'c', 'b'])
  })
  it('returns null at an edge or for an unknown id', () => {
    expect(moveInList(['a', 'b'], 'a', -1)).toBeNull()
    expect(moveInList(['a', 'b'], 'b', 1)).toBeNull()
    expect(moveInList(['a'], 'x', 1)).toBeNull()
  })
})

describe('labels', () => {
  it('spells out a delete impact', () => {
    expect(impactLabel({ modules: 3, lessons: 21, learners_assigned: 20, learners_with_progress: 14 }))
      .toBe('Deletes 3 modules, 21 lessons and the progress of 14 learners.')
    expect(impactLabel({ modules: 0, lessons: 1, learners_assigned: 0, learners_with_progress: 0 }))
      .toBe('Deletes 1 lesson. No learner has progress on it.')
  })
  it('describes the assignment gap, or nothing when there is none', () => {
    expect(gapLabel({ lesson_ids: ['l9'], learner_count: 14, missing_pairs: 14 }))
      .toBe('1 lesson not yet assigned to the 14 learners who have this module.')
    expect(gapLabel({ lesson_ids: [], learner_count: 0, missing_pairs: 0 })).toBeNull()
  })
})
