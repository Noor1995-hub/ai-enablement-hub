import { useLayoutEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Spinner from './components/Spinner'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import AdminShell from './pages/admin2/AdminShell'
import AssignmentsPage from './pages/admin2/AssignmentsPage'
import ContentImprovementPage from './pages/admin2/ContentImprovementPage'
import DashboardPage from './pages/admin2/DashboardPage'
import FeedbackPage from './pages/admin2/FeedbackPage'
import PeoplePage from './pages/admin2/PeoplePage'
import ProjectsPage from './pages/admin2/ProjectsPage'
import PromptsPage from './pages/admin2/PromptsPage'
import SetupPage from './pages/admin2/SetupPage'
import TemplatesPage from './pages/admin2/TemplatesPage'
import UserDetailPage from './pages/admin2/UserDetailPage'
import Assessment from './pages/Assessment'
import AuthCallback from './pages/AuthCallback'
import DevChat from './pages/DevChat'
import Interview from './pages/Interview'
import InviteRedirect from './pages/InviteRedirect'
import JourneyHome from './pages/JourneyHome'
import LearningPathNew from './pages/LearningPathNew'
import LessonPage from './pages/LessonPage'
import Login from './pages/Login'
import SetPassword from './pages/SetPassword'

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
        <Route path="content-improvement" element={<ContentImprovementPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="prompts" element={<PromptsPage />} />
        <Route path="setup" element={<SetupPage />} />
      </Route>
      <Route path="/assessment" element={session ? <Assessment /> : <Navigate to="/login" replace />} />
      {/* Redesign is the working page; it carries the admin edit mode too. The
          old graph page (/learning/old) + ModulePopup were removed 2026-07-09. */}
      <Route path="/learning" element={session ? <LearningPathNew /> : <Navigate to="/login" replace />} />
      <Route path="/learning/lesson/:lessonId" element={session ? <LessonPage /> : <Navigate to="/login" replace />} />
      <Route path="/interview" element={session ? <Interview /> : <Navigate to="/login" replace />} />
      {/* Temporary Batch A dev-only verification route for the AI chat foundation.
          Admin-only (the AI-enable toggles now live on /admin/projects; this is just
          the ChatPanel harness). Delete once Batch B mounts ChatPanel for real. */}
      <Route path="/dev-chat" element={
        !session ? <Navigate to="/login" replace />
          : role !== 'admin' ? <Navigate to="/" replace />
          : <DevChat />
      } />
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
