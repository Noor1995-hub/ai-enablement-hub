import { useEffect, useState } from 'react'
import { type ChatKind, useChat } from '../lib/useChat'

interface ChatPanelProps {
  kind: ChatKind
}

export default function ChatPanel({ kind }: ChatPanelProps) {
  const { messages, send, loading, error, conversations, loadConversations, loadConversation, startNew } =
    useChat(kind)
  const [input, setInput] = useState('')
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    if (showHistory) void loadConversations()
  }, [showHistory, loadConversations])

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return
    setInput('')
    void send(trimmed)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: 480, fontFamily: 'var(--dlw-font-body)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: 12, borderBottom: '1px solid #E2E2E2' }}>
        <button type="button" onClick={startNew} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
          + New conversation
        </button>
        <button type="button" onClick={() => setShowHistory((v) => !v)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
          History
        </button>
      </div>

      {showHistory && (
        <div style={{ borderBottom: '1px solid #E2E2E2', maxHeight: 160, overflowY: 'auto' }}>
          {conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => {
                void loadConversation(c.id)
                setShowHistory(false)
              }}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: 8, background: 'none', border: 'none', cursor: 'pointer' }}
            >
              {new Date(c.updated_at).toLocaleString()}
            </button>
          ))}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? '#C42828' : '#F2F2F2',
              color: m.role === 'user' ? '#fff' : '#1A1A1A',
              borderRadius: 12,
              padding: '8px 12px',
              maxWidth: '80%',
              whiteSpace: 'pre-wrap',
            }}
          >
            {m.content}
          </div>
        ))}
        {error && <div style={{ color: '#C42828', fontSize: 13 }}>{error}</div>}
      </div>

      <p style={{ fontSize: 11, color: '#8A8A8A', padding: '0 12px', margin: '0 0 8px' }}>
        Conversations are stored and may be reviewed by hub admins to improve the hub.
      </p>

      <form onSubmit={onSubmit} style={{ display: 'flex', gap: 8, padding: 12, borderTop: '1px solid #E2E2E2' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          style={{ flex: 1, padding: '8px 12px', borderRadius: 999, border: '1px solid #E2E2E2' }}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{ borderRadius: 999, padding: '8px 16px', background: '#C42828', color: '#fff', border: 'none', cursor: 'pointer' }}
        >
          {loading ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
