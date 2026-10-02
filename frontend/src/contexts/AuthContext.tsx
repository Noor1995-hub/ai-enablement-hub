import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { client, errorMessage } from '../api/client'
import { clearTokens, getAccessToken, getRefreshToken, setTokens, subscribe } from '../api/tokens'
import type { UserProfile } from '../types/domain'

// Same provider value shape as the old Supabase context (minus isRecovery, which
// existed only for Supabase's recovery-session event) so consuming pages port
// mechanically; the internals are the FastAPI token pair (design-frontend.md §2).

// 'admin' = power admin. Project admins are role 'user' with admin rights over
// specific projects (adminProjectIds) — spec 2026-10-01-project-scoped-admin.
export type Role = 'admin' | 'user'

/** Thrown by login() so the Login page can distinguish 401 (wrong password)
 * from 429 (rate limited — NEVER auto-retried). */
export class LoginError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'LoginError'
    this.status = status
  }
}

interface AuthValue {
  /** undefined = restoring, false = logged out, true = logged in */
  session: boolean | undefined
  user: UserProfile | null | undefined
  role: Role | null
  /** role === 'admin': every admin power, on every project. */
  isPowerAdmin: boolean
  /** Projects this user administers as a project admin (empty for learners). */
  adminProjectIds: string[]
  /** Server-resolved: power admins, and project admins on their own project,
   * bypass locked components, module prerequisites and the assessment gate. */
  bypassesLocks: boolean
  passwordSet: boolean | undefined
  /** true once an Entra ID account is linked — such users never need the
   * forced set-password step (they may have no password at all). */
  externalLogin: boolean | undefined
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  markPasswordSet: () => void
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  // Single source of truth: undefined = restoring, null = logged out.
  const [user, setUser] = useState<UserProfile | null | undefined>(undefined)

  const fetchProfile = useCallback(async (): Promise<UserProfile | null> => {
    const { data } = await client.GET('/api/me')
    return data ?? null
  }, [])

  // Session restore on reload: a stored access token + GET /api/me replaces the
  // old getSession() + users-table SELECT. An expired access token is refreshed
  // transparently by the client middleware; if that fails too, tokens are
  // cleared and we land logged-out.
  useEffect(() => {
    if (!getAccessToken()) {
      setUser(null)
      return
    }
    let cancelled = false
    fetchProfile().then((profile) => {
      if (!cancelled) setUser(profile)
    })
    return () => {
      cancelled = true
    }
  }, [fetchProfile])

  // Middleware-forced logout (dead refresh session) → React state.
  useEffect(
    () =>
      subscribe(() => {
        setUser(null)
      }),
    [],
  )

  const login = useCallback(
    async (email: string, password: string) => {
      const { data, error, response } = await client.POST('/api/auth/login', {
        body: { email: email.trim(), password },
      })
      if (!data) {
        throw new LoginError(response.status, errorMessage(error, 'Login failed'))
      }
      setTokens(data.access_token, data.refresh_token)
      setUser(await fetchProfile())
    },
    [fetchProfile],
  )

  const logout = useCallback(async () => {
    const refresh = getRefreshToken()
    if (refresh) {
      // Best-effort server-side revocation; local logout happens regardless.
      await client
        .POST('/api/auth/logout', { body: { refresh_token: refresh } })
        .catch(() => undefined)
    }
    clearTokens()
    setUser(null)
  }, [])

  const markPasswordSet = useCallback(() => {
    setUser((u) => (u ? { ...u, password_set: true } : u))
  }, [])

  const refreshProfile = useCallback(async () => {
    setUser(await fetchProfile())
  }, [fetchProfile])

  const value: AuthValue = {
    session: user === undefined ? undefined : user !== null,
    user,
    role: user ? (user.role as Role) : null,
    isPowerAdmin: user?.is_power_admin ?? false,
    adminProjectIds: user?.admin_project_ids ?? [],
    bypassesLocks: user?.bypasses_locks ?? false,
    passwordSet: user?.password_set,
    externalLogin: user?.external_login,
    loading: user === undefined,
    login,
    logout,
    markPasswordSet,
    refreshProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components -- context + hook pair, same as the old app
export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
