// Contract tests for the typed admin hooks: stub `fetch`, drive the real hook, and assert the
// method, path, query and body that reach the wire. These replace the manual "click it on the
// live DB" checks for the rawRequest retirement (review 8.2) — the endpoints write live data,
// so they are never exercised against a real backend.
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import {
  useApplyDefaults,
  useBulkAssignUsers,
  useCalibrationNotes,
  useDashboard,
  useDefaults,
  useFeedback,
  useGenerateLearnCard,
  useGraduateCalibrationNote,
  useImprovementQueue,
  useInterview,
  usePatchFeedback,
  useProposal,
  useProposals,
  useReviewCalibrationNote,
  useReviewProposal,
  useRunImprovement,
  useSendReminder,
  useSetDefaults,
  useSuggestTriage,
} from './api'

// openapi-fetch captures `globalThis.fetch` and `globalThis.Request` when `client` is created, so a
// per-test stubGlobal would be too late. Before api.ts (and so the client) is imported, install a
// fetch that forwards to a swappable handler, and a Request that supplies an origin (Node's Request
// rejects the relative URLs the client builds; browsers resolve them against the page origin).
const net = vi.hoisted(() => {
  const holder = { handler: (async () => new Response(null, { status: 500 })) as (req: Request) => Promise<Response> }
  globalThis.fetch = ((req: Request) => holder.handler(req)) as typeof fetch
  const NativeRequest = globalThis.Request
  globalThis.Request = class extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      super(typeof input === 'string' && input.startsWith('/') ? `http://localhost${input}` : input, init)
    }
  }
  return holder
})

interface Sent {
  method: string
  path: string
  query: Record<string, string>
  body: unknown
}

