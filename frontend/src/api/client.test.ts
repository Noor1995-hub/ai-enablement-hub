import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { refreshAccessToken } from './client'
import { getAccessToken, getRefreshToken, setTokens, subscribe } from './tokens'

// In-memory localStorage: tokens.ts is the only reader/writer, so a Map is enough
// and the tests stay independent of jsdom's storage implementation.
function stubLocalStorage() {
  const store = new Map<string, string>()
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
    removeItem: (key: string) => void store.delete(key),
    clear: () => store.clear(),
  })
}

/** A refresh endpoint that answers 401, optionally after "another tab" rotated
 * the shared token pair while our request was in flight. */
function stubRefresh401(otherTabRotatesTo?: { access: string; refresh: string }) {
  const fetchMock = vi.fn(() => {
    if (otherTabRotatesTo) setTokens(otherTabRotatesTo.access, otherTabRotatesTo.refresh)
    return Promise.resolve(new Response(null, { status: 401 }))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('refreshAccessToken on a 401', () => {
  beforeEach(() => {
    stubLocalStorage()
    setTokens('old-access', 'old-refresh')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('adopts the pair another tab just rotated instead of logging out', async () => {
    stubRefresh401({ access: 'tab-b-access', refresh: 'tab-b-refresh' })
    const onLogout = vi.fn()
    const unsubscribe = subscribe(onLogout)

    const access = await refreshAccessToken()
    unsubscribe()

    expect(access).toBe('tab-b-access')
    expect(getRefreshToken()).toBe('tab-b-refresh')
    expect(onLogout).not.toHaveBeenCalled()
  })

  it('clears the tokens and broadcasts the logout when nobody rotated', async () => {
    const fetchMock = stubRefresh401()
    const onLogout = vi.fn()
    const unsubscribe = subscribe(onLogout)

    const access = await refreshAccessToken()
    unsubscribe()

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(access).toBeNull()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(onLogout).toHaveBeenCalledOnce()
  })
})
