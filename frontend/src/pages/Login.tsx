import { useState, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { LoginError, useAuth } from '../contexts/AuthContext'

const s = {
  page: { display: 'flex', minHeight: '100vh', alignItems: 'stretch' },

  art: {
    position: 'relative', flex: '0 0 46%', overflow: 'hidden',
    backgroundImage: 'url(/assets/images/banner-large.jpg)',
    backgroundSize: 'cover', backgroundPosition: 'center',
    backgroundColor: '#101820',
    display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    padding: '40px 44px',
  },
  artOverlay: {
    position: 'absolute', inset: 0,
    background: 'linear-gradient(195deg, rgba(16,24,32,.30) 0%, rgba(16,24,32,.18) 38%, rgba(16,24,32,.72) 100%)',
  },
  artTop:    { position: 'relative', zIndex: 1 },
  artBottom: { position: 'relative', zIndex: 1 },
  artLogo:   { height: 22, width: 'auto', display: 'block' },
  artHeadline: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700, color: '#fff',
    fontSize: 32, lineHeight: 1.16, letterSpacing: '-0.01em',
    margin: '0 0 12px', maxWidth: '14ch',
  },
  artSub: {
    fontSize: 16, lineHeight: 1.55, color: '#fff',
    opacity: 0.86, fontWeight: 300, margin: '0 0 26px', maxWidth: '34ch',
  },
  artFooter: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 700,
    fontSize: 13, color: '#fff', opacity: 0.92, margin: 0,
  },

  panel: {
    flex: '1 1 54%', display: 'flex', alignItems: 'center',
    justifyContent: 'center', padding: '48px 40px', overflowY: 'auto', background: '#fff',
  },
  col: { width: 'min(400px, 100%)' },

  logoRow: { display: 'flex', alignItems: 'center', gap: 2, marginBottom: 40, textDecoration: 'none' },
  dLogo:   { height: 32, width: 'auto', display: 'block' },
  wordmark: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 22, color: '#101820', letterSpacing: '-0.01em',
  },

  eyebrow: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.14em', textTransform: 'uppercase',
    color: '#EF463C', margin: '0 0 12px',
  },
  heading: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 38, lineHeight: 1.12, letterSpacing: '-0.01em',
    color: '#101820', margin: '0 0 10px',
  },
  subtitle: {
    fontSize: 17, lineHeight: 1.55, fontWeight: 300,
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

  btn: {
    width: '100%', padding: '14px 24px', marginTop: 4,
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 15,
    color: '#fff', background: '#C42828', border: 'none',
    borderRadius: 999, cursor: 'pointer', transition: 'background 180ms',
  },
  btnHover:    { background: '#941914' },
  btnDisabled: { background: '#E2E2E2', color: '#999', cursor: 'not-allowed' },

  forgotWrap: { textAlign: 'right', marginTop: 10 },
  forgotBtn: {
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
    color: '#8A8A8A', padding: 0, transition: 'color 180ms',
  },

  errorBox: {
    marginTop: 14, padding: '11px 14px',
    background: '#FFF0EF', border: '1px solid #FBCFCC',
    borderRadius: 6, fontSize: 13, lineHeight: 1.55, color: '#C42828',
  },
  consent: {
    display: 'flex', gap: 10, alignItems: 'flex-start',
    marginTop: 24, fontSize: 13, lineHeight: 1.55, color: '#B6B6B6',
  },
} satisfies Record<string, CSSProperties>

function ShieldIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none"
      stroke="currentColor" strokeWidth="1.3" style={{ flexShrink: 0, marginTop: 1 }}>
      <path d="M8 1.5l5 2v4c0 3.2-2.1 5.6-5 7-2.9-1.4-5-3.8-5-7v-4l5-2z" strokeLinejoin="round" />
    </svg>
  )
}

interface InputFieldProps {
  id: string
  label: string
  type: 'email' | 'password'
  placeholder: string
  value: string
  onChange: (value: string) => void
}

function InputField({ id, label, type, placeholder, value, onChange }: InputFieldProps) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={s.fieldWrap}>
      <label style={s.label} htmlFor={id}>{label}</label>
      <input
        id={id} type={type} placeholder={placeholder}
        value={value} onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        style={{ ...s.input, ...(focused ? s.inputFocus : {}) }}
        autoComplete={type === 'password' ? 'current-password' : 'email'}
      />
    </div>
  )
}

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [btnHover, setBtnHover] = useState(false)
  const [forgotMode, setForgotMode] = useState(false)

  const canSubmit = email.includes('@') && password.length >= 6

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit || loading) return
    setLoading(true)
    setError(null)

    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      // 429 = rate limited (5/min per email): show the backend's message and
      // let the user retry manually — never auto-retry a login.
      if (err instanceof LoginError && err.status === 429) setError(err.message)
      else setError('Incorrect email or password.')
      setLoading(false)
    }
  }

  const btnStyle = {
    ...s.btn,
    ...(btnHover && canSubmit && !loading ? s.btnHover : {}),
    ...(!canSubmit || loading ? s.btnDisabled : {}),
  }

  return (
    <div style={s.page}>
      <div style={s.art}>
        <div style={s.artOverlay} />
        <div style={s.artTop}>
          <img style={s.artLogo} src="/assets/logo/delaware-wordmark-white.svg" alt="delaware" />
        </div>
        <div style={s.artBottom}>
          <h1 style={s.artHeadline}>ai enablement, built around how you work</h1>
          <p style={s.artSub}>
            a short journey to understand where you are with ai today, and to shape support that fits.
          </p>
          <p style={s.artFooter}>delaware · ai enablement hub</p>
        </div>
      </div>

      <div style={s.panel}>
        <div style={s.col}>
          <a href="https://delaware.pro" style={s.logoRow} tabIndex={-1}>
            <img style={s.dLogo} src="/assets/logo/delaware-d.svg" alt="" />
            <span style={s.wordmark}>elaware</span>
          </a>

          <p style={s.eyebrow}>AI Enablement Hub</p>
          <h2 style={s.heading}>{forgotMode ? 'forgot password?' : 'welcome'}</h2>

          {forgotMode ? (
            <p style={{ ...s.subtitle, marginBottom: 0 }}>
              Please contact your delaware contact person, they will provide you with a new link to reset your password.
            </p>
          ) : (
            <>
              <p style={s.subtitle}>sign in with your work email and password.</p>

              <form onSubmit={handleSubmit} noValidate>
                <InputField
                  id="hub-email" label="work email" type="email"
                  placeholder="you@company.com" value={email} onChange={setEmail}
                />
                <InputField
                  id="hub-password" label="password" type="password"
                  placeholder="••••••••" value={password} onChange={setPassword}
                />
                <button
                  type="submit" style={btnStyle}
                  disabled={!canSubmit || loading}
                  onMouseEnter={() => setBtnHover(true)}
                  onMouseLeave={() => setBtnHover(false)}
                >
                  {loading ? 'signing in…' : 'sign in →'}
                </button>
              </form>

              {error && <div style={s.errorBox}>{error}</div>}
            </>
          )}

          <div style={s.forgotWrap}>
            <button
              className="link-muted-hover"
              style={s.forgotBtn}
              onClick={() => { setForgotMode(f => !f); setError(null) }}
            >
              {forgotMode ? '← back to sign in' : 'forgot password?'}
            </button>
          </div>

          <div style={s.consent}>
            <ShieldIcon />
            <span>your responses are stored securely and used only for this engagement.</span>
          </div>
        </div>
      </div>
    </div>
  )
}
