import type { ReactNode } from 'react'

export interface TableColumn<T> {
  key: string
  header: ReactNode
  /** Deliberately dynamic per-column sizing (e.g. "40px", "20%") — the one
   * inline style in this component, same rationale as Chip's `dot`. */
  width?: string
  render: (row: T) => ReactNode
}

interface TableProps<T> {
  columns: TableColumn<T>[]
  rows: T[]
  rowKey: (r: T) => string
  onRowClick?: (row: T) => void
  selectable?: boolean
  selected?: Set<string>
  onSelect?: (next: Set<string>) => void
  empty?: ReactNode
}

/** Generic data table with optional row-click and checkbox-select columns.
 * Empty state is the caller's `empty` node (normally an `<EmptyState/>`) —
 * this component never renders its own "no rows" copy.
 * Prototype: docs/design-prototypes/admin-redesign/styles.css `table.data`. */
export function Table<T,>({
  columns,
  rows,
  rowKey,
  onRowClick,
  selectable = false,
  selected,
  onSelect,
  empty,
}: TableProps<T>) {
  if (rows.length === 0 && empty) return <>{empty}</>

  const selectedIds = selected ?? new Set<string>()
  const allSelected = rows.length > 0 && selectedIds.size === rows.length

  function toggleAll() {
    onSelect?.(allSelected ? new Set() : new Set(rows.map(rowKey)))
  }

  function toggleOne(id: string) {
    if (!onSelect) return
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onSelect(next)
  }

  return (
    <table className="adm-table">
      <thead>
        <tr>
          {selectable && (
            <th className="adm-table-check">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Select all rows" />
            </th>
          )}
          {columns.map(col => (
            <th key={col.key} style={col.width ? { width: col.width } : undefined}>
              {col.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(row => {
          const id = rowKey(row)
          const isSelected = selectedIds.has(id)
          return (
            <tr
              key={id}
              className={[
                onRowClick && 'adm-table-row-clickable',
                isSelected && 'adm-table-row-selected',
              ]
                .filter(Boolean)
                .join(' ')}
              // Clickable rows were mouse-only. tabIndex + Enter/Space makes them
              // reachable; the row keeps its native `row` role (an added
              // role="button" would break the table semantics screen readers use
              // to announce column headers).
              tabIndex={onRowClick ? 0 : undefined}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={
                onRowClick
                  ? e => {
                      if (e.target !== e.currentTarget) return // let checkboxes/buttons handle their own keys
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onRowClick(row)
                      }
                    }
                  : undefined
              }
            >
              {selectable && (
                <td className="adm-table-check" onClick={e => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleOne(id)}
                    aria-label="Select row"
                  />
                </td>
              )}
              {columns.map(col => (
                <td key={col.key}>{col.render(row)}</td>
              ))}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
