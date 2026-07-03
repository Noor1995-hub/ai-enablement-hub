import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import InviteRedirect from './pages/InviteRedirect'
import JourneyHome from './pages/JourneyHome'
import Login from './pages/Login'
import SetPassword from './pages/SetPassword'

function Spinner() {
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

function AppRoutes() {
  const { session, role, passwordSet, loading } = useAuth()

  if (loading) return <Spinner />

  // Old app also gated on isRecovery; that mode is gone (the invite/reset
  // credential is a URL token, not a session). This gate is defensive only —
  // the primary flow never hits it because set-password auto-logs-in with
  // password_set already true.
  const needsPassword = session && passwordSet === false

  // /admin, /assessment, /learning(+lesson) and /interview render ComingSoon
  // until Batches 5–6 port the real pages; the guard semantics are final.
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
          : <ComingSoon />
      } />
      <Route path="/assessment" element={session ? <ComingSoon /> : <Navigate to="/login" replace />} />
      <Route path="/learning" element={session ? <ComingSoon /> : <Navigate to="/login" replace />} />
      <Route path="/learning/lesson/:lessonId" element={session ? <ComingSoon /> : <Navigate to="/login" replace />} />
      <Route path="/interview" element={session ? <ComingSoon /> : <Navigate to="/login" replace />} />
      <Route path="/invite/:id" element={<InviteRedirect />} />
      <Route path="*" element={<Navigate to={needsPassword ? '/set-password' : session ? '/' : '/login'} replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
