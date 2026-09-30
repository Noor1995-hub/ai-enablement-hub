import { beforeEach, describe, expect, it } from 'vitest'
import { claimChunkReload, isChunkLoadError } from './chunkLoadError'

describe('isChunkLoadError', () => {
  it.each([
    // Chromium, and Vite's own wording for a failed `import()`
    'Failed to fetch dynamically imported module: https://hub.example/assets/AdminShell-abc123.js',
    // Safari
    'Importing a module script failed.',
    // Firefox
    'error loading dynamically imported module: https://hub.example/assets/x.js',
    // Vite 6, when a lazy chunk's CSS file is gone
    'Unable to preload CSS for /assets/admin-abc123.css',
  ])('recognises a dynamic-import failure: %s', message => {
    expect(isChunkLoadError(new TypeError(message))).toBe(true)
  })

  it('recognises a ChunkLoadError by name', () => {
    const error = new Error('Loading chunk 7 failed.')
    error.name = 'ChunkLoadError'
    expect(isChunkLoadError(error)).toBe(true)
  })

  it.each([
    "Cannot read properties of null (reading '0')",
    'Failed to fetch',
    '',
  ])('does not treat an ordinary render error as a chunk failure: "%s"', message => {
    expect(isChunkLoadError(new TypeError(message))).toBe(false)
  })

  it('tolerates non-Error values thrown by a render', () => {
    expect(isChunkLoadError(null)).toBe(false)
    expect(isChunkLoadError('Failed to fetch dynamically imported module')).toBe(false)
    expect(isChunkLoadError({ name: 'ChunkLoadError' })).toBe(false)
  })
})

describe('claimChunkReload', () => {
  beforeEach(() => sessionStorage.clear())

  it('allows the first reload and refuses another within 30 seconds', () => {
    expect(claimChunkReload(1_000_000)).toBe(true)
    expect(claimChunkReload(1_010_000)).toBe(false)
  })

  it('allows a reload again once the window has passed', () => {
    expect(claimChunkReload(1_000_000)).toBe(true)
    expect(claimChunkReload(1_031_000)).toBe(true)
  })
})
