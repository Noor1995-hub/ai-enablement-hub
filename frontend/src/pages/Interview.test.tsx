import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ts from 'typescript'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Interview from './Interview'
import interviewSource from './Interview.tsx?raw'
import { INTERVIEW_STRINGS } from '../lib/interviewStrings'

const EN = INTERVIEW_STRINGS.en
const NL = INTERVIEW_STRINGS.nl

// The interview endpoints, mocked at the page's own API module.
const api = vi.hoisted(() => ({ getInterviewState: vi.fn(), openInterview: vi.fn(), buildPlaybook: vi.fn() }))
vi.mock('../lib/interviewApi', () => api)

// The shared chat hook, as a plain object each test sets up before rendering.
const chat = vi.hoisted(() => ({
  messages: [] as { role: 'user' | 'assistant'; content: string }[],
  loading: false,
  error: null as string | null,
  send: vi.fn(),
  loadConversation: vi.fn(),
  loadConversations: vi.fn(),
  startNew: vi.fn(),
  conversations: [],
}))
vi.mock('../lib/useChat', () => ({ useChat: () => chat }))

// The page asks /api/me/journey whether the assessment is done.
const clientMock = vi.hoisted(() => ({ GET: vi.fn() }))
vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, client: clientMock }
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'learner-1', role: 'user', first_name: 'Ada', last_name: 'Lovelace' },
    role: 'user',
    logout: vi.fn(),
  }),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <Interview />
    </MemoryRouter>,
  )
}

/** Six answers: past the fallback floor, so the Build button can be used. */
function longConversation() {
  return Array.from({ length: 6 }, (_, i) => [
    { role: 'assistant' as const, content: `Question ${i + 1}?` },
    { role: 'user' as const, content: `Answer ${i + 1}` },
  ]).flat()
}

beforeEach(() => {
  vi.clearAllMocks()
  chat.messages = []
  chat.loading = false
  chat.error = null
  chat.loadConversation.mockResolvedValue(undefined)
  clientMock.GET.mockResolvedValue({ data: { survey_status: 'complete' }, error: undefined })
  api.getInterviewState.mockResolvedValue({ status: 'not_started', language: 'en' })
})

describe('Interview: the language choice', () => {
  it('switches the welcome copy and <main lang> as soon as Nederlands is picked', async () => {
    renderPage()
    await screen.findByRole('heading', { name: EN.welcomeHeading })
    expect(screen.getByRole('main').getAttribute('lang')).toBe('en')

    fireEvent.click(screen.getByRole('radio', { name: 'Nederlands' }))

    expect(screen.getByRole('heading', { name: NL.welcomeHeading })).toBeTruthy()
    expect(screen.getByRole('button', { name: new RegExp(NL.startButton) })).toBeTruthy()
    expect(screen.getByRole('main').getAttribute('lang')).toBe('nl')
  })

  it('starts the interview in the chosen language', async () => {
    api.openInterview.mockResolvedValue({ conversation_id: 'c1', greeting: 'Hallo', language: 'nl' })
    renderPage()
    fireEvent.click(await screen.findByRole('radio', { name: 'Nederlands' }))
    fireEvent.click(screen.getByRole('button', { name: new RegExp(NL.startButton) }))

    await waitFor(() => expect(api.openInterview).toHaveBeenCalledWith('nl'))
    expect(chat.loadConversation).toHaveBeenCalledWith('c1')
  })

  it("restores an interview's stored language on reload", async () => {
    api.getInterviewState.mockResolvedValue({ status: 'in_progress', language: 'nl', conversation_id: 'c1' })
    chat.messages = [{ role: 'assistant', content: 'Waar werkt u het meest in?' }]
    renderPage()

    expect(await screen.findByText(NL.hintFirstAnswer)).toBeTruthy()
    expect(screen.getByRole('main').getAttribute('lang')).toBe('nl')
    expect(screen.getByRole('button', { name: NL.buildButton })).toBeTruthy()
  })

  it('gives the live region the interview language too (it sits outside <main>)', async () => {
    api.getInterviewState.mockResolvedValue({ status: 'in_progress', language: 'nl', conversation_id: 'c1' })
    chat.messages = [{ role: 'assistant', content: 'Waar werkt u het meest in?' }]
    const { container } = renderPage()

    await screen.findByText(NL.hintFirstAnswer)
    const live = container.querySelector('[aria-live="polite"]')
    expect(live?.getAttribute('lang')).toBe('nl')
    expect(live?.textContent).toBe('Waar werkt u het meest in?')
  })

  it('shows the needs-assessment notice in the interview language', async () => {
    api.getInterviewState.mockResolvedValue({ status: 'in_progress', language: 'nl', conversation_id: 'c1' })
    clientMock.GET.mockResolvedValue({ data: { survey_status: 'in_progress' }, error: undefined })
    renderPage()

    expect(await screen.findByRole('heading', { name: NL.needsAssessmentHeading })).toBeTruthy()
    expect(screen.getByText(NL.needsAssessmentText)).toBeTruthy()
  })
})

