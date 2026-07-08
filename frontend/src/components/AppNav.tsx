import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const s = {
  nav:      { flexShrink: 0, zIndex: 20, background: '#fff', borderBottom: '1px solid #E2E2E2', display: 'flex', alignItems: 'center', padding: '0 40px', height: 64 },
  left:     { flex: '1 1 0', display: 'flex', alignItems: 'center', gap: 12 },
  center:   { flex: '1 1 0', display: 'flex', justifyContent: 'center', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 30, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#3C3C3C', pointerEvents: 'none' },
  right:    { flex: '1 1 0', position: 'relative', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 10 },
  logo:     { height: 28, width: 'auto', display: 'block' },
  divider:  { width: 1, height: 20, background: '#E2E2E2', flexShrink: 0 },
  backBtn:  { background: 'none', border: 'none', padding: 0, cursor: 'pointer', fontSize: 13, fontWeight: 600, color: 'var(--dlw-muted)', fontFamily: 'var(--dlw-font-body)', whiteSpace: 'nowrap' },
  trigger:  { display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', background: 'none', border: 'none', padding: 0 },
  nameCol:  { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.2 },
  name:     { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 14, color: '#101820' },
  avatar:   { width: 36, height: 36, borderRadius: '50%', background: '#C42828', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 13, flexShrink: 0 },
  dropdown: { position: 'absolute', top: 'calc(100% + 10px)', right: 0, background: '#fff', border: '1px solid #E2E2E2', borderRadius: 10, boxShadow: '0 8px 24px -8px rgba(16,24,32,.18)', minWidth: 180, zIndex: 100, overflow: 'hidden' },
  item:     { display: 'block', width: '100%', textAlign: 'left', padding: '12px 16px', background: 'none', border: 'none', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: '#3C3C3C', cursor: 'pointer' },
  itemLine: { height: 1, background: '#F0EFED', margin: '2px 0' },
} satisfies Record<string, CSSProperties>

interface AppNavProps {
  title?: string
  backTo?: string
  backLabel?: string
  leftExtra?: ReactNode
  rightExtra?: ReactNode
  /** Render for a dark background (transparent bar, white logo + light text).
   *  Used by the immersive dark hero on JourneyHome; safe to drop anywhere. */
  dark?: boolean
}

export default function AppNav({ title, backTo, backLabel = '← Back to hub', leftExtra, rightExtra, dark = false }: AppNavProps) {
  const { user, role, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!dropdownOpen) return
    function handler(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setDropdownOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [dropdownOpen])

  async function handleSignOut() {
    await logout()
    navigate('/login')
  }

  const firstName = user?.first_name ?? ''
  const lastName  = user?.last_name  ?? ''
  const initials  = firstName && lastName ? `${firstName[0]}${lastName[0]}` : '?'
  const showAdminLink = role === 'admin' && pathname !== '/admin'

  // Dark-variant overrides — transparent bar so the hero background shows
  // through; light logo/text. Everything else (dropdown, avatar) is unchanged.
  const nav     = dark ? { ...s.nav, background: 'transparent', borderBottom: 'none' } : s.nav
  const center  = dark ? { ...s.center, color: 'rgba(255,255,255,0.85)' } : s.center
  const name    = dark ? { ...s.name, color: '#fff' } : s.name
  const backBtn = dark ? { ...s.backBtn, color: 'rgba(255,255,255,0.7)' } : s.backBtn
  const divider = dark ? { ...s.divider, background: 'rgba(255,255,255,0.22)' } : s.divider
  const logoSrc = dark ? '/assets/logo/delaware-wordmark-white.svg' : '/assets/logo/delaware-wordmark.svg'

  return (
    <nav style={nav}>
      <div style={s.left}>
        <img style={s.logo} src={logoSrc} alt="delaware" />
        {backTo && <>
          <div style={divider} />
          <button type="button" style={backBtn} onClick={() => navigate(backTo)}>
            {backLabel}
          </button>
        </>}
        {leftExtra}
      </div>

      {title && <span style={center}>{title}</span>}

      <div style={s.right}>
        {rightExtra}
        <div style={{ position: 'relative' }} ref={dropdownRef}>
          <button type="button" style={s.trigger} onClick={() => setDropdownOpen(o => !o)}>
            <div style={s.nameCol}>
              <span style={name}>{firstName} {lastName}</span>
            </div>
            <div style={s.avatar}>{initials}</div>
          </button>
          {dropdownOpen && (
            <div style={s.dropdown}>
              {showAdminLink && <>
                <button type="button" className="menu-item-hover" style={s.item}
                  onClick={() => { setDropdownOpen(false); navigate('/admin') }}>
                  Admin panel
                </button>
                <div style={s.itemLine} />
              </>}
              <button type="button" className="menu-action-hover"
                style={{ ...s.item, color: '#8A8A8A' }}
                onClick={handleSignOut}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
