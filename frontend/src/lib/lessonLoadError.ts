import { errorMessage } from '../api/client'

/** Why `GET /api/lessons/{id}` produced no lesson, for an HTTP response that
 * actually came back (status >= 0). A rejected fetch — no response at all,
 * e.g. offline or a dropped connection mid-deploy — is NOT this: openapi-fetch
 * 0.17 re-throws that rejection rather than resolving with some sentinel
 * status, so the caller must catch it separately and go straight to `failed`
 * without calling this function. See `LessonPage.tsx`'s `load()`.
 * - `not-found`: the server said 404 — the lesson doesn't exist (or isn't the
 *   caller's; the endpoint doesn't distinguish the two).
 * - `forbidden`: the server said 403 — the lesson exists but access is denied.
 *   Covers both `LessonNotAccessibleError` (above the learner's level/not
 *   assigned) and a project-level component lock; both cases carry their own
 *   message server-side, so it's shown verbatim rather than picking one copy.
 * - `failed`: any other status this function is actually called with (5xx,
 *   422 on a malformed id, a 401 whose refresh already failed — the auth
 *   middleware in `api/client.ts` handles the refresh-and-retry itself, so a
 *   401 reaching here means that already didn't work) — a failure to load,
 *   not a verdict on the lesson. */
export type LessonLoadError =
  | { kind: 'not-found' }
  | { kind: 'forbidden'; message: string }
  | { kind: 'failed' }

export function classifyLessonLoadError(status: number, errorBody: unknown): LessonLoadError {
  if (status === 404) return { kind: 'not-found' }
  if (status === 403) {
    return {
      kind: 'forbidden',
      message: errorMessage(errorBody, "You don't have access to this lesson."),
    }
  }
  return { kind: 'failed' }
}
