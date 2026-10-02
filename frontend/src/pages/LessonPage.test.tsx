import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LessonPage from './LessonPage'
import * as mdxParser from '../lib/mdxParser'

const LESSON_ID = '11111111-1111-1111-1111-111111111111'
const MODULE_ID = '22222222-2222-2222-2222-222222222222'

// client.GET is hit for two endpoints from this page (lesson detail, module
// lesson list); route on the templated path openapi-fetch is called with.
const clientMock = vi.hoisted(() => ({ GET: vi.fn(), PATCH: vi.fn() }))
vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, client: clientMock }
})

const authState = vi.hoisted(() => ({ role: 'user' as string }))
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'learner-1', role: authState.role, first_name: 'Ada', last_name: 'Lovelace' },
    role: authState.role,
    isPowerAdmin: authState.role === 'admin',
    adminProjectIds: [],
    logout: vi.fn(),
  }),
}))

function lessonBody(overrides: Record<string, unknown> = {}) {
  return {
    id: LESSON_ID,
    module_id: MODULE_ID,
    title: 'Test lesson',
    sort_order: 1,
    content_blocks: [{ id: 'p1', type: 'paragraph', text: 'Hello world' }],
    module: { id: MODULE_ID, title: 'Test module' },
    my_answers: null,
    next_lesson_id: null,
    next_module_id: null,
    ...overrides,
  }
}

function mockLessonResponse(result: { data?: unknown; status?: number; error?: unknown }) {
  clientMock.GET.mockImplementation((path: string) => {
    if (path === '/api/lessons/{lesson_id}') {
      return Promise.resolve({
        data: result.data,
        error: result.error,
        response: { status: result.status ?? 200 },
      })
    }
    if (path === '/api/modules/{module_id}/lessons') {
      return Promise.resolve({ data: { lessons: [] }, error: undefined, response: { status: 200 } })
    }
    throw new Error(`unexpected client.GET call: ${path}`)
  })
}

function renderLessonPage(url = `/learning/lesson/${LESSON_ID}`) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/learning/lesson/:lessonId" element={<LessonPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LessonPage load failures', () => {
  beforeEach(() => {
    authState.role = 'user'
    clientMock.GET.mockReset()
  })

  it('shows the server message on a 403', async () => {
    mockLessonResponse({
      status: 403,
      error: { error: { code: 'lesson_not_accessible', message: 'This lesson is not available on your learning path' } },
    })
    renderLessonPage()

    expect(await screen.findByText('This lesson is not available on your learning path')).toBeInTheDocument()
    expect(screen.queryByText('Lesson not found.')).not.toBeInTheDocument()
    expect(screen.queryByText("We couldn't load this lesson.")).not.toBeInTheDocument()
  })

  it('shows "Lesson not found" on a 404', async () => {
    mockLessonResponse({ status: 404 })
    renderLessonPage()

    expect(await screen.findByText('Lesson not found.')).toBeInTheDocument()
    expect(screen.queryByText('Try again')).not.toBeInTheDocument()
  })

  it('shows a generic failure with a retry option on other errors (e.g. 500)', async () => {
    mockLessonResponse({ status: 500 })
    renderLessonPage()

    expect(await screen.findByText("We couldn't load this lesson.")).toBeInTheDocument()
    expect(screen.getByText('Try again')).toBeInTheDocument()
  })

  it('shows the same generic failure when the fetch itself rejects (offline, no response at all)', async () => {
    // openapi-fetch re-throws a rejected fetch rather than resolving with some
    // sentinel status — this is the case a bare "!data" check on a resolved
    // response can never catch; load() must catch the rejection itself.
    clientMock.GET.mockImplementation((path: string) => {
      if (path === '/api/lessons/{lesson_id}') return Promise.reject(new TypeError('Failed to fetch'))
      return Promise.resolve({ data: { lessons: [] }, error: undefined, response: { status: 200 } })
    })
    renderLessonPage()

    expect(await screen.findByText("We couldn't load this lesson.")).toBeInTheDocument()
    expect(screen.getByText('Try again')).toBeInTheDocument()
  })

  it('recovers on "Try again" once the retried fetch succeeds', async () => {
    let call = 0
    clientMock.GET.mockImplementation((path: string) => {
      if (path === '/api/lessons/{lesson_id}') {
        call += 1
        if (call === 1) return Promise.resolve({ data: undefined, error: undefined, response: { status: 500 } })
        return Promise.resolve({ data: lessonBody(), error: undefined, response: { status: 200 } })
      }
      return Promise.resolve({ data: { lessons: [] }, error: undefined, response: { status: 200 } })
    })
    renderLessonPage()

    const retry = await screen.findByText('Try again')
    fireEvent.click(retry)

    expect(await screen.findByText('Test lesson')).toBeInTheDocument()
    expect(screen.queryByText("We couldn't load this lesson.")).not.toBeInTheDocument()
  })
})

