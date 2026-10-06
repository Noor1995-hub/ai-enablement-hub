import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MediaPage from './MediaPage'

const clientMock = vi.hoisted(() => ({ GET: vi.fn(), DELETE: vi.fn() }))
vi.mock('../../api/client', async importOriginal => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, client: clientMock }
})

const USED = `images/${'a'.repeat(32)}.png`
const UNUSED = `videos/${'b'.repeat(32)}.mp4`
const LIBRARY = {
  total_bytes: 4 * 1_048_576,
  files: [
    {
      path: USED, kind: 'image', size_bytes: 1_048_576, uploaded_at: '2026-10-01T10:00:00Z',
      preview_url: 'https://blob/x.png?sas', used_in: [{ lesson_id: 'l1', lesson_title: 'Ask clearly', module_title: 'Basics' }],
      proposals: 0,
    },
    {
      path: UNUSED, kind: 'video', size_bytes: 3 * 1_048_576, uploaded_at: '2026-10-02T10:00:00Z',
      preview_url: null, used_in: [], proposals: 0,
    },
  ],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter><MediaPage /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MediaPage', () => {
  beforeEach(() => {
    clientMock.GET.mockReset()
    clientMock.DELETE.mockReset()
    clientMock.GET.mockResolvedValue({ data: structuredClone(LIBRARY) })
    clientMock.DELETE.mockResolvedValue({ data: undefined, error: undefined })
  })

  it('summarises the library and shows where each file is used', async () => {
    renderPage()
    expect(await screen.findByText('2 files · 4 MB · 1 unused (3 MB)')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ask clearly' })).toHaveAttribute('href', '/learning/lesson/l1?edit=true')
    expect(screen.getByText('Not used anywhere')).toBeInTheDocument()
  })

  it('offers delete only on unused files, and filters to unused', async () => {
    renderPage()
    await screen.findByText('Ask clearly')
    expect(screen.getAllByRole('button', { name: 'Delete' })).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Unused' }))
    expect(screen.queryByText('Ask clearly')).toBeNull()
  })

  it('deletes an unused file after a second click', async () => {
    renderPage()
    await screen.findByText('Ask clearly')
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(clientMock.DELETE).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))
    await waitFor(() =>
      expect(clientMock.DELETE).toHaveBeenCalledWith('/api/admin/media/{kind}/{name}', {
        params: { path: { kind: 'videos', name: `${'b'.repeat(32)}.mp4` } },
      }),
    )
  })

  it('shows a refused delete (file now in use)', async () => {
    clientMock.DELETE.mockResolvedValue({ data: undefined, error: { error: { code: 'conflict', message: 'This file is still used in: Intro' } } })
    renderPage()
    await screen.findByText('Ask clearly')
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))
    expect(within(await screen.findByRole('alert')).getByText('This file is still used in: Intro')).toBeInTheDocument()
  })
})
