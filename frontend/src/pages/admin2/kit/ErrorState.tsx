interface ErrorStateProps {
  message: string
  onRetry?: () => void
}

/** Standard query-failure block — every Phase C screen renders this instead
 * of ad hoc error copy; `onRetry` typically calls the query's `refetch`. */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="adm-error">
      <p className="adm-error-message">{message}</p>
      {onRetry && (
        <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}
