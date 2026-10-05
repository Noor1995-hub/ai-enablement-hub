// Pure helpers for the lesson editor's guarded save (B5, spec 2026-10-05).
import type { components } from '../api/schema'
import type { ContentBlock } from '../types/contentBlocks'

export type Finding = components['schemas']['LessonFindingOut']

/** [singular, plural] nouns for a removal sentence. BLOCK_LABELS are the
 * editor picker's labels ("Text", "Cards", …) and read badly in prose. */
export const BLOCK_NOUNS: Record<ContentBlock['type'], [string, string]> = {
  heading: ['heading', 'headings'],
  paragraph: ['paragraph', 'paragraphs'],
  callout: ['callout', 'callouts'],
  kicker: ['kicker', 'kickers'],
  card_group: ['card group', 'card groups'],
  quiz: ['quiz', 'quizzes'],
  question: ['question', 'questions'],
  whitespace: ['spacer', 'spacers'],
  interactive: ['interactive exercise', 'interactive exercises'],
  try_it_yourself: ['try-it-yourself exercise', 'try-it-yourself exercises'],
  image: ['image', 'images'],
  video: ['video', 'videos'],
}

/** "This removes 1 quiz and 1 card group." when `after` has fewer blocks of
 * some type than `before`; null when nothing is lost. The #60 safety net. */
export function removalSummary(before: ContentBlock[], after: ContentBlock[]): string | null {
  const count = (blocks: ContentBlock[]) => {
    const counts = new Map<ContentBlock['type'], number>()
    for (const block of blocks) counts.set(block.type, (counts.get(block.type) ?? 0) + 1)
    return counts
  }
  const now = count(after)
  const lost: string[] = []
  for (const [type, was] of count(before)) {
    const n = was - (now.get(type) ?? 0)
    if (n <= 0) continue
    const [one, many] = BLOCK_NOUNS[type] ?? [type, `${type}s`]
    lost.push(`${n} ${n === 1 ? one : many}`)
  }
  if (lost.length === 0) return null
  const list = lost.length === 1 ? lost[0] : `${lost.slice(0, -1).join(', ')} and ${lost[lost.length - 1]}`
  return `This removes ${list}.`
}

/** The 409 `lesson_changed` body, or null for any other error. */
export function parseConflict(error: unknown): { updatedAt: string; updatedByName: string | null } | null {
  if (!error || typeof error !== 'object' || !('error' in error)) return null
  const body = (error as { error: Record<string, unknown> }).error
  if (!body || body.code !== 'lesson_changed' || typeof body.updated_at !== 'string') return null
  return {
    updatedAt: body.updated_at,
    updatedByName: typeof body.updated_by_name === 'string' ? body.updated_by_name : null,
  }
}
