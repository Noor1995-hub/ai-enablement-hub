import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LessonEditor from './LessonEditor'

const clientMock = vi.hoisted(() => ({ PATCH: vi.fn(), POST: vi.fn() }))
vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, client: clientMock }
})

const LESSON = {
  id: '11111111-1111-1111-1111-111111111111',
  title: 'Test lesson',
  content_blocks: [{ id: 'p1', type: 'paragraph', text: 'Hello world' }],
}

/** True when a beforeunload listener asks the browser to keep the page. */
function unloadBlocked(): boolean {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event.defaultPrevented
}

describe('LessonEditor unsaved-changes guard', () => {
  beforeEach(() => {
    clientMock.PATCH.mockReset()
    // B5: Save runs the house-style check first; no findings → it saves.
    clientMock.POST.mockReset()
    clientMock.POST.mockResolvedValue({ data: { findings: [] }, error: undefined })
  })

  it('guards once a block is edited and releases the guard after a successful save', async () => {
    clientMock.PATCH.mockResolvedValue({
      data: { title: 'Test lesson', content_blocks: [{ id: 'p1', type: 'paragraph', text: 'Changed' }] },
      error: undefined,
    })
    render(<LessonEditor lesson={LESSON} />)
    expect(unloadBlocked()).toBe(false)

    fireEvent.change(screen.getByDisplayValue('Hello world'), { target: { value: 'Changed' } })
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument()
    expect(unloadBlocked()).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Saved')).toBeInTheDocument()
    expect(unloadBlocked()).toBe(false)
  })

  it('keeps guarding when the save fails', async () => {
    clientMock.PATCH.mockResolvedValue({ data: undefined, error: { error: { message: 'nope' } } })
    render(<LessonEditor lesson={LESSON} />)
    fireEvent.change(screen.getByDisplayValue('Test lesson'), { target: { value: 'Renamed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('nope')).toBeInTheDocument()
    expect(unloadBlocked()).toBe(true)
  })

  it('never guards an embedded instance: its host owns saving and the guard', () => {
    render(<LessonEditor lesson={LESSON} embedded onLiveChange={() => {}} />)
    fireEvent.change(screen.getByDisplayValue('Hello world'), { target: { value: 'Changed' } })
    expect(unloadBlocked()).toBe(false)
  })
})

describe('LessonEditor guarded save (B5)', () => {
  const BASE = '2026-10-05T12:00:00+00:00'
  beforeEach(() => {
    clientMock.PATCH.mockReset()
    clientMock.POST.mockReset()
    clientMock.POST.mockResolvedValue({ data: { findings: [] }, error: undefined })
    clientMock.PATCH.mockResolvedValue({
      data: { ...LESSON, sort_order: 0, module_id: 'm', updated_at: '2026-10-05T12:05:00+00:00', content_blocks: [{ id: 'p1', type: 'paragraph', text: 'Changed' }] },
      error: undefined,
    })
  })

  function edit() {
    fireEvent.change(screen.getByDisplayValue('Hello world'), { target: { value: 'Changed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  }

  it('saves straight away when the check finds nothing, sending the base updated_at', async () => {
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    expect(await screen.findByText('Saved')).toBeInTheDocument()
    expect(clientMock.PATCH.mock.calls[0][1].body.expected_updated_at).toBe(BASE)
  })

  it('shows findings with Save anyway and Keep editing', async () => {
    clientMock.POST.mockResolvedValue({
      data: { findings: [{ severity: 'warning', block_index: 0, where: 'block 1 · paragraph', message: 'em dash in [0].text' }] },
      error: undefined,
    })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    expect(await screen.findByText('em dash in [0].text')).toBeInTheDocument()
    expect(clientMock.PATCH).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Keep editing' }))
    expect(clientMock.PATCH).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Save anyway' }))
    expect(await screen.findByText('Saved')).toBeInTheDocument()
  })

  it('offers Reload or Overwrite on a 409, naming who and when', async () => {
    const onReload = vi.fn()
    clientMock.PATCH.mockResolvedValueOnce({
      data: undefined,
      error: { error: { code: 'lesson_changed', message: 'm', updated_at: '2026-10-05T14:32:00+00:00', updated_by_name: 'Aaron Neuville' } },
    })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} onReload={onReload} />)
    edit()
    expect(await screen.findByText(/Aaron Neuville changed this lesson/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Overwrite with mine' }))
    expect(await screen.findByText('Saved')).toBeInTheDocument()
    expect(clientMock.PATCH.mock.calls[1][1].body.expected_updated_at).toBe('2026-10-05T14:32:00+00:00')
  })

  it('a second conflict after overwrite shows again', async () => {
    const conflict = (name: string, at: string) => ({ data: undefined, error: { error: { code: 'lesson_changed', message: 'm', updated_at: at, updated_by_name: name } } })
    clientMock.PATCH
      .mockResolvedValueOnce(conflict('Aaron Neuville', '2026-10-05T14:32:00+00:00'))
      .mockResolvedValueOnce(conflict('Bea Third', '2026-10-05T14:40:00+00:00'))
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    fireEvent.click(await screen.findByRole('button', { name: 'Overwrite with mine' }))
    expect(await screen.findByText(/Bea Third changed this lesson/)).toBeInTheDocument()
  })

  it('names "Someone" when the editor is unknown, and Reload calls back', async () => {
    const onReload = vi.fn()
    clientMock.PATCH.mockResolvedValueOnce({
      data: undefined,
      error: { error: { code: 'lesson_changed', message: 'm', updated_at: '2026-10-05T14:32:00+00:00', updated_by_name: null } },
    })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} onReload={onReload} />)
    edit()
    expect(await screen.findByText(/Someone changed this lesson/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reload their version' }))
    expect(onReload).toHaveBeenCalled()
  })

  it('embedded editor never calls check', () => {
    render(<LessonEditor lesson={LESSON} embedded />)
    fireEvent.change(screen.getByDisplayValue('Hello world'), { target: { value: 'x' } })
    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull()
    expect(clientMock.POST).not.toHaveBeenCalled()
  })
  it('Save anyway saves what is on screen now, including edits made while the panel was open', async () => {
    clientMock.POST.mockResolvedValue({
      data: { findings: [{ severity: 'warning', block_index: 0, where: 'block 1 · paragraph', message: 'em dash in [0].text' }] },
      error: undefined,
    })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    await screen.findByText('em dash in [0].text')
    fireEvent.change(screen.getByDisplayValue('Changed'), { target: { value: 'Fixed while the panel was open' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save anyway' }))
    await screen.findByText('Saved')
    expect(clientMock.PATCH.mock.calls[0][1].body.content_blocks[0].text).toBe('Fixed while the panel was open')
  })

  it('a failed check never blocks the save', async () => {
    clientMock.POST.mockResolvedValue({ data: undefined, error: { error: { code: 'internal_error', message: 'boom' } } })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    expect(await screen.findByText(/couldn't run the checks/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save anyway' }))
    expect(await screen.findByText('Saved')).toBeInTheDocument()
  })
  it('a save that cannot reach the server shows an error and lets you save again', async () => {
    clientMock.PATCH.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    expect(await screen.findByText('The save could not be reached. Please try again.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()
  })
})
