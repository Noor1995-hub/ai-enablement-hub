// frontend/src/components/LessonFeedback.tsx
import { useEffect, useRef, useState } from 'react'
import { client } from '../api/client'

type Status = 'idle' | 'sending' | 'sent' | 'error'

const RED = '#C42828'

export default function LessonFeedback({
  lessonId,
  lessonTitle,
}: {
  lessonId: string
  lessonTitle: string
}) {
  const [open, setOpen]       = useState(false)
  const [message, setMessage] = useState('')
  const [status, setStatus]   = useState<Status>('idle')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const sendGenRef = useRef(0)

  function close() {
    sendGenRef.current += 1
    setOpen(false)
    setMessage('')
    setStatus('idle')
  }

  // Focus the textarea on open; Escape closes the popup.
  useEffect(() => {
    if (!open) return
    textareaRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  async function send() {
    const trimmed = message.trim()
    if (!trimmed || status === 'sending') return
    const gen = sendGenRef.current
    setStatus('sending')
    const { error } = await client.POST('/api/feedback', {
      body: { lesson_id: lessonId, message: trimmed },
    })
    if (sendGenRef.current !== gen) return
    setStatus(error ? 'error' : 'sent')
  }

  const canSend = message.trim().length > 0 && status !== 'sending'

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="lesson-cta"
        aria-label="Share feedback"
        style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 50,
          padding: '11px 22px', borderRadius: 999, border: 'none',
          background: RED, color: '#fff',
          fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
          cursor: 'pointer', boxShadow: 'var(--dlw-shadow-lg)',
          transition: 'background 180ms',
        }}
      >
        Feedback
      </button>

      {open && (
        <div
          onClick={close}
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            background: 'rgba(16,24,32,.45)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 20,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Share feedback"
            style={{
              width: '100%', maxWidth: 440, background: '#fff',
              borderRadius: 'var(--dlw-radius-xl)', boxShadow: 'var(--dlw-shadow-lg)',
              padding: 24, fontFamily: 'var(--dlw-font-body)',
            }}
          >
            {status === 'sent' ? (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <p style={{ margin: '0 0 18px', fontSize: 15, fontWeight: 600, color: '#101820' }}>
                  Thanks, your feedback has been sent!
                </p>
                <button
                  type="button"
                  onClick={close}
                  style={{
                    padding: '10px 22px', borderRadius: 8, border: 'none',
                    background: RED, color: '#fff', fontFamily: 'var(--dlw-font-body)',
                    fontWeight: 700, fontSize: 14, cursor: 'pointer',
                  }}
                >
                  Close
                </button>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 4 }}>
                  <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: RED }}>
                    Share feedback
                  </h2>
                  <button
                    type="button"
                    onClick={close}
                    aria-label="Close"
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      fontSize: 22, lineHeight: 1, color: '#8A8A8A', padding: 0,
                    }}
                  >
                    ×
                  </button>
                </div>
                <p style={{ margin: '0 0 14px', fontSize: 13, color: '#8A8A8A' }}>
                  {lessonTitle}
                </p>
                <textarea
                  ref={textareaRef}
                  value={message}
                  onChange={e => {
                    setMessage(e.target.value)
                    if (status === 'error') setStatus('idle')
                  }}
                  placeholder="What's on your mind?"
                  rows={5}
                  style={{
                    width: '100%', boxSizing: 'border-box', resize: 'vertical',
                    padding: '12px 14px', borderRadius: 10,
                    border: `1.5px solid ${RED}`, outline: 'none',
                    fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#3C3C3C',
                    marginBottom: 14,
                  }}
                />
                {status === 'error' && (
                  <p style={{ margin: '0 0 12px', fontSize: 13, color: RED }}>
                    Couldn't send feedback. Please try again.
                  </p>
                )}
                <button
                  type="button"
                  onClick={send}
                  disabled={!canSend}
                  style={{
                    width: '100%', padding: '12px', borderRadius: 8, border: 'none',
                    background: canSend ? RED : '#E2E2E2',
                    color: canSend ? '#fff' : '#8A8A8A',
                    fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
                    cursor: canSend ? 'pointer' : 'default',
                  }}
                >
                  {status === 'sending' ? 'Sending…' : 'Send feedback'}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
