export default function Spinner({ fullPage = false }: { fullPage?: boolean }) {
  return (
    <div style={{
      ...(fullPage ? { minHeight: '100vh' } : { height: '100%', flex: 1 }),
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
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