describe('Interview: errors in the interview language', () => {
  it('localises a failed opener in Dutch', async () => {
    api.openInterview.mockRejectedValue(new Error('Too many requests, try again in 60 seconds'))
    renderPage()
    fireEvent.click(await screen.findByRole('radio', { name: 'Nederlands' }))
    fireEvent.click(screen.getByRole('button', { name: new RegExp(NL.startButton) }))

    expect((await screen.findByRole('alert')).textContent).toBe(NL.openFailed)
  })

  it("keeps the server's own message in English", async () => {
    api.openInterview.mockRejectedValue(new Error('Too many requests, try again in 60 seconds'))
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: new RegExp(EN.startButton) }))

    expect((await screen.findByRole('alert')).textContent).toBe('Too many requests, try again in 60 seconds')
  })

  it('localises a failed chat turn in Dutch', async () => {
    api.getInterviewState.mockResolvedValue({ status: 'in_progress', language: 'nl', conversation_id: 'c1' })
    chat.messages = [{ role: 'assistant', content: 'Waar werkt u het meest in?' }]
    chat.error = 'Connection lost while streaming the reply.'
    renderPage()

    expect((await screen.findByRole('alert')).textContent).toBe(NL.chatFailed)
  })

  it('localises a failed build in Dutch', async () => {
    api.getInterviewState.mockResolvedValue({ status: 'in_progress', language: 'nl', conversation_id: 'c1' })
    api.buildPlaybook.mockRejectedValue(new Error('Could not build your playbook.'))
    chat.messages = longConversation()
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: NL.buildButton }))

    expect((await screen.findByRole('alert')).textContent).toBe(NL.buildFailed)
  })
})

/** Every user-visible literal in Interview.tsx, found with the TypeScript parser: JSX text,
 *  literal text attributes, and string literals that read as prose. */
function visibleLiterals() {
  const file = ts.createSourceFile('Interview.tsx', interviewSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const jsxText: string[] = []
  const attributes: string[] = []
  const prose: string[] = []
  const visit = (node: ts.Node) => {
    if (ts.isJsxText(node) && /\p{L}{2,}/u.test(node.text.replace(/&[a-z]+;/g, ''))) jsxText.push(node.text.trim())
    if (ts.isJsxAttribute(node) && node.initializer && ts.isStringLiteral(node.initializer)
      && ['aria-label', 'title', 'placeholder', 'alt'].includes(node.name.getText(file))) {
      attributes.push(`${node.name.getText(file)}="${node.initializer.text}"`)
    }
    // A capitalised literal of three words or more is prose, not a style value or an id.
    if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) && /^[A-Z]\S* \S+ \S+/.test(node.text)) {
      prose.push(node.text)
    }
    ts.forEachChild(node, visit)
  }
  visit(file)
  return { jsxText, attributes, prose }
}

describe('Interview.tsx house-style guard', () => {
  const found = visibleLiterals()

  it('has no hard-coded words between JSX tags: every visible text comes from the dictionary', () => {
    expect(found.jsxText).toEqual([])
  })

  it('has no hard-coded sentences in string literals (labels, fallbacks, errors)', () => {
    expect(found.prose).toEqual([])
  })

  it('names no visible text in literal attributes, apart from the flagged AppNav title', () => {
    // AppNav is shared with the rest of the hub, which is English only; flagged, not changed.
    expect(found.attributes).toEqual(['title="Interview"'])
  })
})
