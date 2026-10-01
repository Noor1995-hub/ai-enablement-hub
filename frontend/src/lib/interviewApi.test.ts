import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { InterviewState, PlaybookShared } from '../types/domain'
import { buildPlaybook, getInterviewState, openInterview } from './interviewApi'

// openapi-fetch binds `fetch` when the client is created, so stub the client's verbs:
// each call's first argument is the schema path openapi-fetch would request.
const clientMock = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn() }))
vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, client: clientMock }
})

const CONVERSATION_ID = '6f1c2d3e-4a5b-4c6d-8e7f-001122334455'

const PLAYBOOK: PlaybookShared = {
  where_you_are_today: 'You run monthly reporting for a client team; it takes two days.',
  use_cases: [
    {
      rank: 1,
      start_here: true,
      name: 'Draft the monthly commentary',
      pain_it_kills: 'Two days of copy-paste every month-end.',
      in_practice: 'Paste the variance table into Copilot and ask for a first draft.',
      before: 'Two days',
      after: 'Half a day',
      impact: 'Frees 1.5 days a month.',
      difficulty: 'Quick Win',
      systems_involved: ['Excel', 'Copilot'],
      assumption_to_check: null,
      cross_functional: false,
    },
  ],
  next_moves: [{ order: 1, move: 'Try it on last month', why_now: 'The data is fresh.', linked_use_case: 1 }],
  reframes: [
    {
      their_hesitation: 'The client will notice.',
      the_concern: 'Quality',
      reframe: 'You still review every line.',
      first_proof: 'Compare it with last month’s version.',
    },
  ],
  do_this_today: { action: 'Open last month’s report', time_required: '15 minutes', why_this_one: 'Lowest effort.' },
}

const ERROR_BODY = { error: { code: 'component_locked', message: 'The interview is locked.' } }

beforeEach(() => {
  clientMock.GET.mockReset()
  clientMock.POST.mockReset()
})

describe('getInterviewState', () => {
  it('GETs /api/interview/me and resolves the state unchanged', async () => {
    const state: InterviewState = { status: 'complete', conversation_id: CONVERSATION_ID, playbook: PLAYBOOK }
    clientMock.GET.mockResolvedValueOnce({ data: state })

    await expect(getInterviewState()).resolves.toEqual(state)
    expect(clientMock.GET).toHaveBeenCalledTimes(1)
    expect(clientMock.GET.mock.calls[0][0]).toBe('/api/interview/me')
    expect(clientMock.POST).not.toHaveBeenCalled()
  })

  it('throws the server message when there is no data', async () => {
    clientMock.GET.mockResolvedValueOnce({ error: ERROR_BODY })
    await expect(getInterviewState()).rejects.toThrow('The interview is locked.')
  })
})

describe('buildPlaybook', () => {
  it('POSTs /api/interview/playbook and resolves the unwrapped playbook', async () => {
    clientMock.POST.mockResolvedValueOnce({ data: { playbook: PLAYBOOK } })

    await expect(buildPlaybook()).resolves.toEqual(PLAYBOOK)
    expect(clientMock.POST).toHaveBeenCalledTimes(1)
    expect(clientMock.POST.mock.calls[0][0]).toBe('/api/interview/playbook')
    expect(clientMock.GET).not.toHaveBeenCalled()
  })

  it('falls back to its own message for an unshaped error', async () => {
    clientMock.POST.mockResolvedValueOnce({ error: 'boom' })
    await expect(buildPlaybook()).rejects.toThrow('Could not build your playbook.')
  })
})

describe('openInterview', () => {
  it('POSTs /api/interview/opener and resolves { conversation_id, greeting }', async () => {
    const opener = { conversation_id: CONVERSATION_ID, greeting: 'Tell me about a typical week.' }
    clientMock.POST.mockResolvedValueOnce({ data: opener })

    await expect(openInterview()).resolves.toEqual(opener)
    expect(clientMock.POST).toHaveBeenCalledTimes(1)
    expect(clientMock.POST.mock.calls[0][0]).toBe('/api/interview/opener')
    expect(clientMock.GET).not.toHaveBeenCalled()
  })

  it('throws the server message when there is no data', async () => {
    clientMock.POST.mockResolvedValueOnce({ error: ERROR_BODY })
    await expect(openInterview()).rejects.toThrow('The interview is locked.')
  })
})
