import { describe, expect, it } from 'vitest'
import type { ContentBlock } from '../types/contentBlocks'
import { BLOCK_NOUNS, parseConflict, removalSummary } from './lessonSave'
import { BLOCK_FACTORIES, BLOCK_LABELS } from './contentBlocks'

const b = (type: ContentBlock['type'], id: string): ContentBlock => ({ ...BLOCK_FACTORIES[type](), id })

describe('removalSummary', () => {
  it('names what a save would remove', () => {
    const before = [b('quiz', '1'), b('card_group', '2'), b('paragraph', '3')]
    const after = [b('paragraph', '3')]
    expect(removalSummary(before, after)).toBe('This removes 1 quiz and 1 card group.')
  })
  it('is null when nothing is lost (additions and reorders are fine)', () => {
    expect(removalSummary([b('quiz', '1')], [b('paragraph', '9'), b('quiz', '1')])).toBeNull()
  })
  it('counts per type, plural', () => {
    expect(removalSummary([b('paragraph', '1'), b('paragraph', '2')], [])).toBe('This removes 2 paragraphs.')
  })
})

describe('parseConflict', () => {
  it('reads a lesson_changed 409 body', () => {
    expect(parseConflict({ error: { code: 'lesson_changed', message: 'm', updated_at: '2026-10-05T14:32:00+00:00', updated_by_name: 'Aaron Neuville' } }))
      .toEqual({ updatedAt: '2026-10-05T14:32:00+00:00', updatedByName: 'Aaron Neuville' })
  })
  it('ignores any other error', () => {
    expect(parseConflict({ error: { code: 'conflict', message: 'm' } })).toBeNull()
    expect(parseConflict(undefined)).toBeNull()
  })
})

describe('BLOCK_NOUNS', () => {
  it('has a noun for every block type', () => {
    expect(Object.keys(BLOCK_NOUNS).sort()).toEqual(Object.keys(BLOCK_LABELS).sort())
  })
  it('pluralises quizzes', () => {
    expect(removalSummary([b('quiz', '1'), b('quiz', '2')], [])).toBe('This removes 2 quizzes.')
  })
})