/** Stubs `fetch`; every request is recorded and answered with `status` + `json`. */
function stubFetch(json: unknown = {}, status = 200) {
  const sent: Sent[] = []
  net.handler = async (input: Request) => {
    const url = new URL(input.url)
    const text = await input.clone().text()
    sent.push({
      method: input.method,
      path: url.pathname,
      query: Object.fromEntries(url.searchParams),
      body: text ? JSON.parse(text) : undefined,
    })
    return status === 204
      ? new Response(null, { status })
      : new Response(JSON.stringify(json), { status, headers: { 'Content-Type': 'application/json' } })
  }
  return sent
}

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('dashboard and reminder (E13)', () => {
  it('GETs the dashboard scoped to a project', async () => {
    const sent = stubFetch({ tiles: 1 })
    const { result } = renderHook(() => useDashboard('p-1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([{ method: 'GET', path: '/api/admin/dashboard', query: { project_id: 'p-1' }, body: undefined }])
  })

  it('omits project_id for the all-projects scope', async () => {
    const sent = stubFetch({})
    const { result } = renderHook(() => useDashboard(null), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent[0].query).toEqual({})
  })

  it('surfaces the server message when the dashboard fails', async () => {
    stubFetch({ error: { code: 'x', message: 'Dashboard exploded' } }, 500)
    const { result } = renderHook(() => useDashboard(null), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toBe('Dashboard exploded')
  })

  it('POSTs a reminder to the user with no body', async () => {
    const sent = stubFetch({ sent: 1 })
    const { result } = renderHook(() => useSendReminder(), { wrapper })
    await result.current.mutateAsync('u-9')
    expect(sent).toEqual([{ method: 'POST', path: '/api/admin/users/u-9/reminder', query: {}, body: undefined }])
  })
})

describe('feedback family (E14)', () => {
  it('GETs the feedback list, mapping track to track_id and page to offset', async () => {
    const sent = stubFetch({ items: [], total: 0 })
    const { result } = renderHook(() => useFeedback({ status: 'new', track: 't-1', project: 'p-1', page: 3, limit: 10 }), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([
      {
        method: 'GET',
        path: '/api/admin/feedback',
        query: { status: 'new', track_id: 't-1', project_id: 'p-1', limit: '10', offset: '20' },
        body: undefined,
      },
    ])
  })

  it('omits unset filters and defaults to the first page of 50', async () => {
    const sent = stubFetch({ items: [], total: 0 })
    const { result } = renderHook(() => useFeedback({ project: null }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent[0].query).toEqual({ limit: '50', offset: '0' })
  })

  it('PATCHes the status of one item and resolves on 204', async () => {
    const sent = stubFetch(undefined, 204)
    const { result } = renderHook(() => usePatchFeedback(), { wrapper })
    await result.current.mutateAsync({ id: 'f-7', status: 'accepted' })
    expect(sent).toEqual([
      { method: 'PATCH', path: '/api/admin/feedback/f-7', query: {}, body: { status: 'accepted' } },
    ])
  })

  it('rejects a failed PATCH with the server message', async () => {
    stubFetch({ error: { code: 'nope', message: 'Cannot update' } }, 403)
    const { result } = renderHook(() => usePatchFeedback(), { wrapper })
    await expect(result.current.mutateAsync({ id: 'f-7', status: 'dismissed' })).rejects.toThrow('Cannot update')
  })

  it('POSTs suggest-triage with the project and limit as query params and no body', async () => {
    const sent = stubFetch({ suggested: 0 })
    const { result } = renderHook(() => useSuggestTriage(), { wrapper })
    await result.current.mutateAsync({ project: 'p-1', limit: 5 })
    expect(sent).toEqual([
      {
        method: 'POST',
        path: '/api/admin/feedback/suggest-triage',
        query: { project_id: 'p-1', limit: '5' },
        body: undefined,
      },
    ])
  })
})

describe('project defaults and bulk assignment (E15)', () => {
  it('GETs the defaults of one project', async () => {
    const sent = stubFetch({ track_ids: ['t-1'] })
    const { result } = renderHook(() => useDefaults('p-1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([{ method: 'GET', path: '/api/admin/projects/p-1/defaults', query: {}, body: undefined }])
    expect(result.current.data).toEqual({ track_ids: ['t-1'] })
  })

  it('PUTs the full track list as the defaults body and resolves on 204', async () => {
    const sent = stubFetch(undefined, 204)
    const { result } = renderHook(() => useSetDefaults(), { wrapper })
    await result.current.mutateAsync({ projectId: 'p-1', trackIds: ['t-1', 't-2'] })
    expect(sent[0]).toEqual({
      method: 'PUT',
      path: '/api/admin/projects/p-1/defaults',
      query: {},
      body: { track_ids: ['t-1', 't-2'] },
    })
  })

  it('POSTs defaults/apply with no body', async () => {
    const sent = stubFetch({ users_updated: 2 })
    const { result } = renderHook(() => useApplyDefaults(), { wrapper })
    await result.current.mutateAsync('p-1')
    expect(sent).toEqual([
      { method: 'POST', path: '/api/admin/projects/p-1/defaults/apply', query: {}, body: undefined },
    ])
  })

  it('POSTs a bulk assignment body unchanged and resolves on 204', async () => {
    const sent = stubFetch(undefined, 204)
    const { result } = renderHook(() => useBulkAssignUsers(), { wrapper })
    const body = { user_ids: ['u-1', 'u-2'], track_ids: ['t-1'], assigned: true }
    await result.current.mutateAsync(body)
    expect(sent).toEqual([{ method: 'POST', path: '/api/admin/assignments/bulk', query: {}, body }])
  })

  it('rejects a failed bulk assignment with the server message', async () => {
    stubFetch({ error: { code: 'bad', message: 'Nothing to assign' } }, 422)
    const { result } = renderHook(() => useBulkAssignUsers(), { wrapper })
    await expect(result.current.mutateAsync({ user_ids: ['u-1'], track_ids: [], assigned: true })).rejects.toThrow(
      'Nothing to assign',
    )
  })
})

describe('content improvement (E16)', () => {
  it('GETs the proposal list with status, limit and offset', async () => {
    const sent = stubFetch({ items: [], total: 0 })
    const { result } = renderHook(() => useProposals({ status: 'pending', page: 2, limit: 5 }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([
      {
        method: 'GET',
        path: '/api/admin/content-improvement',
        query: { status: 'pending', limit: '5', offset: '5' },
        body: undefined,
      },
    ])
  })

  it('GETs one proposal by id', async () => {
    const sent = stubFetch({ id: 'pr-1' })
    const { result } = renderHook(() => useProposal('pr-1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([
      { method: 'GET', path: '/api/admin/content-improvement/pr-1', query: {}, body: undefined },
    ])
  })

  it('GETs the draft queue', async () => {
    const sent = stubFetch({ lessons: [] })
    const { result } = renderHook(() => useImprovementQueue(true), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([
      { method: 'GET', path: '/api/admin/content-improvement/queue', query: {}, body: undefined },
    ])
  })

  it('POSTs the chosen lesson ids to run', async () => {
    const sent = stubFetch({ results: [] })
    const { result } = renderHook(() => useRunImprovement(), { wrapper })
    await result.current.mutateAsync(['l-1', 'l-2'])
    expect(sent).toEqual([
      { method: 'POST', path: '/api/admin/content-improvement/run', query: {}, body: { lesson_ids: ['l-1', 'l-2'] } },
    ])
  })

  it('reviews with the edited blocks when the admin changed the draft', async () => {
    const sent = stubFetch({ status: 'approved' })
    const { result } = renderHook(() => useReviewProposal(), { wrapper })
    const editedBlocks = [{ id: 'b1', type: 'text', text: 'edited' }]
    await result.current.mutateAsync({ proposalId: 'pr-1', decision: 'approve', editedBlocks })
    expect(sent).toEqual([
      {
        method: 'POST',
        path: '/api/admin/content-improvement/pr-1/review',
        query: {},
        body: { decision: 'approve', edited_blocks: editedBlocks },
      },
    ])
  })

  it('sends edited_blocks: null when the draft is accepted as drafted', async () => {
    const sent = stubFetch({ status: 'rejected' })
    const { result } = renderHook(() => useReviewProposal(), { wrapper })
    await result.current.mutateAsync({ proposalId: 'pr-1', decision: 'reject' })
    expect(sent[0].body).toEqual({ decision: 'reject', edited_blocks: null })
  })

  it('POSTs the learn-card critique with no body', async () => {
    const sent = stubFetch({ id: 'lc-1' })
    const { result } = renderHook(() => useGenerateLearnCard(), { wrapper })
    await result.current.mutateAsync('pr-1')
    expect(sent).toEqual([
      { method: 'POST', path: '/api/admin/content-improvement/pr-1/critique', query: {}, body: undefined },
    ])
  })

  it('rejects a failed review with the server message', async () => {
    stubFetch({ error: { code: 'stale', message: 'Lesson changed since the draft' } }, 409)
    const { result } = renderHook(() => useReviewProposal(), { wrapper })
    await expect(result.current.mutateAsync({ proposalId: 'pr-1', decision: 'approve' })).rejects.toThrow(
      'Lesson changed since the draft',
    )
  })
})

describe('calibration notes and interview (E17)', () => {
  it('GETs calibration notes with status, limit and offset', async () => {
    const sent = stubFetch({ items: [], total: 0 })
    const { result } = renderHook(() => useCalibrationNotes({ status: 'suggested', page: 2, limit: 10 }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([
      {
        method: 'GET',
        path: '/api/admin/calibration-notes',
        query: { status: 'suggested', limit: '10', offset: '10' },
        body: undefined,
      },
    ])
  })

  it('POSTs the review decision for one note', async () => {
    const sent = stubFetch({ status: 'approved' })
    const { result } = renderHook(() => useReviewCalibrationNote(), { wrapper })
    await result.current.mutateAsync({ noteId: 'n-1', decision: 'approve' })
    expect(sent).toEqual([
      { method: 'POST', path: '/api/admin/calibration-notes/n-1/review', query: {}, body: { decision: 'approve' } },
    ])
  })

  it('rejects a failed review with the server message', async () => {
    stubFetch({ error: { code: 'gone', message: 'Note not found' } }, 404)
    const { result } = renderHook(() => useReviewCalibrationNote(), { wrapper })
    await expect(result.current.mutateAsync({ noteId: 'n-1', decision: 'reject' })).rejects.toThrow('Note not found')
  })

  it('POSTs the graduate action with no body and returns the response', async () => {
    const sent = stubFetch({ line: 'Write short.' })
    const { result } = renderHook(() => useGraduateCalibrationNote(), { wrapper })
    const out = await result.current.mutateAsync('n-1')
    expect(sent).toEqual([
      { method: 'POST', path: '/api/admin/calibration-notes/n-1/graduate', query: {}, body: undefined },
    ])
    expect(out).toEqual({ line: 'Write short.' })
  })

  it('GETs one user interview by id', async () => {
    const sent = stubFetch({ status: 'complete' })
    const { result } = renderHook(() => useInterview('u-3'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sent).toEqual([{ method: 'GET', path: '/api/admin/interviews/u-3', query: {}, body: undefined }])
  })
})
