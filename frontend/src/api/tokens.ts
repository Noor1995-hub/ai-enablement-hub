// localStorage token store — the single seam for auth credentials. When Entra ID
// lands, MSAL token acquisition replaces this module (design-frontend.md §2);
// nothing else touches storage directly.

const ACCESS_KEY = 'hub.access_token'
const REFRESH_KEY = 'hub.refresh_token'

type Listener = () => void
const listeners = new Set<Listener>()

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

/** Clears the pair and broadcasts, so a middleware-forced logout (dead refresh
 * session) reaches AuthContext without a React dependency on this module. */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  for (const cb of listeners) cb()
}

export function subscribe(cb: Listener): () => void {
  listeners.add(cb)
  return () => {
    listeners.delete(cb)
  }
}
