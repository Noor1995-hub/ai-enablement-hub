interface ProgressBarProps {
  completed: number
  total: number
}

/** Text label + bar — accessibility rule: progress is never color-only, so
 * the "x/y (z%)" text always renders alongside the fill.
 * Prototype: docs/design-prototypes/admin-redesign/common.js
 * `progressBar()` / styles.css `.progress`. */
export function ProgressBar({ completed, total }: ProgressBarProps) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0
  return (
    <div className="adm-progress">
      <div className="adm-progress-track">
        {/* Fill width is the one inline style here — a bar's width is
            inherently per-instance data, not component "look". */}
        <div className="adm-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="adm-progress-label">
        {completed}/{total} ({pct}%)
      </span>
    </div>
  )
}
