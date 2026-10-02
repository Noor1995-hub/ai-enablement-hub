import { describe, expect, it } from 'vitest'
import {
  isIntroComplete,
  isModuleDone,
  isModuleUnlocked,
  isPrereqSatisfied,
  type LockContext,
  type LockModule,
} from './learningPathLocks'

// Level ranks as in lib/levels.ts LEVELS: explore 0, practitioner 1, integrator 2, multiplier 3.
const EXPLORE = 0
const PRACTITIONER = 1

function mod(id: string, over: Partial<LockModule> = {}): LockModule {
  return {
    id,
    lesson_count: 3,
    completed_lesson_count: 0,
    unlocked_by_maturity: true,
    is_introduction: false,
    ...over,
  }
}

/** A learner at `levelIdx` with the given modules; prereqs as [dependent, prerequisite] pairs. */
function ctx(
  modules: LockModule[],
  opts: {
    prereqs?: [string, string][]
    rank?: Record<string, number>
    levelIdx?: number
    canBypassLocks?: boolean
    introComplete?: boolean
  } = {},
): LockContext {
  const prereqMap = new Map<string, string[]>()
  for (const [dep, pre] of opts.prereqs ?? []) prereqMap.set(dep, [...(prereqMap.get(dep) ?? []), pre])
  return {
    canBypassLocks: opts.canBypassLocks ?? false,
    moduleById: new Map(modules.map(m => [m.id, m])),
    prereqMap,
    moduleLevelRank: new Map(Object.entries(opts.rank ?? {})),
    levelIdx: opts.levelIdx ?? EXPLORE,
    introComplete: opts.introComplete ?? true,
  }
}

describe('isModuleDone', () => {
  it('is done when every lesson is completed', () => {
    expect(isModuleDone(mod('a', { completed_lesson_count: 3 }))).toBe(true)
    expect(isModuleDone(mod('a', { completed_lesson_count: 2 }))).toBe(false)
  })
  it('is never done with 0 lessons (accepted quirk: 0/0 locks dependents forever)', () => {
    expect(isModuleDone(mod('a', { lesson_count: 0, completed_lesson_count: 0 }))).toBe(false)
  })
  it('is not done when the module is unknown', () => {
    expect(isModuleDone(undefined)).toBe(false)
  })
})

describe('isIntroComplete', () => {
  const intro = { id: 't-intro', is_introduction: true }
  const other = { id: 't-gen', is_introduction: false }
  it('is complete when every Introduction lesson is done', () => {
    const mods = { 't-intro': [mod('i1', { completed_lesson_count: 3 })] }
    expect(isIntroComplete([intro, other], mods)).toBe(true)
  })
  it('is incomplete while an Introduction lesson is open', () => {
    const mods = { 't-intro': [mod('i1', { completed_lesson_count: 1 })] }
    expect(isIntroComplete([intro, other], mods)).toBe(false)
  })
  it('an EMPTY Introduction leaves the gate open', () => {
    expect(isIntroComplete([intro], { 't-intro': [mod('i1', { lesson_count: 0 })] })).toBe(true)
    expect(isIntroComplete([other], {})).toBe(true)
  })
  it('an over-completed module cannot make up for an unfinished one', () => {
    const mods = {
      't-intro': [mod('i1', { completed_lesson_count: 5 }), mod('i2', { completed_lesson_count: 0 })],
    }
    expect(isIntroComplete([intro], mods)).toBe(false)
  })
  it('ignores non-Introduction tracks', () => {
    const mods = { 't-gen': [mod('g1', { completed_lesson_count: 0 })] }
    expect(isIntroComplete([other], mods)).toBe(true)
  })
})

