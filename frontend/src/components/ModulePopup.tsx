import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { client } from '../api/client'

const POPUP_WIDTH  = 280
const POPUP_HEIGHT = 164 // approximate, for clamping

interface ModulePopupProps {
  moduleId: string
  title: string
  total: number
  completed: number
  locked?: boolean
  anchorRect: DOMRect
  onClose: () => void
}

export default function ModulePopup({ moduleId, title, total, completed, locked = false, anchorRect, onClose }: ModulePopupProps) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  // Position to the right of the anchor node, clamped to viewport
  const top  = Math.min(
    Math.max(8, anchorRect.top + anchorRect.height / 2 - POPUP_HEIGHT / 2),
    window.innerHeight - POPUP_HEIGHT - 8
  )
  const left = anchorRect.right + 16 + POPUP_WIDTH > window.innerWidth
    ? anchorRect.left - POPUP_WIDTH - 16
    : anchorRect.right + 16

  async function handleStart() {
    setLoading(true)

    // One call replaces the old lessons + lesson_progress pair: next_lesson_id
    // is the first uncompleted ASSIGNED lesson (server-computed), the first
    // assigned lesson the fallback when everything is already done.
    const { data } = await client.GET('/api/modules/{module_id}/lessons', {
      params: { path: { module_id: moduleId } },
    })
    if (!data) { setLoading(false); return }
    const assignedLessons = data.lessons.filter(l => l.assigned)
    if (assignedLessons.length === 0) { setLoading(false); return }

    navigate(`/learning/lesson/${data.next_lesson_id ?? assignedLessons[0].id}`)
    setLoading(false)
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.92 }}
      transition={{ duration: 0.15 }}
      style={{
        position: 'fixed',
        top,
        left,
        width: POPUP_WIDTH,
        background: '#fff',
        borderRadius: 16,
        boxShadow: '0 8px 40px rgba(0,0,0,0.18)',
        padding: '20px 20px 20px 20px',
        zIndex: 200,
        fontFamily: 'var(--dlw-font-body)',
      }}
    >
      {/* Close */}
      <button
        onClick={onClose}
        style={{
          position: 'absolute', top: 14, right: 14,
          background: 'none', border: 'none', cursor: 'pointer',
          fontSize: 16, color: '#8A8A8A', lineHeight: 1, padding: 4,
        }}
      >
        ×
      </button>

      {/* Module title */}
      <p style={{ margin: '0 0 6px', fontWeight: 700, fontSize: 16, color: '#101820', paddingRight: 20 }}>
        {title}
      </p>

      {/* Progress */}
      <p style={{ margin: '0 0 18px', fontSize: 13, fontWeight: 300, color: '#8A8A8A' }}>
        {locked ? 'Complete the required modules first to unlock this one.' : `${completed} of ${total} lesson${total !== 1 ? 's' : ''} completed`}
      </p>

      {/* Start button */}
      <button
        onClick={handleStart}
        disabled={loading || total === 0 || locked}
        style={{
          display: 'block', width: '100%',
          padding: '11px 0', borderRadius: 8,
          background: (total === 0 || locked) ? '#E2E2E2' : '#C42828',
          border: 'none',
          color: (total === 0 || locked) ? '#8A8A8A' : '#fff',
          fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 14,
          cursor: (total === 0 || locked) ? 'default' : 'pointer',
        }}
      >
        {locked ? 'Locked' : loading ? 'Loading…' : completed > 0 ? 'Continue module →' : 'Start module →'}
      </button>
    </motion.div>
  )
}
