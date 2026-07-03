import AppNav from '../components/AppNav'

// Batch 4 placeholder — the real JourneyHome (components grid, survey CTA,
// progress stepper) ports in Batch 5. This exists so the auth spine has a
// signed-in landing page with a working nav (name, admin link, sign out).
export default function JourneyHome() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#fff' }}>
      <AppNav />
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ fontSize: 17, fontWeight: 300, color: '#8A8A8A', margin: 0 }}>
          You're signed in. The journey home page lands in Batch 5.
        </p>
      </div>
    </div>
  )
}
