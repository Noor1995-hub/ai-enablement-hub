// React hook for the chat SSE endpoints (design-frontend.md's AI Chat Foundation plan, Task 15).
//
// Streaming uses a raw `fetch` + manual SSE line parser, NOT native EventSource: EventSource can
// only issue GET requests, and POST /api/chat/{kind} carries a JSON body (the message content +
// optional conversation_id). History loading (conversation list/detail) goes through the typed
// `openapi-fetch` client instead, since those are plain JSON GET endpoints.
import { useCallback, useState } from 'react'
import { client, refreshAccessToken } from '../api/client'
import { getAccessToken } from '../api/tokens'

export type ChatKind = 'chatbot' | 'assessment' | 'lesson' | 'interview'

export interface ChatUiMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ConversationSummary {
  id: string
  kind: string
  context_ref: string | null
  created_at: string
  updated_at: string
}

/** Bearer-auth fetch with the same 401→refresh→retry-once behaviour as the
 * openapi-fetch client's auth middleware (api/client.ts), reimplemented on raw
 * `fetch` because streaming responses can't go through openapi-fetch. */
async function fetchWithAuth(input: string, init: RequestInit): Promise<Response> {
  const access = getAccessToken()
  const headers = new Headers(init.headers)
  if (access) headers.set('Authorization', `Bearer ${access}`)
  let response = await fetch(input, { ...init, headers })
  if (response.status === 401) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      headers.set('Authorization', `Bearer ${refreshed}`)
      response = await fetch(input, { ...init, headers })
    }
  }
  return response
}

function parseSseLine(
  line: string,
  currentEvent: string,
): { event: string; data: unknown } | null {
  if (line.startsWith('event:')) return null
  if (line.startsWith('data:')) {
    return { event: currentEvent, data: JSON.parse(line.slice('data:'.length).trim()) }
  }
  return null
}

/** Drops a trailing empty assistant placeholder bubble, if present. Used to clean up the
 * optimistic placeholder that `send` appends before the request resolves, when the request
 * fails before any tokens arrive. Leaves other message arrays untouched. */
function dropTrailingEmptyAssistant(prev: ChatUiMessage[]): ChatUiMessage[] {
  if (prev.length === 0) return prev
  const last = prev[prev.length - 1]
  return last.role === 'assistant' && last.content === '' ? prev.slice(0, -1) : prev
}

export function useChat(kind: ChatKind) {
  const [messages, setMessages] = useState<ChatUiMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])

  const send = useCallback(
    async (content: string) => {
      setLoading(true)
      setError(null)
      setMessages((prev) => [...prev, { role: 'user', content }])
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

      try {
        const response = await fetchWithAuth(`/api/chat/${kind}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, conversation_id: conversationId }),
        })
        if (!response.ok || !response.body) {
          setError(`Chat request failed (${response.status})`)
          setMessages(dropTrailingEmptyAssistant)
          setLoading(false)
          return
        }
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let currentEvent = 'message'
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''
          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEvent = line.slice('event:'.length).trim()
              continue
            }
            const parsed = parseSseLine(line, currentEvent)
            if (!parsed) continue
            if (parsed.event === 'token') {
              const { text } = parsed.data as { text: string }
              setMessages((prev) => {
                // Defensive: if `startNew()` or `loadConversation()` reset/replaced `messages`
                // while this stream was in flight, the assistant placeholder this stream is
                // meant to update may no longer be the last message (or may not exist at all).
                // Drop the stray token rather than indexing into an empty/unrelated array.
                if (prev.length === 0) return prev
                const last = prev[prev.length - 1]
                if (last.role !== 'assistant') return prev
                const next = [...prev]
                next[next.length - 1] = { role: 'assistant', content: last.content + text }
                return next
              })
            } else if (parsed.event === 'done') {
              const { conversation_id } = parsed.data as { conversation_id: string }
              setConversationId(conversation_id)
            } else if (parsed.event === 'error') {
              const { message } = parsed.data as { message: string }
              setError(message)
            }
          }
        }
      } catch {
        setError('Connection lost while streaming the reply.')
        setMessages(dropTrailingEmptyAssistant)
      } finally {
        setLoading(false)
      }
    },
    [kind, conversationId],
  )

  const loadConversations = useCallback(async () => {
    const { data } = await client.GET('/api/chat/conversations', { params: { query: { kind } } })
    if (data) setConversations(data.conversations)
  }, [kind])

  const loadConversation = useCallback(async (id: string) => {
    const { data } = await client.GET('/api/chat/conversations/{conversation_id}', {
      params: { path: { conversation_id: id } },
    })
    if (data) {
      setConversationId(id)
      setMessages(data.messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })))
    }
  }, [])

  const startNew = useCallback(() => {
    setConversationId(null)
    setMessages([])
    setError(null)
  }, [])

  return { messages, send, loading, error, conversations, loadConversations, loadConversation, startNew }
}
