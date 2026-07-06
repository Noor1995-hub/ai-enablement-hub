import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { client } from '../api/client'
import { setTokens } from '../api/tokens'
import { useAuth } from '../contexts/AuthContext'

/**
 * Landing pad for the Entra ID sign-in: the backend callback redirects here
 * with a one-time code in the URL *fragment* (never sent to the server, never
 * in access logs). We swap it for the normal token pair and enter the app —
 * the same "credential from URL → setTokens → refreshProfile → navigate"
 * shape as SetPassword.
 */
export default function AuthCallback() {
  const navigate = useNavigate()
  const { refreshProfile } = useAuth()
  // The code is single-use: React StrictMode's dev double-effect would redeem
  // it twice (the second attempt 404s and would bounce a successful login back
  // to /login), so the ref guard is load-bearing.
  const fired = useRef(false)

  useEffect(() => {
    if (fired.current) return
    fired.current = true

    const code = new URLSearchParams(window.location.hash.slice(1)).get('code')
    if (!code) {
      navigate('/login?error=entra_failed', { replace: true })
      return
    }
    ;(async () => {
      const { data } = await client.POST('/api/auth/entra/redeem', { body: { code } })
      if (!data) {
        navigate('/login?error=entra_failed', { replace: true })
        return
      }
      setTokens(data.access_token, data.refresh_token)
      await refreshProfile()
      navigate('/', { replace: true })
    })()
  }, [navigate, refreshProfile])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="13" stroke="#E2E2E2" strokeWidth="3" />
        <circle cx="16" cy="16" r="13" stroke="#EF463C" strokeWidth="3"
          strokeDasharray="40 44" strokeLinecap="round"
          style={{ transformOrigin: '50% 50%', animation: 'spin 0.9s linear infinite' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </svg>
    </div>
  )
}
