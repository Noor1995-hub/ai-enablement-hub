import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useChat } from './useChat'

const CONVERSATION_ID = '6f1c2d3e-4a5b-4c6d-8e7f-001122334455'
const BUSY = 'The assistant is busy right now - please try again in a moment.'

/** A 200 text/event-stream response carrying the given frames, shaped like the backend's. */
function sseResponse(frames: Array<[string, unknown]>): Response {
  const body = frames.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join('')
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useChat error frame', () => {
  it('drops the empty bubble and adopts the conversation id when the reply fails before any token', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(sseResponse([['error', { message: BUSY, conversation_id: CONVERSATION_ID }]]))
      .mockResolvedValueOnce(sseResponse([['done', { conversation_id: CONVERSATION_ID, truncated: false, usage: null }]]))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat('chatbot'))

    await act(async () => {
      await result.current.send('hi')
    })

    expect(result.current.error).toBe(BUSY)
    expect(result.current.messages).toEqual([{ role: 'user', content: 'hi' }])

    // The retry continues the same conversation instead of orphaning the first turn.
    await act(async () => {
      await result.current.send('hi again')
    })
    const retryBody = JSON.parse((fetchMock.mock.calls[1][1] as RequestInit).body as string)
    expect(retryBody.conversation_id).toBe(CONVERSATION_ID)
  })

  it('keeps the partial reply when the provider fails mid-stream', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(
        sseResponse([
          ['token', { text: 'Par' }],
          ['error', { message: BUSY, conversation_id: CONVERSATION_ID }],
        ]),
      ),
    )
    const { result } = renderHook(() => useChat('chatbot'))

    await act(async () => {
      await result.current.send('hi')
    })

    expect(result.current.error).toBe(BUSY)
    expect(result.current.messages).toEqual([
      { role: 'user', content: 'hi' },
      { role: 'assistant', content: 'Par' },
    ])
  })
})
