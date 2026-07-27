import { useEffect, type ReactNode } from 'react'

interface ModalProps {
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}

/** Centered overlay dialog — click-outside and Escape both close.
 * Prototype: docs/design-prototypes/admin-redesign/styles.css
 * `.modal-overlay` / `.modal`. */
export function Modal({ title, onClose, children, footer }: ModalProps) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div className="adm-modal-overlay" onClick={onClose}>
      <div
        className="adm-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
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
