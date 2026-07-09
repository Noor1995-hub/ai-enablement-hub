import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { client } from '../api/client'
import Spinner from '../components/Spinner'

// The URL token IS the credential now (single-use, validated without being
// consumed): instead of exchanging /invite/:id for a stored Supabase action
// link, we peek GET /api/auth/invite/{token} and hand the same token to
// /set-password (design-frontend.md §2).

type Status = 'loading' | 'invalid' | 'expired' | 'error'

const ERROR_MESSAGES: Record<Exclude<Status, 'loading'>, string> = {
  invalid: 'This invite link is invalid or has already been used.',
  expired: 'This invite link has expired. Please ask your admin for a new one.',
  error:   'Could not verify this link — please try again.',
}

export default function InviteRedirect() {
  const { id } = useParams<'id'>()
  const navigate = useNavigate()
  const [status, setStatus] = useState<Status>('loading')

  useEffect(() => {
    if (!id) {
      setStatus('invalid')
      return
    }
    let cancelled = false
    client.GET('/api/auth/invite/{token}', { params: { path: { token: id } } })
      .then(({ data, response }) => {
        if (cancelled) return
        if (data) {
          navigate(`/set-password?token=${encodeURIComponent(id)}`, { replace: true })
        } else if (response.status === 410) {
          setStatus('expired')
        } else if (response.status >= 500) {
          setStatus('error')
        } else {
          setStatus('invalid')
        }
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [id, navigate])

  if (status === 'loading') return <Spinner fullPage />

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#fff', borderRadius: 16, padding: '48px 40px', textAlign: 'center', boxShadow: '0 2px 16px rgba(0,0,0,0.08)' }}>
        <p style={{ color: '#8A8A8A', fontSize: 16, margin: '0 0 24px' }}>
          {ERROR_MESSAGES[status]}
        </p>
        <button
          style={{ background: 'var(--dlw-primary-red)', color: '#fff', border: 'none', borderRadius: 999, padding: '12px 28px', cursor: 'pointer', fontSize: 15, fontFamily: 'var(--dlw-font-body)' }}
          onClick={() => navigate('/login')}
        >
          back to sign in
        </button>
      </div>
    </div>
  )
}
