import { useLayoutEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import Spinner from './components/Spinner'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Admin from './pages/Admin'
import AdminShell from './pages/admin2/AdminShell'
import AssignmentsPage from './pages/admin2/AssignmentsPage'
import DashboardPage from './pages/admin2/DashboardPage'
import FeedbackPage from './pages/admin2/FeedbackPage'
import Placeholder from './pages/admin2/Placeholder'
import PeoplePage from './pages/admin2/PeoplePage'
import UserDetailPage from './pages/admin2/UserDetailPage'
import Assessment from './pages/Assessment'
import AuthCallback from './pages/AuthCallback'
import InviteRedirect from './pages/InviteRedirect'
import JourneyHome from './pages/JourneyHome'
import LearningPathNew from './pages/LearningPathNew'
import LessonPage from './pages/LessonPage'
import Login from './pages/Login'
import SetPassword from './pages/SetPassword'

function ComingSoon() {
  const navigate = useNavigate()
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16, background: '#fff' }}>
      <p style={{ fontSize: 17, fontWeight: 300, color: '#8A8A8A', margin: 0 }}>This component is coming soon.</p>
      <button
        style={{ background: 'none', border: '1px solid #E2E2E2', borderRadius: 999, padding: '9px 20px', cursor: 'pointer', fontSize: 14, color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)' }}
        onClick={() => navigate('/')}
      >
        ← Back to hub
      </button>
    </div>
  )
}

// React Router v6 keeps the window scroll offset across navigations, so a route
// like /learning could open mid-page (whatever you'd scrolled to before). Reset
// to the top on every path change; useLayoutEffect runs before paint (no flash).
function ScrollToTop() {
  const { pathname } = useLocation()
  useLayoutEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

function AppRoutes() {
  const { session, role, passwordSet, externalLogin, loading } = useAuth()

  if (loading) return <Spinner fullPage />

  // Old app also gated on isRecovery; that mode is gone (the invite/reset
  // credential is a URL token, not a session). This gate is defensive only —
  // the primary flow never hits it because set-password auto-logs-in with
  // password_set already true. Entra-linked users are exempt: they sign in
  // via Microsoft and may never have a hub password at all.
  const needsPassword = session && passwordSet === false && !externalLogin

  // /interview is ComingSoon in the old app too. Guard semantics are final.
  return (
    <Routes>
      <Route path="/login" element={session ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/set-password" element={<SetPassword />} />
      <Route path="/" element={
        needsPassword
          ? <Navigate to="/set-password" replace />
          : session ? <JourneyHome /> : <Navigate to="/login" replace />
      } />
      <Route path="/admin" element={
        !session ? <Navigate to="/login" replace />
          : role !== 'admin' ? <Navigate to="/" replace />
          : <AdminShell />
      }>
        <Route index element={<DashboardPage />} />
        <Route path="people" element={<PeoplePage />} />
        <Route path="people/:userId" element={<UserDetailPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="feedback" element={<FeedbackPage />} />
        <Route path="projects" element={<Placeholder />} />
        <Route path="templates" element={<Placeholder />} />
        <Route path="setup" element={<Placeholder />} />
      </Route>
      {/* Old panel stays reachable until Phase D cuts over; same guard. */}
      <Route path="/admin-old" element={
        !session ? <Navigate to="/login" replace />
          : role !== 'admin' ? <Navigate to="/" replace />
          : <Admin />
      } />
      <Route path="/assessment" element={session ? <Assessment /> : <Navigate to="/login" replace />} />
      {/* Redesign is the working page; it carries the admin edit mode too. The
          old graph page (/learning/old) + ModulePopup were removed 2026-07-09. */}
      <Route path="/learning" element={session ? <LearningPathNew /> : <Navigate to="/login" replace />} />
      <Route path="/learning/lesson/:lessonId" element={session ? <LessonPage /> : <Navigate to="/login" replace />} />
      <Route path="/interview" element={session ? <ComingSoon /> : <Navigate to="/login" replace />} />
      <Route path="/invite/:id" element={<InviteRedirect />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="*" element={<Navigate to={needsPassword ? '/set-password' : session ? '/' : '/login'} replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToTop />
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
