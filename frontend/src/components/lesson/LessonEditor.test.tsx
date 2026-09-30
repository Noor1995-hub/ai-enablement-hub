import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LessonEditor from './LessonEditor'

const clientMock = vi.hoisted(() => ({ PATCH: vi.fn() }))
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
