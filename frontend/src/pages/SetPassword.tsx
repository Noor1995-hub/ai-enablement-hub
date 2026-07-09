import { useEffect, useState, type CSSProperties } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { client, errorMessage } from '../api/client'
import { setTokens } from '../api/tokens'
import { useAuth } from '../contexts/AuthContext'
import Spinner from '../components/Spinner'
import type { InviteInfo } from '../types/domain'

// Reworked from the old two-step (supabase.auth.updateUser + complete-password-setup):
// the invite/reset credential is now an opaque token in the URL, and one atomic
// POST /api/auth/set-password validates it, sets the password, and returns login
// tokens (design-frontend.md §2). The old "recovery session" mode is gone.

const s = {
  page: {
    minHeight: '100vh', background: '#F5F5F5',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 24,
  },
  card: {
    background: '#fff', borderRadius: 16, padding: '48px 44px',
    width: 'min(440px, 100%)',
    boxShadow: '0 18px 50px -20px rgba(16,24,32,.18), 0 2px 8px rgba(16,24,32,.05)',
  },
  logoRow: { display: 'flex', alignItems: 'center', gap: 2, marginBottom: 36, textDecoration: 'none' },
  dLogo:   { height: 28, width: 'auto', display: 'block' },
  wordmark: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 20, color: '#101820', letterSpacing: '-0.01em',
  },
  eyebrow: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.14em', textTransform: 'uppercase',
    color: '#EF463C', margin: '0 0 10px',
  },
  heading: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 30, lineHeight: 1.15, color: '#101820', margin: '0 0 8px',
  },
  subtitle: {
    fontSize: 15, lineHeight: 1.6, fontWeight: 300,
    color: '#8A8A8A', margin: '0 0 28px',
  },

  fieldWrap: { marginBottom: 16 },
  label: {
    display: 'block', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 12, letterSpacing: '0.04em', color: '#3C3C3C', marginBottom: 8,
  },
  input: {
    width: '100%', padding: '13px 16px', boxSizing: 'border-box',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 15,
    color: '#101820', background: '#fff',
    border: '1px solid #E2E2E2', borderRadius: 4, outline: 'none',
    transition: 'border-color 180ms',
  },
  inputFocus: { borderColor: '#EF463C' },

  hint: { fontSize: 12, color: '#B6B6B6', marginTop: 6 },

  btn: {
    width: '100%', padding: '14px 24px', marginTop: 8,
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 15,
    color: '#fff', background: '#C42828', border: 'none',
    borderRadius: 999, cursor: 'pointer', transition: 'background 180ms',
  },
  btnDisabled: { background: '#E2E2E2', color: '#999', cursor: 'not-allowed' },

  errorBox: {
    marginTop: 14, padding: '11px 14px',
    background: '#FFF0EF', border: '1px solid #FBCFCC',
    borderRadius: 6, fontSize: 13, lineHeight: 1.55, color: '#C42828',
  },

  noSession: {
    textAlign: 'center', fontSize: 15, fontWeight: 300,
    color: '#8A8A8A', lineHeight: 1.6,
  },
} satisfies Record<string, CSSProperties>

interface InputFieldProps {
  id: string
  label: string
  placeholder: string
  value: string
  onChange: (value: string) => void
  hint?: string
}

function InputField({ id, label, placeholder, value, onChange, hint }: InputFieldProps) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={s.fieldWrap}>
      <label style={s.label} htmlFor={id}>{label}</label>
      <input
        id={id} type="password" placeholder={placeholder}
        value={value} onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        style={{ ...s.input, ...(focused ? s.inputFocus : {}) }}
        autoComplete="new-password"
      />
      {hint && <p style={s.hint}>{hint}</p>}
    </div>
  )
}

type LinkState = 'checking' | 'ok' | 'invalid' | 'expired'

const LINK_ERRORS: Record<'invalid' | 'expired', string> = {
  invalid: 'This link has expired or is invalid.',
  expired: 'This link has expired. Please ask your admin for a new one.',
}

