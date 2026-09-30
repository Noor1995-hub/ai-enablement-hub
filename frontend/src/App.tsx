import { lazy, Suspense, useLayoutEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { RoutedErrorBoundary } from './components/ErrorBoundary'
import Spinner from './components/Spinner'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Assessment from './pages/Assessment'
import AuthCallback from './pages/AuthCallback'
import Interview from './pages/Interview'
import InviteRedirect from './pages/InviteRedirect'
import JourneyHome from './pages/JourneyHome'
import LearningPathNew from './pages/LearningPathNew'
import LessonPage from './pages/LessonPage'
import Login from './pages/Login'
import SetPassword from './pages/SetPassword'

// The admin panel is admin-only and pulls in @tanstack/react-query plus
// styles/admin.css. Loading it lazily keeps all of that out of the bundle every
// LEARNER downloads to read a lesson. AdminShell renders its own <Suspense>
// around <Outlet/>, so switching admin sections swaps only the content area;
// this outer boundary covers the shell chunk itself. A chunk that fails to load
// throws into RoutedErrorBoundary, which reloads the page (chunkLoadError.ts).
const AdminShell = lazy(() => import('./pages/admin2/AdminShell'))
const AssignmentsPage = lazy(() => import('./pages/admin2/AssignmentsPage'))
const ContentImprovementPage = lazy(() => import('./pages/admin2/ContentImprovementPage'))
const DashboardPage = lazy(() => import('./pages/admin2/DashboardPage'))
const FeedbackPage = lazy(() => import('./pages/admin2/FeedbackPage'))
const PeoplePage = lazy(() => import('./pages/admin2/PeoplePage'))
const ProjectsPage = lazy(() => import('./pages/admin2/ProjectsPage'))
const PromptsPage = lazy(() => import('./pages/admin2/PromptsPage'))
const SetupPage = lazy(() => import('./pages/admin2/SetupPage'))
const TemplatesPage = lazy(() => import('./pages/admin2/TemplatesPage'))
const UserDetailPage = lazy(() => import('./pages/admin2/UserDetailPage'))
// Admin-only ChatPanel harness (see the route comment below).
const DevChat = lazy(() => import('./pages/DevChat'))

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
          : <Suspense fallback={<Spinner fullPage />}><AdminShell /></Suspense>
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
          : <Suspense fallback={<Spinner fullPage />}><DevChat /></Suspense>
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
        <RoutedErrorBoundary>
          <AppRoutes />
        </RoutedErrorBoundary>
      </BrowserRouter>
    </AuthProvider>
  )
}
