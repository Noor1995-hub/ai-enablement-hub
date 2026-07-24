import type { ReactNode } from 'react'

interface BulkBarProps {
  count: number
  children: ReactNode
  onClear: () => void
}

/** Sticky bottom bar for row-selection bulk actions (`children` = the action
 * buttons); renders nothing when nothing is selected.
 * Prototype: docs/design-prototypes/admin-redesign/styles.css `.bulkbar`. */
export function BulkBar({ count, children, onClear }: BulkBarProps) {
  if (count === 0) return null
  return (
    <div className="adm-bulkbar">
      <span className="adm-bulkbar-count">{count} selected</span>
      <div className="adm-bulkbar-actions">{children}</div>
      <button type="button" className="adm-bulkbar-close" onClick={onClear} aria-label="Clear selection">
        ✕
      </button>
    </div>
  )
}
