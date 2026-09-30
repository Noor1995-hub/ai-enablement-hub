import type { AdminLearningResponseEnriched, AdminLearningUserEnriched } from '../../types/domain'
import type { AssignmentKind } from './api'

export type LearningModule = AdminLearningResponseEnriched['modules'][number]
export type LearningLesson = AdminLearningResponseEnriched['lessons'][number]
export type CellState = 'yes' | 'def' | 'part' | ''

/** Parent → direct-child ids, built once per data load. `deriveCellState` used
 * to call `modules.filter(...)` / `lessons.filter(...)` inside every single cell,
 * so the work was O(users × columns × content) on every render — including the
 * re-render each optimistic cell toggle causes. */
export interface ChildIdIndex {
  byTrack: Map<string, string[]>
  byModule: Map<string, string[]>
}

export function buildChildIdIndex(modules: LearningModule[], lessons: LearningLesson[]): ChildIdIndex {
  const byTrack = new Map<string, string[]>()
  for (const module of modules) {
    const list = byTrack.get(module.track_id)
    if (list) list.push(module.id)
    else byTrack.set(module.track_id, [module.id])
  }
  const byModule = new Map<string, string[]>()
  for (const lesson of lessons) {
    const list = byModule.get(lesson.module_id)
    if (list) list.push(lesson.id)
    else byModule.set(lesson.module_id, [lesson.id])
  }
  return { byTrack, byModule }
}

/**
 * Cell state for one user × content-item, derived entirely client-side from the
 * enriched assignment/default arrays (spec §3.4):
 * - in `assigned_*` and NOT in `default_*` → `yes` (explicit, solid ✓)
 * - in both → `def` (via project default, tinted ✓)
 * - not assigned itself but SOME-but-not-all children assigned → `part` (◐)
 *   (tracks check their modules, modules check their lessons; lessons have none)
 * - else empty.
 */
export function deriveCellState(
  kind: AssignmentKind,
  itemId: string,
  user: AdminLearningUserEnriched,
  childIds: ChildIdIndex,
): CellState {
  const assigned =
    kind === 'track'
      ? user.assigned_track_ids
      : kind === 'module'
        ? user.assigned_module_ids
        : user.assigned_lesson_ids
  const defaults =
    kind === 'track'
      ? user.default_track_ids
      : kind === 'module'
        ? user.default_module_ids
        : user.default_lesson_ids

  if (assigned.includes(itemId)) {
    return defaults.includes(itemId) ? 'def' : 'yes'
  }

  // Partial is a coverage signal over the item's direct children.
  const children =
    kind === 'track' ? childIds.byTrack.get(itemId) : kind === 'module' ? childIds.byModule.get(itemId) : undefined
  if (!children || children.length === 0) return ''
  const assignedChildren = new Set(kind === 'track' ? user.assigned_module_ids : user.assigned_lesson_ids)
  const covered = children.filter(id => assignedChildren.has(id)).length
  return covered > 0 && covered < children.length ? 'part' : ''
}