describe('LessonPage ?edit=true admin gate', () => {
  beforeEach(() => {
    clientMock.GET.mockReset()
    mockLessonResponse({ data: lessonBody() })
  })

  it('gives a non-admin no editor even with ?edit=true in the URL', async () => {
    authState.role = 'user'
    renderLessonPage(`/learning/lesson/${LESSON_ID}?edit=true`)

    await screen.findByText('Test lesson')
    expect(screen.queryByText('Edit content')).not.toBeInTheDocument()
    expect(screen.queryByText('MDX')).not.toBeInTheDocument()
    expect(screen.queryByText('Hello world')).toBeInTheDocument()
  })

  it('lets an admin open straight into the editor from a ?edit=true deep link', async () => {
    authState.role = 'admin'
    renderLessonPage(`/learning/lesson/${LESSON_ID}?edit=true`)

    await screen.findByText('✓ Editing')
  })
})

describe('LessonPage MDX preview parsing', () => {
  beforeEach(() => {
    authState.role = 'admin'
    clientMock.GET.mockReset()
    clientMock.PATCH.mockReset()
    mockLessonResponse({ data: lessonBody() })
  })

  it('re-parses only when the MDX text changes, not on unrelated re-renders', async () => {
    const parse = vi.spyOn(mdxParser, 'parseMdxToBlocks')
    renderLessonPage()
    fireEvent.click(await screen.findByText('MDX'))
    const box = screen.getByPlaceholderText(/Lesson heading/)

    fireEvent.change(box, { target: { value: '# Title\n\nBody text' } })
    expect(await screen.findByText('2 blocks parsed')).toBeInTheDocument()
    const afterTyping = parse.mock.calls.length

    // Unrelated state changes (mdxSaving, then mdxError) re-render the page.
    // saveMdx itself parses once to build its payload; the preview must not.
    clientMock.PATCH.mockResolvedValue({ data: undefined, error: { error: { message: 'nope' } } })
    fireEvent.click(screen.getByText('Save as blocks'))
    expect(await screen.findByText('nope')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Save as blocks')).toBeInTheDocument())
    expect(parse.mock.calls.length).toBe(afterTyping + 1)

    // A real text change does re-parse.
    fireEvent.change(box, { target: { value: '# Title\n\nBody text\n\n> Callout' } })
    expect(await screen.findByText('3 blocks parsed')).toBeInTheDocument()
    expect(parse.mock.calls.length).toBe(afterTyping + 2)
    parse.mockRestore()
  })
})

/** True when a beforeunload listener asks the browser to keep the page. */
function unloadBlocked(): boolean {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event.defaultPrevented
}

describe('LessonPage MDX pane unsaved-changes guard', () => {
  beforeEach(() => {
    authState.role = 'admin'
    clientMock.GET.mockReset()
    clientMock.PATCH.mockReset()
    mockLessonResponse({ data: lessonBody() })
  })

  it('does not guard a freshly opened pane, only once the MDX is edited', async () => {
    renderLessonPage()
    fireEvent.click(await screen.findByText('MDX'))
    const box = screen.getByPlaceholderText(/Lesson heading/) as HTMLTextAreaElement
    // Opening seeds the pane from the lesson; nothing is lost by leaving yet.
    expect(box.value).toContain('Hello world')
    expect(unloadBlocked()).toBe(false)

    fireEvent.change(box, { target: { value: '# Title\n\nBody text' } })
    expect(unloadBlocked()).toBe(true)
  })

  it('releases the guard after "Save as blocks" succeeds', async () => {
    clientMock.PATCH.mockResolvedValue({
      data: { content_blocks: [{ id: 'h1', type: 'heading', text: 'Title', level: 1 }] },
      error: undefined,
    })
    renderLessonPage()
    fireEvent.click(await screen.findByText('MDX'))
    fireEvent.change(screen.getByPlaceholderText(/Lesson heading/), { target: { value: '# Title' } })
    expect(unloadBlocked()).toBe(true)

    fireEvent.click(screen.getByText('Save as blocks'))
    expect(await screen.findByText('✓ Editing')).toBeInTheDocument()
    expect(unloadBlocked()).toBe(false)
  })

  it('keeps guarding when the save fails', async () => {
    clientMock.PATCH.mockResolvedValue({ data: undefined, error: { error: { message: 'nope' } } })
    renderLessonPage()
    fireEvent.click(await screen.findByText('MDX'))
    fireEvent.change(screen.getByPlaceholderText(/Lesson heading/), { target: { value: '# Title' } })
    fireEvent.click(screen.getByText('Save as blocks'))
    expect(await screen.findByText('nope')).toBeInTheDocument()
    expect(unloadBlocked()).toBe(true)
  })

  it('releases the guard on Clear and on leaving the pane', async () => {
    renderLessonPage()
    fireEvent.click(await screen.findByText('MDX'))
    const box = screen.getByPlaceholderText(/Lesson heading/)
    fireEvent.change(box, { target: { value: '# Title' } })
    fireEvent.click(screen.getByText('Clear'))
    expect(unloadBlocked()).toBe(false)

    fireEvent.change(box, { target: { value: '# Title' } })
    expect(unloadBlocked()).toBe(true)
    fireEvent.click(screen.getByText('MDX'))
    expect(unloadBlocked()).toBe(false)
  })

  it('closes the pane when navigating to another lesson, so lesson A MDX cannot be saved into B', async () => {
    const OTHER_ID = '55555555-5555-5555-5555-555555555555'
    render(
      <MemoryRouter initialEntries={[`/learning/lesson/${LESSON_ID}`]}>
        <Link to={`/learning/lesson/${OTHER_ID}`}>Go to lesson B</Link>
        <Routes>
          <Route path="/learning/lesson/:lessonId" element={<LessonPage />} />
        </Routes>
      </MemoryRouter>,
    )
    fireEvent.click(await screen.findByText('MDX'))
    fireEvent.change(screen.getByPlaceholderText(/Lesson heading/), { target: { value: '# Lesson A draft' } })
    expect(unloadBlocked()).toBe(true)

    fireEvent.click(screen.getByText('Go to lesson B'))
    await waitFor(() =>
      expect(clientMock.GET).toHaveBeenCalledWith('/api/lessons/{lesson_id}', expect.objectContaining({
        params: { path: { lesson_id: OTHER_ID } },
      })),
    )
    expect(screen.queryByPlaceholderText(/Lesson heading/)).not.toBeInTheDocument()
    expect(screen.queryByText('Save as blocks')).not.toBeInTheDocument()
    expect(unloadBlocked()).toBe(false)
    expect(clientMock.PATCH).not.toHaveBeenCalled()
  })
})
