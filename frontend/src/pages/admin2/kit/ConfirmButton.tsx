import { useState } from 'react'
import { Spinner } from './Spinner'

interface ConfirmButtonProps {
  label: string
  confirmLabel: string
  onConfirm: () => void
  busy?: boolean
}

/** Two-step in-place confirm — click once to arm, click again (or Cancel to
 * back out). Never `window.confirm`: a native dialog reads as an
 * out-of-app interruption (the same call made for ModulePanel's
 * delete-module confirm in the old panel). */
export function ConfirmButton({ label, confirmLabel, onConfirm, busy = false }: ConfirmButtonProps) {
  const [armed, setArmed] = useState(false)

  if (!armed) {
    return (
      <button
        type="button"
        className="adm-btn adm-btn-ghost adm-btn-danger adm-btn-sm"
        onClick={() => setArmed(true)}
      >
        {label}
      </button>
    )
  }

  return (
    <span className="adm-confirm">
      <button type="button" className="adm-btn adm-btn-red adm-btn-sm" onClick={onConfirm} disabled={busy}>
        {busy && <Spinner size="sm" />}
        {confirmLabel}
      </button>
      <button
        type="button"
        className="adm-btn adm-btn-subtle adm-btn-sm"
        onClick={() => setArmed(false)}
        disabled={busy}
      >
        Cancel
      </button>
    </span>
  )
}
