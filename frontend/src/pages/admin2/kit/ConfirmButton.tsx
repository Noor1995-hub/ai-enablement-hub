import { useEffect, useRef, useState, type FocusEvent } from 'react'
import { Spinner } from './Spinner'

interface ConfirmButtonProps {
  label: string
  confirmLabel: string
  onConfirm: () => void
  busy?: boolean
  /** Unarmed-button styling only. Defaults to 'danger' (the original, only
   * pre-existing caller: "Remove participant"). 'neutral' drops the danger
   * class for actions that are reversible/non-destructive but still worth a
   * confirm step (e.g. "Draft proposals" — spends tokens, doesn't publish
   * anything). The armed confirm/cancel pair is unaffected by this prop:
   * armed always means "you are about to do this", so red stays red there
   * for both tones. */
  tone?: 'danger' | 'neutral'
}

const DISARM_DELAY_MS = 150

/** Two-step in-place confirm — click once to arm, click again (or Cancel to
 * back out). Never `window.confirm`: a native dialog reads as an
 * out-of-app interruption (the same call made for ModulePanel's
 * delete-module confirm in the old panel).
 *
 * Armed state also disarms on blur: if focus leaves the Confirm/Cancel pair
 * entirely (a stray click elsewhere while this row is still mounted) a short
 * timer resets to the unarmed button, so a later click can't land on a
 * still-armed Confirm and fire `onConfirm` unexpectedly. Focus moving
 * *within* the pair (Confirm ↔ Cancel) cancels the pending disarm. */
export function ConfirmButton({ label, confirmLabel, onConfirm, busy = false, tone = 'danger' }: ConfirmButtonProps) {
  const [armed, setArmed] = useState(false)
  const disarmTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(
    () => () => {
      if (disarmTimer.current) clearTimeout(disarmTimer.current)
    },
    [],
  )

  // A mutation going into flight disables both buttons, which blurs whichever one held
  // focus — that's not a "clicked away" signal, so cancel (rather than let a stale timer
  // fire) any disarm already pending from before `busy` flipped true.
  useEffect(() => {
    if (busy && disarmTimer.current) {
      clearTimeout(disarmTimer.current)
      disarmTimer.current = null
    }
  }, [busy])

  function handleBlur(e: FocusEvent<HTMLSpanElement>) {
    // Disabling the focused button (busy=true) fires this same blur — disabled buttons
    // can't be clicked, so there's nothing to guard against; arming the disarm timer here
    // would revert to the unarmed, enabled label button mid-mutation.
    if (busy) return
    // relatedTarget is the element gaining focus (null if focus leaves the
    // document, e.g. a click on a non-focusable area) — only disarm when
    // it's outside this Confirm/Cancel pair.
    if (e.currentTarget.contains(e.relatedTarget as Node | null)) return
    disarmTimer.current = setTimeout(() => setArmed(false), DISARM_DELAY_MS)
  }

  function handleFocus() {
    if (disarmTimer.current) {
      clearTimeout(disarmTimer.current)
      disarmTimer.current = null
    }
  }

  if (!armed) {
    return (
      <button
        type="button"
        className={`adm-btn adm-btn-ghost${tone === 'danger' ? ' adm-btn-danger' : ''} adm-btn-sm`}
        onClick={() => setArmed(true)}
      >
        {label}
      </button>
    )
  }

  return (
    <span className="adm-confirm" onBlur={handleBlur} onFocus={handleFocus}>
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
