import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ExportModal from './ExportModal'

const api = vi.hoisted(() => ({
  fetchProjectExport: vi.fn(),
  saveFile: vi.fn(),
}))
vi.mock('../../api/projectExport', () => api)

function renderModal(onClose = vi.fn()) {
  render(<ExportModal projectId="p-1" projectName="Acme · Rollout" onClose={onClose} />)
  return onClose
}

describe('ExportModal', () => {
  beforeEach(() => {
    api.fetchProjectExport.mockReset()
    api.saveFile.mockReset()
  })

  it('ticks everything but the interview, and warns about personal data', () => {
    renderModal()

    expect(screen.getByRole('checkbox', { name: /^People/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /^Assessment/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /^Progress/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /^Interview/ })).not.toBeChecked()
    expect(screen.getByRole('note')).toHaveTextContent(/personal data/)
  })

  it('downloads the ticked sections in sheet order, then closes', async () => {
    const file = { blob: new Blob(), filename: 'x.xlsx' }
    api.fetchProjectExport.mockResolvedValue(file)
    const onClose = renderModal()

    fireEvent.click(screen.getByRole('checkbox', { name: /^Interview/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /^Assessment/ }))
    fireEvent.click(screen.getByRole('button', { name: /Download/ }))

    await waitFor(() => expect(onClose).toHaveBeenCalled())
    expect(api.fetchProjectExport).toHaveBeenCalledWith('p-1', ['people', 'progress', 'interview'])
    expect(api.saveFile).toHaveBeenCalledWith(file)
  })

  it('cannot download with nothing ticked', () => {
    renderModal()

    for (const name of [/^People/, /^Assessment/, /^Progress/]) {
      fireEvent.click(screen.getByRole('checkbox', { name }))
    }

    expect(screen.getByRole('button', { name: /Download/ })).toBeDisabled()
  })

  it('shows the error and stays open when the export fails', async () => {
    api.fetchProjectExport.mockRejectedValue(new Error('Project not found'))
    const onClose = renderModal()

    fireEvent.click(screen.getByRole('button', { name: /Download/ }))

    expect(await screen.findByText('Project not found')).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
    expect(api.saveFile).not.toHaveBeenCalled()
  })
})
