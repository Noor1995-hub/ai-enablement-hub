// Pure helpers for the admin Content page (spec 2026-10-05, B4).
import type { components } from '../api/schema'

export type TreeTrack = components['schemas']['TreeTrack']
export type TreeModule = components['schemas']['TreeModule']
export type TreeLesson = components['schemas']['TreeLesson']
export type DeleteImpact = components['schemas']['DeleteImpactResponse']
export type AssignmentGap = components['schemas']['AssignmentGapResponse']

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/** Case-insensitive name filter. A matching track or module is kept whole;
 * otherwise only matching descendants and their ancestors remain. */
export function filterTree(tracks: TreeTrack[], query: string): TreeTrack[] {
  const q = query.trim().toLowerCase()
  if (!q) return tracks
  const hit = (text: string) => text.toLowerCase().includes(q)
  return tracks.flatMap(track => {
    if (hit(track.name)) return [track]
    const modules = track.modules.flatMap(module => {
      if (hit(module.title)) return [module]
      const lessons = module.lessons.filter(lesson => hit(lesson.title))
      return lessons.length ? [{ ...module, lessons }] : []
    })
    return modules.length ? [{ ...track, modules }] : []
  })
}

/** The id list with `id` swapped one step up (-1) or down (+1); null when it
 * can't move (an edge, or not in the list). */
export function moveInList(ids: string[], id: string, direction: -1 | 1): string[] | null {
  const from = ids.indexOf(id)
  const to = from + direction
  if (from < 0 || to < 0 || to >= ids.length) return null
  const next = [...ids]
  ;[next[from], next[to]] = [next[to], next[from]]
  return next
}

export function impactLabel(impact: DeleteImpact): string {
  const parts = [
    ...(impact.modules ? [plural(impact.modules, 'module')] : []),
    plural(impact.lessons, 'lesson'),
  ]
  const what = parts.length === 2 ? `${parts[0]}, ${parts[1]}` : parts[0]
  if (impact.learners_with_progress === 0) {
    return `Deletes ${what}. No learner has progress on ${impact.lessons === 1 ? 'it' : 'them'}.`
  }
  return `Deletes ${what} and the progress of ${plural(impact.learners_with_progress, 'learner')}.`
}

export function gapLabel(gap: AssignmentGap): string | null {
  if (gap.missing_pairs === 0) return null
  return `${plural(gap.lesson_ids.length, 'lesson')} not yet assigned to the ${plural(gap.learner_count, 'learner')} who have this module.`
}
