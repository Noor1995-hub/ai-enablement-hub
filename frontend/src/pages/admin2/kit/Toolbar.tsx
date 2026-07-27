import type { ReactNode } from 'react'

interface ToolbarProps {
  children: ReactNode
}

/** The search + filter-pills row above a table/list. Content (search box,
 * pills, selects) is caller-supplied — style it with the `adm-search` /
 * `adm-pills` / `adm-pill` / `adm-select-look` classes added alongside this
 * component. Prototype: docs/design-prototypes/admin-redesign/styles.css
 * `.toolbar`. */
export function Toolbar({ children }: ToolbarProps) {
  return <div className="adm-toolbar">{children}</div>
}
