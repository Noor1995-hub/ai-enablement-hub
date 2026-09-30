// Browser wordings for a failed dynamic `import()`, i.e. a lazy chunk that no
// longer exists after a redeploy (hashed asset names change) or a dropped
// connection: Chromium and Vite, Safari, Firefox. Vite 6 also rejects with
// "Unable to preload CSS for <file>" when a lazy chunk's stylesheet is gone.
const DYNAMIC_IMPORT_FAILURE =
  /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS for/i

/** True when a caught render error is a chunk-load failure. `React.lazy` caches
 * the rejected import, so re-rendering in place only re-throws it: the one
 * recovery is a full page reload, which fetches the new index.html and its
 * current chunk names. */
export function isChunkLoadError(error: unknown): boolean {
  if (!(error instanceof Error)) return false
  return error.name === 'ChunkLoadError' || DYNAMIC_IMPORT_FAILURE.test(error.message)
}

const RELOAD_KEY = 'chunk-reload-at'
const RELOAD_WINDOW_MS = 30_000

/** Reload-loop guard. Returns true (and records the attempt in sessionStorage) if
 * a chunk-failure reload may go ahead, false if one already ran in the last 30 s:
 * then the chunk is genuinely unreachable (offline, blocked) and reloading again
 * would only loop, so the caller falls back to an in-place retry. */
export function claimChunkReload(now: number = Date.now()): boolean {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_KEY))
    if (last && now - last < RELOAD_WINDOW_MS) return false
    sessionStorage.setItem(RELOAD_KEY, String(now))
  } catch {
    // Storage unavailable (private mode): reload once per click, never automatically.
  }
  return true
}