export default function SetPassword() {
  const navigate = useNavigate()
  const { session, logout, refreshProfile } = useAuth()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [linkState, setLinkState] = useState<LinkState>(token ? 'checking' : 'invalid')
  const [info, setInfo] = useState<InviteInfo | null>(null)
  const [password, setPassword]   = useState('')
  const [confirm, setConfirm]     = useState('')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState<string | null>(null)
  const [btnHover, setBtnHover]   = useState(false)

  // Peek (non-consuming) validation for the greeting + early expired/invalid UI.
  useEffect(() => {
    if (!token) return
    let cancelled = false
    client.GET('/api/auth/invite/{token}', { params: { path: { token } } })
      .then(({ data, response }) => {
        if (cancelled) return
        if (data) {
          setInfo(data)
          setLinkState('ok')
        } else {
          setLinkState(response.status === 410 ? 'expired' : 'invalid')
        }
      })
      .catch(() => {
        if (!cancelled) setLinkState('invalid')
      })
    return () => {
      cancelled = true
    }
  }, [token])

  const firstName = info?.first_name ?? ''
  const mismatch  = confirm.length > 0 && password !== confirm
  const canSubmit = password.length >= 8 && password === confirm

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit || loading || !token) return
    setLoading(true)
    setError(null)

    const { data, error: err, response } = await client.POST('/api/auth/set-password', {
      body: { token, password },
    })
    if (!data) {
      if (response.status === 404 || response.status === 410) {
        setLinkState(response.status === 410 ? 'expired' : 'invalid')
      } else {
        // 429 (rate limited) or unexpected — show the backend message, keep the form.
        setError(errorMessage(err, 'Could not set your password — please try again.'))
      }
      setLoading(false)
      return
    }

    // The backend consumed the token, set the password, and auto-logged us in.
    setTokens(data.access_token, data.refresh_token)
    await refreshProfile()
    navigate('/', { replace: true })
  }

  const btnStyle = {
    ...s.btn,
    ...(btnHover && canSubmit && !loading ? { background: '#941914' } : {}),
    ...(!canSubmit || loading ? s.btnDisabled : {}),
  }

  if (linkState === 'checking') return <Spinner fullPage />

  if (linkState !== 'ok') {
    return (
      <div style={s.page}>
        <div style={s.card}>
          <p style={s.noSession}>
            {LINK_ERRORS[linkState]}<br />
            <button
              style={{ ...s.btn, marginTop: 20 }}
              onClick={() => {
                // Defensive: a live session here (password_set=false gate) would
                // otherwise bounce straight back from /login.
                if (session) void logout()
                navigate('/login')
              }}
            >
              back to sign in
            </button>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <a href="https://delaware.pro" style={s.logoRow} tabIndex={-1}>
          <img style={s.dLogo} src="/assets/logo/delaware-d.svg" alt="" />
          <span style={s.wordmark}>elaware</span>
        </a>

        <p style={s.eyebrow}>AI Enablement Hub</p>
        <h1 style={s.heading}>
          {firstName ? `choose a password, ${firstName}.` : 'create your password'}
        </h1>
        <p style={s.subtitle}>
          {firstName
            ? `set a new password for your account, ${firstName}. you'll use it every time you sign in.`
            : 'choose a password to secure your account. you\'ll use it every time you sign in.'}
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <InputField
            id="pw-new" label="new password" placeholder="at least 8 characters"
            value={password} onChange={setPassword}
            hint="minimum 8 characters"
          />
          <InputField
            id="pw-confirm" label="confirm password" placeholder="repeat your password"
            value={confirm} onChange={setConfirm}
            hint={mismatch ? '⚠ passwords don\'t match' : ''}
          />
          <button
            type="submit" style={btnStyle}
            disabled={!canSubmit || loading}
            onMouseEnter={() => setBtnHover(true)}
            onMouseLeave={() => setBtnHover(false)}
          >
            {loading ? 'saving…' : 'set password & continue →'}
          </button>
        </form>

        {error && <div style={s.errorBox}>{error}</div>}

        <p style={{ textAlign: 'center', marginTop: 24, fontSize: 13, color: '#8A8A8A' }}>
          Not you?{' '}
          <button
            style={{ background: 'none', border: 'none', color: '#8A8A8A', textDecoration: 'underline', cursor: 'pointer', fontSize: 13, padding: 0 }}
            onClick={async () => { await logout(); navigate('/login') }}
          >
            Sign out
          </button>
        </p>
      </div>
    </div>
  )
}
