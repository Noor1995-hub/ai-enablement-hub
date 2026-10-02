/**
 * The learning-path module unlock rule, as pure functions (moved verbatim out of
 * LearningPathNew.tsx so it can be tested — see learningPathLocks.test.ts and CLAUDE.md
 * "Locking, prerequisites & preview"). This is a VISIBILITY rule, not access control: the
 * server serves any lesson of an unlocked `learning` component regardless.
 */
import type { ModuleNode, TrackNode } from '../types/domain'

export type LockModule = Pick<
  ModuleNode,
  'id' | 'lesson_count' | 'completed_lesson_count' | 'unlocked_by_maturity' | 'is_introduction'
>
export type LockTrack = Pick<TrackNode, 'id' | 'is_introduction'>

export interface LockContext {
  /** Server-resolved (GET /api/me bypasses_locks): power admins, and project
   * admins on their own project (spec 2026-10-01-project-scoped-admin). */
  canBypassLocks: boolean
  moduleById: Map<string, LockModule>
  /** module_id → its ASSIGNED prerequisite module ids. */
  prereqMap: Map<string, string[]>
  /** module_id → maturity-level rank of its track, over the FULL graph (assigned or not). */
  moduleLevelRank: Map<string, number>
  /** The learner's effective level index, a missing level clamped to Explorer (0). */
  levelIdx: number
  introComplete: boolean
}

export function isModuleDone(mod: LockModule | undefined): boolean {
  return !!mod && mod.lesson_count > 0 && mod.completed_lesson_count >= mod.lesson_count
}

// Introduction gate: the pre-Explorer track(s) must be finished before any
// other track unlocks. Lesson-based (matches the group bar) with the guard
// that an EMPTY Introduction (no lessons yet) leaves the gate OPEN, so
// shipping the empty track changes nothing until content is published.
export function isIntroComplete(
  tracks: LockTrack[],
  modulesByTrack: Record<string, LockModule[]>,
): boolean {
  const introMods = tracks
    .filter(t => t.is_introduction)
    .flatMap(t => modulesByTrack[t.id] ?? [])
  const total = introMods.reduce((n, m) => n + m.lesson_count, 0)
  const done = introMods.reduce(
    (n, m) => n + Math.min(m.completed_lesson_count, m.lesson_count),
    0,
  )
  return total === 0 || done >= total
}

// A prerequisite is satisfied either by completion, OR — when it points into a
// strictly-lower maturity level than the dependent module's track — by the
// learner's maturity alone. isModuleUnlocked only reaches the prereq check for a
// maturity-unlocked module, so its effective level already covers every
// lower-level track; re-gating on those cross-track (general → tool) edges
// would block a pinned/skip-ahead learner on general modules the ladder never
// required them to walk. Same-track and same-level prerequisites still gate.
export function isPrereqSatisfied(ctx: LockContext, predId: string, dependentId: string): boolean {
  const myRank = ctx.moduleLevelRank.get(dependentId)
  const pRank = ctx.moduleLevelRank.get(predId)
  if (myRank !== undefined && pRank !== undefined && pRank < myRank) return true
  return isModuleDone(ctx.moduleById.get(predId))
}

export function isModuleUnlocked(ctx: LockContext, id: string): boolean {
  if (ctx.canBypassLocks) return true // same rule as the server's lesson gate
  const mod = ctx.moduleById.get(id)
  if (mod?.unlocked_by_maturity === false) return false
  // Introduction gate: modules OUTSIDE the Introduction track stay locked
  // until the Introduction is complete.
  if (mod && !mod.is_introduction && !ctx.introComplete) return false
  // Below-level tracks are already "mastered": a module whose track sits at a
  // maturity level strictly below the learner's effective level is fully
  // unlocked — the whole prerequisite path is bypassed so the learner can
  // freely review it (levels below the assessed level count as complete, the
  // same model the overall bar uses). Current-level and higher tracks still
  // gate: higher levels never reach here (unlocked_by_maturity === false
  // above), and same-level prerequisites fall through to isPrereqSatisfied below.
  const rank = ctx.moduleLevelRank.get(id)
  if (rank !== undefined && rank < ctx.levelIdx) return true
  const preds = ctx.prereqMap.get(id)
  if (!preds || preds.length === 0) return true
  return preds.every(p => isPrereqSatisfied(ctx, p, id))
}
