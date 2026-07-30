import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import '../../styles/admin.css'
import { useFeedback, useProposals } from './api'
import { NAV_ITEMS, type NavIconKey } from './nav'
import ScopeSwitcher from './ScopeSwitcher'
import { useScope } from './useScope'

// One client for the whole admin2 shell — its children (dashboard, people,
// etc.) all read through this via useQuery. Created once per mount, not per
// render (a fresh QueryClient every render would drop the cache).
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, retry: 1 },
    },
  })
}

/** Layout route for /admin/*: topbar (brand + scope switcher + learner-app
 * link + user chip) + fixed sidebar (nav.ts registry) + scrollable main.
 * Mirrors docs/design-prototypes/admin-redesign/option-b.html's shell. */
export default function AdminShell() {
  const [queryClient] = useState(makeQueryClient)
  // Scope (?project=) must survive sidebar navigation — read once here and
  // carry it through every NavLink below.
  const [searchParams] = useSearchParams()
  const search = searchParams.toString()

  return (
    <QueryClientProvider client={queryClient}>
      <header className="adm-topbar">
        <Link className="adm-brand" to={{ pathname: '/admin', search: search ? `?${search}` : '' }}>
          <img className="adm-brand-logo" src="/assets/logo/delaware-wordmark.svg" alt="delaware" />
          <span className="adm-admin-tag">Admin</span>
        </Link>
        <ScopeSwitcher />
        <div className="adm-topbar-right">
          <Link className="adm-app-link" to="/">
            Open learner app <ExternalIcon />
          </Link>
          <UserChip />
        </div>
      </header>
      <div className="adm-shell">
        <nav className="adm-sidebar">
          {NAV_ITEMS.map(item => (
            <SidebarLink
              key={item.key}
              label={item.label}
              icon={item.icon}
              path={item.path}
              search={search}
              badge={
                item.key === 'feedback' ? <FeedbackNavBadge />
                : item.key === 'content-ai' ? <ProposalNavBadge />
                : undefined
              }
            />
          ))}
        </nav>
        <main className="adm-main">
          <div className="adm-container">
            <Outlet />
          </div>
        </main>
      </div>
    </QueryClientProvider>
  )
}

interface SidebarLinkProps {
  label: string
  icon: NavIconKey
  path: string
  search: string
  badge?: ReactNode
}

function SidebarLink({ label, icon, path, search, badge }: SidebarLinkProps) {
  const to = { pathname: path ? `/admin/${path}` : '/admin', search: search ? `?${search}` : '' }

  return (
    <NavLink
      to={to}
      end={path === ''}
      className={({ isActive }) => `adm-nav-item${isActive ? ' active' : ''}`}
    >
      <NavIcon name={icon} />
      {label}
      {badge}
    </NavLink>
  )
}

/** New-feedback count for the sidebar "Feedback" item — a dedicated
 * `{status:'new', limit:1}` query, project-scoped like every other screen
 * (spec §3.5 has no "always global" language), and deliberately the SAME
 * query key FeedbackPage's own "New" pill count fires, so the two share one
 * cache entry: triaging an item there invalidates `['admin','feedback']` on
 * settle, which refreshes this badge for free. Rendered as a child of
 * AdminShell's own `<QueryClientProvider>` (not called directly in
 * AdminShell's body) — that provider covers its JSX children, not the
 * component instantiating it. */
function FeedbackNavBadge() {
  const scope = useScope()
  const { data } = useFeedback({ status: 'new', project: scope.projectId, limit: 1 })
  const count = data?.total
  if (!count) return null
  return <span className="adm-nav-count">{count}</span>
}

/** Pending-proposal count for the "Content AI" nav item — same shape and same
 * shared-cache trick as FeedbackNavBadge: it fires the exact query key the
 * page's own "Pending" pill uses, so reviewing a proposal there invalidates
 * `['admin','proposals']` and refreshes this badge for free. Not project-
 * scoped: lessons are shared catalogue content, so proposals have no project. */
function ProposalNavBadge() {
  const { data } = useProposals({ status: 'pending', limit: 1 })
  const count = data?.total
  if (!count) return null
  return <span className="adm-nav-count">{count}</span>
}

function UserChip() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const firstName = user?.first_name ?? ''
  const lastName = user?.last_name ?? ''
  const initials = firstName && lastName ? `${firstName[0]}${lastName[0]}` : '?'

  async function handleSignOut() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="adm-user-chip" ref={ref}>
      <button type="button" className="adm-user-trigger" onClick={() => setOpen(o => !o)}>
        <span className="adm-user-name">{firstName} {lastName}</span>
        <span className="adm-avatar">{initials}</span>
      </button>
      {open && (
        <div className="adm-user-dropdown">
          <button type="button" className="adm-user-dropdown-item danger" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

// Path data lifted verbatim from the prototype's ICON_PATHS
// (docs/design-prototypes/admin-redesign/common.js).
const NAV_ICON_ELEMENTS: Record<NavIconKey, ReactNode> = {
  home: <path d="M3 9.5 12 3l9 6.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z" />,
  users: <>
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx={9} cy={7} r={4} />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
  </>,
  grid: <>
    <rect x={3} y={3} width={7} height={7} rx={1} />
    <rect x={14} y={3} width={7} height={7} rx={1} />
    <rect x={14} y={14} width={7} height={7} rx={1} />
    <rect x={3} y={14} width={7} height={7} rx={1} />
  </>,
  inbox: <>
    <path d="M22 12h-6l-2 3h-4l-2-3H2" />
    <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
  </>,
  edit: <>
    <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6" />
    <path d="M14 3v5h5" />
    <path d="m18.5 12.5 3 3L17 20H14v-3z" />
  </>,
  folder: <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />,
  mail: <>
    <rect x={2} y={4} width={20} height={16} rx={2} />
    <path d="m22 7-10 6L2 7" />
  </>,
  terminal: <>
    <polyline points="4 17 10 11 4 5" />
    <line x1={12} y1={19} x2={20} y2={19} />
  </>,
  settings: <>
    <circle cx={12} cy={12} r={3} />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </>,
}

function NavIcon({ name }: { name: NavIconKey }) {
  return (
    <svg width={17} height={17} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {NAV_ICON_ELEMENTS[name]}
    </svg>
  )
}

function ExternalIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <path d="M15 3h6v6" />
      <path d="M10 14 21 3" />
    </svg>
  )
}
