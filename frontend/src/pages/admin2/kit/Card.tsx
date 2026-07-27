import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

/** Generic bordered panel — the base unit of every admin screen.
 * Prototype: docs/design-prototypes/admin-redesign/styles.css `.card` /
 * `.card-title`. */
export function Card({ title, actions, children, className }: CardProps) {
  return (
    <div className={`adm-card${className ? ` ${className}` : ''}`}>
      {(title !== undefined || actions !== undefined) && (
        <div className="adm-card-title">
          {title}
          {actions && <span className="adm-card-actions">{actions}</span>}
        </div>
      )}
      {children}
    </div>
  )
}
