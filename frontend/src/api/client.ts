import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './tokens'

/** Error body produced by the backend's exception handlers:
 * `{"error": {code, message[, fields]}}`. */
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    fields?: { field: string; message: string }[]
  }
}

/** Pull the human-readable message out of an error body of unknown shape. */
export function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'error' in body) {
    const err = (body as ApiErrorBody).error
    if (err && typeof err.message === 'string') return err.message
  }
  return fallback
}

// ── Single-flight refresh ─────────────────────────────────────────────────────
// Refresh tokens ROTATE ON EVERY USE: if two 401s each fired their own
// POST /api/auth/refresh, the second would present the token the first just
// consumed, get a 401, and force a logout loop. All concurrent callers must
// share one in-flight refresh.

let refreshInFlight: Promise<string | null> | null = null

export function refreshAccessToken(): Promise<string | null> {
  refreshInFlight ??= doRefresh().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

async function doRefresh(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  let res: Response
  try {
    res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
  } catch {
    return null // network blip: keep the tokens, surface the original 401
  }
  if (res.status === 401) {
    // The single-flight above is per tab, but localStorage is shared: if another
    // tab rotated while we were in flight, our token lost that race — adopt the
    // winner's pair rather than logging every tab out.
    const current = getRefreshToken()
    if (current !== null && current !== refresh) return getAccessToken()
    clearTokens() // session is dead (revoked/expired) — forced logout broadcast
    return null
  }
  if (!res.ok) return null
  const pair = (await res.json()) as { access_token: string; refresh_token: string }
  setTokens(pair.access_token, pair.refresh_token)
  return pair.access_token
}

// ── Auth middleware ───────────────────────────────────────────────────────────
// Everything under /api/auth/* is exempt: those endpoints carry their own
// credential (body or URL token), and a 401 from them is an answer, not an
// expired-access-token signal (login 401 = wrong password; refresh 401 = dead
// session). Retrying them through refresh would loop.

const AUTH_EXEMPT_PREFIX = '/api/auth/'

function isAuthExempt(request: Request): boolean {
  return new URL(request.url).pathname.startsWith(AUTH_EXEMPT_PREFIX)
}

// Request bodies are one-shot streams; keep a pristine clone so the 401-retry
// can re-send POST/PUT bodies.
const retryClones = new WeakMap<Request, Request>()

const authMiddleware: Middleware = {
  onRequest({ request }) {
    if (isAuthExempt(request)) return
    const access = getAccessToken()
    if (access) request.headers.set('Authorization', `Bearer ${access}`)
    retryClones.set(request, request.clone())
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 || isAuthExempt(request)) return
    const access = await refreshAccessToken()
    if (!access) return // refresh failed; the original 401 propagates
    const retry = retryClones.get(request) ?? request
    retry.headers.set('Authorization', `Bearer ${access}`)
    return fetch(retry) // plain fetch: a second 401 must not re-enter the middleware
  },
}

export const client = createClient<paths>()
client.use(authMiddleware)