describe('isModuleUnlocked', () => {
  it('a caller who bypasses locks passes every lock', () => {
    const locked = mod('a', { unlocked_by_maturity: false })
    const c = ctx([locked, mod('p')], { prereqs: [['a', 'p']], introComplete: false })
    expect(isModuleUnlocked(c, 'a')).toBe(false)
    expect(isModuleUnlocked({ ...c, canBypassLocks: true }, 'a')).toBe(true)
  })

  it('a track above the learner level locks its modules (unlocked_by_maturity false)', () => {
    expect(isModuleUnlocked(ctx([mod('a', { unlocked_by_maturity: false })]), 'a')).toBe(false)
    expect(isModuleUnlocked(ctx([mod('a', { unlocked_by_maturity: true })]), 'a')).toBe(true)
  })

  it('the Introduction gate locks everything outside the Introduction until it is complete', () => {
    const general = mod('g')
    const introMod = mod('i', { is_introduction: true })
    const gated = ctx([general, introMod], { introComplete: false })
    expect(isModuleUnlocked(gated, 'g')).toBe(false)
    expect(isModuleUnlocked(gated, 'i')).toBe(true)
    expect(isModuleUnlocked({ ...gated, introComplete: true }, 'g')).toBe(true)
  })

  it('a module with no prerequisites is unlocked', () => {
    expect(isModuleUnlocked(ctx([mod('a')]), 'a')).toBe(true)
  })

  it('a same-level prerequisite gates until it is done', () => {
    const rank = { a: EXPLORE, p: EXPLORE }
    const open = ctx([mod('a'), mod('p', { completed_lesson_count: 1 })], { prereqs: [['a', 'p']], rank })
    expect(isModuleUnlocked(open, 'a')).toBe(false)
    const done = ctx([mod('a'), mod('p', { completed_lesson_count: 3 })], { prereqs: [['a', 'p']], rank })
    expect(isModuleUnlocked(done, 'a')).toBe(true)
  })

  it('every prerequisite must be satisfied, not just one', () => {
    const rank = { a: EXPLORE, p1: EXPLORE, p2: EXPLORE }
    const c = ctx([mod('a'), mod('p1', { completed_lesson_count: 3 }), mod('p2')], {
      prereqs: [['a', 'p1'], ['a', 'p2']],
      rank,
    })
    expect(isModuleUnlocked(c, 'a')).toBe(false)
  })

  it('a prerequisite with 0 lessons locks its dependent forever (accepted quirk)', () => {
    const c = ctx([mod('a'), mod('p', { lesson_count: 0 })], {
      prereqs: [['a', 'p']],
      rank: { a: EXPLORE, p: EXPLORE },
    })
    expect(isModuleUnlocked(c, 'a')).toBe(false)
  })

  it('a track strictly below the learner level is freely reviewable, prerequisites bypassed', () => {
    const c = ctx([mod('a'), mod('p')], {
      prereqs: [['a', 'p']],
      rank: { a: EXPLORE, p: EXPLORE },
      levelIdx: PRACTITIONER,
    })
    expect(isModuleUnlocked(c, 'a')).toBe(true)
    expect(isModuleUnlocked({ ...c, levelIdx: EXPLORE }, 'a')).toBe(false)
  })

  it('a prerequisite in a strictly lower level is satisfied by maturity alone (cross-track edge)', () => {
    // A tool-track first module at Practitioner depending on the last General module at Explorer.
    const c = ctx([mod('tool1'), mod('gen-last')], {
      prereqs: [['tool1', 'gen-last']],
      rank: { tool1: PRACTITIONER, 'gen-last': EXPLORE },
      levelIdx: PRACTITIONER,
    })
    expect(isModuleUnlocked(c, 'tool1')).toBe(true)
    expect(isPrereqSatisfied(c, 'gen-last', 'tool1')).toBe(true)
    // Same edge at the same level: completion is required again.
    const sameLevel = { ...c, moduleLevelRank: new Map([['tool1', EXPLORE], ['gen-last', EXPLORE]]) }
    expect(isPrereqSatisfied(sameLevel, 'gen-last', 'tool1')).toBe(false)
  })

  it('the maturity and Introduction gates win over the below-level review shortcut', () => {
    // A below-level module (rank < levelIdx) is still locked by either gate: the shortcut only
    // applies once both gates have passed.
    const rank = { a: EXPLORE }
    const introOpen = ctx([mod('a')], { rank, levelIdx: PRACTITIONER, introComplete: false })
    expect(isModuleUnlocked(introOpen, 'a')).toBe(false)
    const maturityLocked = ctx([mod('a', { unlocked_by_maturity: false })], { rank, levelIdx: PRACTITIONER })
    expect(isModuleUnlocked(maturityLocked, 'a')).toBe(false)
  })

  it('an unranked prerequisite falls back to completion', () => {
    const c = ctx([mod('a'), mod('p')], { prereqs: [['a', 'p']], rank: { a: PRACTITIONER } })
    expect(isPrereqSatisfied(c, 'p', 'a')).toBe(false)
  })
})
