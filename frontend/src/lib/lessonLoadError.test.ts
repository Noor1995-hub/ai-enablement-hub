import { describe, expect, it } from 'vitest'
import { classifyLessonLoadError } from './lessonLoadError'

describe('classifyLessonLoadError', () => {
  it('maps 404 to not-found', () => {
    expect(classifyLessonLoadError(404, undefined)).toEqual({ kind: 'not-found' })
  })

  it('maps 403 to forbidden, using the server message', () => {
    const body = {
      error: {
        code: 'lesson_not_accessible',
        message: 'This lesson is not available on your learning path',
      },
    }
    expect(classifyLessonLoadError(403, body)).toEqual({
      kind: 'forbidden',
      message: 'This lesson is not available on your learning path',
    })
  })

  it('shows the component-lock message verbatim too — same 403, different body', () => {
    const body = { error: { code: 'component_locked', message: 'Learning is locked for this project' } }
    expect(classifyLessonLoadError(403, body)).toEqual({
      kind: 'forbidden',
      message: 'Learning is locked for this project',
    })
  })

  it('falls back to a generic sentence on 403 with no parseable body', () => {
    expect(classifyLessonLoadError(403, undefined)).toEqual({
      kind: 'forbidden',
      message: "You don't have access to this lesson.",
    })
  })

  it('maps 5xx and a malformed-id 422 to a generic failed load', () => {
    expect(classifyLessonLoadError(500, undefined)).toEqual({ kind: 'failed' })
    expect(classifyLessonLoadError(502, undefined)).toEqual({ kind: 'failed' })
    expect(classifyLessonLoadError(422, undefined)).toEqual({ kind: 'failed' })
  })

  // Defensive only: this function is never actually called with status 0.
  // openapi-fetch re-throws a rejected fetch (offline, dropped connection)
  // rather than resolving with a sentinel status, so LessonPage's load()
  // catches that case itself and never reaches this classifier for it. This
  // just confirms an unrecognised status still falls through to 'failed'
  // rather than throwing.
  it('falls through to failed for an unrecognised status', () => {
    expect(classifyLessonLoadError(0, undefined)).toEqual({ kind: 'failed' })
  })
})
