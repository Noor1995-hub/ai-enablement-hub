interface EmptyStateProps {
  title: string
  hint?: string
}

/** Standard "nothing here" block — every Phase C screen renders this instead
 * of ad hoc empty copy. Prototype: docs/design-prototypes/admin-redesign
 * styles.css `.empty`. */
export function EmptyState({ title, hint }: EmptyStateProps) {
  return (
    <div className="adm-empty">
      <p className="adm-empty-title">{title}</p>
      {hint && <p className="adm-empty-hint">{hint}</p>}
    </div>
  )
}
