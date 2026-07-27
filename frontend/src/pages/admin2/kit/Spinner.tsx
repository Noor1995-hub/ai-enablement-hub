interface SpinnerProps {
  size?: 'sm' | 'md'
}

/** CSS-driven adaptation of the app's existing spinner
 * (frontend/src/components/Spinner.tsx) — same red-arc-on-grey-track look,
 * but sized via `adm-` classes instead of inline CSSProperties, so it can
 * also sit inline (e.g. inside ConfirmButton while a mutation is in
 * flight). `size` defaults to the standalone block size; screens needing a
 * full-page variant wrap this in their own centering container. */
export function Spinner({ size = 'md' }: SpinnerProps = {}) {
  return (
    <span className={`adm-spinner adm-spinner-${size}`} role="status" aria-label="Loading">
      <svg viewBox="0 0 32 32" fill="none" width="100%" height="100%">
        <circle cx={16} cy={16} r={13} className="adm-spinner-track" fill="none" />
        <circle cx={16} cy={16} r={13} className="adm-spinner-arc" fill="none" />
      </svg>
    </span>
  )
}
