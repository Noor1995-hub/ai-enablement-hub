import { useEffect, useRef, type ReactNode } from 'react'

interface ModalProps {
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}

// Everything inside the dialog that can hold focus, in DOM order — used both for
// the initial focus target and for wrapping Tab at the ends.
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** Centered overlay dialog — click-outside and Escape both close. Focus moves
 * into the dialog on open, is trapped inside it while open (Tab wraps at both
 * ends), and returns to whatever opened it on close.
 * Prototype: docs/design-prototypes/admin-redesign/styles.css
 * `.modal-overlay` / `.modal`. */
export function Modal({ title, onClose, children, footer }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  // Mount-only: move focus in, and put it back where it came from on unmount.
  // onClose is deliberately not a dependency — re-running this would steal focus
  // back to the first field every time the caller re-renders with a new closure.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    const first = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE)
    ;(first ?? dialogRef.current)?.focus()
    return () => opener?.focus()
  }, [])

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab') return
      const nodes = dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE)
      if (!nodes || nodes.length === 0) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      // Wrap at both ends so Tab can't walk out into the page behind the overlay.
      if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      } else if (e.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
        e.preventDefault()
        last.focus()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div className="adm-modal-overlay" onClick={onClose}>
      <div
        className="adm-modal"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        // Fallback focus target when the dialog has no focusable child yet.
        tabIndex={-1}
        onClick={e => e.stopPropagation()}
      >
        <div className="adm-modal-head">
          <h2 className="adm-modal-title">{title}</h2>
          <button type="button" className="adm-modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="adm-modal-body">{children}</div>
        {footer && <div className="adm-modal-footer">{footer}</div>}
      </div>
    </div>
  )
}
