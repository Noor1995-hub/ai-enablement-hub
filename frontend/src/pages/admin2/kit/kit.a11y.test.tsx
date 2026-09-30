import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Modal } from './Modal'
import { Table } from './Table'

function Harness() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button onClick={() => setOpen(true)}>Open</button>
      {open && (
        <Modal title="Invite" onClose={() => setOpen(false)} footer={<button>Save</button>}>
          <input aria-label="Email" />
        </Modal>
      )}
    </>
  )
}

// fireEvent returns false when the handler called preventDefault — i.e. the trap took over.
const tab = (shift = false) => fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Tab', shiftKey: shift })

describe('Modal focus management', () => {
  it('focuses the first focusable element on open', () => {
    render(<Harness />)
    fireEvent.click(screen.getByText('Open'))
    // DOM order: header close button comes first.
    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus()
  })

  it('wraps Tab from the last element to the first, and Shift+Tab back', () => {
    render(<Harness />)
    fireEvent.click(screen.getByText('Open'))
    screen.getByRole('button', { name: 'Save' }).focus()
    expect(tab()).toBe(false)
    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus()
    expect(tab(true)).toBe(false)
    expect(screen.getByRole('button', { name: 'Save' })).toHaveFocus()
  })

  it('leaves Tab alone in the middle of the dialog', () => {
    render(<Harness />)
    fireEvent.click(screen.getByText('Open'))
    screen.getByLabelText('Email').focus()
    expect(tab()).toBe(true)
    expect(tab(true)).toBe(true)
  })

  it('closes on Escape and returns focus to the opener', () => {
    render(<Harness />)
    const opener = screen.getByText('Open')
    opener.focus()
    fireEvent.click(opener)
    expect(opener).not.toHaveFocus() // focus moved into the dialog, so restoring it is observable
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(opener).toHaveFocus()
  })
})

describe('Table keyboard rows', () => {
  const rows = [{ id: 'a' }, { id: 'b' }]
  const columns = [{ key: 'id', header: 'ID', render: (r: { id: string }) => r.id }]

  it('makes clickable rows tabbable and activates on Enter and Space', () => {
    const onRowClick = vi.fn()
    render(<Table columns={columns} rows={rows} rowKey={r => r.id} onRowClick={onRowClick} />)
    const row = screen.getByText('a').closest('tr')!
    expect(row).toHaveAttribute('tabindex', '0')
    fireEvent.keyDown(row, { key: 'Enter' })
    fireEvent.keyDown(row, { key: ' ' })
    expect(onRowClick).toHaveBeenCalledTimes(2)
    expect(onRowClick).toHaveBeenCalledWith(rows[0])
  })

  it('ignores keys from a row checkbox and leaves plain rows non-focusable', () => {
    const onRowClick = vi.fn()
    const { rerender } = render(
      <Table columns={columns} rows={rows} rowKey={r => r.id} onRowClick={onRowClick} selectable onSelect={() => {}} />,
    )
    fireEvent.keyDown(screen.getAllByLabelText('Select row')[0], { key: ' ' })
    expect(onRowClick).not.toHaveBeenCalled()
    rerender(<Table columns={columns} rows={rows} rowKey={r => r.id} />)
    expect(screen.getByText('a').closest('tr')).not.toHaveAttribute('tabindex')
  })
})
