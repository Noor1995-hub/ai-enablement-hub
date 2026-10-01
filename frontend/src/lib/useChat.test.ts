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

/** A streaming fetch stub whose body stays open until the test pushes frames or closes it.
 * `honourAbort` mimics real fetch (the body errors with an AbortError when the signal fires);
 * with it off, the body keeps delivering, which proves the hook's own guards. */
function controllableStream({ honourAbort = true } = {}) {
  const encoder = new TextEncoder()
  let bodyController!: ReadableStreamDefaultController<Uint8Array>
  let signal: AbortSignal | undefined
  const fetchMock = vi.fn((_url: string, init: RequestInit) => {
    signal = init.signal ?? undefined
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        bodyController = c
      },
    })
    if (honourAbort) {
      signal?.addEventListener('abort', () => {
        bodyController.error(new DOMException('The operation was aborted.', 'AbortError'))
      })
    }
    return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }))
  })
  return {
    fetchMock,
    signal: () => signal,
    push(event: string, data: unknown) {
      bodyController.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
    },
    close: () => bodyController.close(),
    fail: () => bodyController.error(new TypeError('network error')),
  }
}

/** Let the hook's read loop drain whatever has been pushed. */
async function flush() {
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0))
  })
}

describe('useChat stream cancellation', () => {
  it('streams a normal reply to completion', async () => {
    const stream = controllableStream()
    vi.stubGlobal('fetch', stream.fetchMock)
    const { result } = renderHook(() => useChat('chatbot'))

    let sent!: Promise<void>
    act(() => {
      sent = result.current.send('hi')
    })
    expect(result.current.loading).toBe(true)
    await flush()
    stream.push('token', { text: 'Hel' })
    stream.push('token', { text: 'lo' })
    stream.push('done', { conversation_id: CONVERSATION_ID, truncated: false, usage: null })
    stream.close()
    await act(async () => {
      await sent
    })

    expect(stream.signal()?.aborted).toBe(false)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.messages).toEqual([
      { role: 'user', content: 'hi' },
      { role: 'assistant', content: 'Hello' },
    ])
  })

  it('aborts the fetch on unmount and touches no state afterwards', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    try {
      const stream = controllableStream()
      vi.stubGlobal('fetch', stream.fetchMock)
      const { result, unmount } = renderHook(() => useChat('chatbot'))

      let sent!: Promise<void>
      act(() => {
        sent = result.current.send('hi')
      })
      await flush()
      stream.push('token', { text: 'Par' })
      await flush()
      const before = result.current

      unmount()
      expect(stream.signal()?.aborted).toBe(true)
      await sent // resolves: the AbortError is swallowed, never surfaced

      expect(result.current).toBe(before)
      expect(result.current.error).toBeNull()
      expect(consoleError).not.toHaveBeenCalled()
    } finally {
      consoleError.mockRestore()
    }
  })

  it('startNew mid-stream aborts, clears the messages and resets loading', async () => {
    const stream = controllableStream()
    vi.stubGlobal('fetch', stream.fetchMock)
    const { result } = renderHook(() => useChat('chatbot'))

    let sent!: Promise<void>
    act(() => {
      sent = result.current.send('hi')
    })
    await flush()
    stream.push('token', { text: 'Par' })
    await flush()
    expect(result.current.loading).toBe(true)

    act(() => {
      result.current.startNew()
    })
    await act(async () => {
      await sent
    })

    expect(stream.signal()?.aborted).toBe(true)
    expect(result.current.messages).toEqual([])
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('ignores frames and failures from a body that keeps going after the abort', async () => {
    const stream = controllableStream({ honourAbort: false })
    const next = sseResponse([['done', { conversation_id: CONVERSATION_ID, truncated: false, usage: null }]])
    vi.stubGlobal('fetch', stream.fetchMock)
    const { result } = renderHook(() => useChat('chatbot'))

    let sent!: Promise<void>
    act(() => {
      sent = result.current.send('hi')
    })
    await flush()
    act(() => {
      result.current.startNew()
    })
    // The old body delivers a conversation id and then fails: neither may land.
    stream.push('done', { conversation_id: CONVERSATION_ID, truncated: false, usage: null })
    await flush()
    stream.fail()
    await act(async () => {
      await sent
    })

    expect(result.current.messages).toEqual([])
    expect(result.current.error).toBeNull()
    expect(result.current.loading).toBe(false)

    // The next send starts a fresh conversation, not the aborted stream's.
    stream.fetchMock.mockResolvedValueOnce(next)
    await act(async () => {
      await result.current.send('fresh')
    })
    const body = JSON.parse((stream.fetchMock.mock.calls[1][1] as RequestInit).body as string)
    expect(body.conversation_id).toBeNull()
  })

  it('a superseding send aborts the first stream', async () => {
    const first = controllableStream()
    vi.stubGlobal('fetch', first.fetchMock)
    const { result } = renderHook(() => useChat('chatbot'))

    let firstSent!: Promise<void>
    act(() => {
      firstSent = result.current.send('one')
    })
    await flush()
    const firstSignal = first.signal()

    first.fetchMock.mockResolvedValueOnce(sseResponse([['token', { text: 'Two' }]]))
    await act(async () => {
      await result.current.send('two')
      await firstSent
    })

    expect(firstSignal?.aborted).toBe(true)
    expect(result.current.error).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.messages[result.current.messages.length - 1]).toEqual({ role: 'assistant', content: 'Two' })
  })
})
