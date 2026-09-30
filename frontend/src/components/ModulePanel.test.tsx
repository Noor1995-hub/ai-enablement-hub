import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ModulePanel from './ModulePanel'

const clientMock = vi.hoisted(() => ({ GET: vi.fn(), DELETE: vi.fn() }))
vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, client: clientMock }
})

function renderPanel() {
  return render(
    <MemoryRouter>
      <ModulePanel moduleId="m1" moduleName="Mod" onClose={vi.fn()} onDeleted={vi.fn()} />
    </MemoryRouter>,
  )
}

describe('ModulePanel lesson delete confirmation', () => {
  let confirmSpy: ReturnType<typeof vi.spyOn>
  beforeEach(() => {
    clientMock.GET.mockReset().mockResolvedValue({
      data: { lessons: [{ id: 'l1', title: 'Lesson one', sort_order: 0 }] },
    })
    clientMock.DELETE.mockReset().mockResolvedValue({ error: undefined })
    confirmSpy = vi.spyOn(window, 'confirm')
  })
  afterEach(() => {
    expect(confirmSpy).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('does not delete on the first click', async () => {
    renderPanel()
    fireEvent.click(await screen.findByTitle('Delete lesson'))
    expect(clientMock.DELETE).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
  })

  it('deletes once confirmed and removes the row', async () => {
    renderPanel()
    fireEvent.click(await screen.findByTitle('Delete lesson'))
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(screen.queryByText('Lesson one')).not.toBeInTheDocument())
    expect(clientMock.DELETE).toHaveBeenCalledExactlyOnceWith('/api/admin/lessons/{lesson_id}', {
      params: { path: { lesson_id: 'l1' } },
    })
  })

  it('does not delete when cancelled', async () => {
    renderPanel()
    fireEvent.click(await screen.findByTitle('Delete lesson'))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(clientMock.DELETE).not.toHaveBeenCalled()
    expect(screen.getByTitle('Delete lesson')).toBeInTheDocument()
    expect(screen.getByText('Lesson one')).toBeInTheDocument()
  })
})
