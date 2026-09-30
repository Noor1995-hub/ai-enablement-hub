import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { client, errorMessage } from '../api/client'

// Admin lesson management. Reorder is ONE batch call
// (PUT /api/admin/modules/{id}/lessons/order) replacing the old N parallel
// sort_order updates (fixes B5); create/delete go through /api/admin/lessons.

interface PanelLesson {
  id: string
  title: string
  sort_order: number
}

interface ModulePanelProps {
  moduleId: string
  moduleName: string
  onClose: () => void
  onDeleted: () => void
}

export default function ModulePanel({ moduleId, moduleName, onClose, onDeleted }: ModulePanelProps) {
  const [lessons, setLessons]           = useState<PanelLesson[]>([])
  const [loading, setLoading]           = useState(true)
  const [addingLesson, setAddingLesson] = useState(false)
  const [newTitle, setNewTitle]         = useState('')
  const [addError, setAddError]         = useState<string | null>(null)
  const [deletingModule, setDeletingModule]   = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  // Which lesson row is armed for deletion (in-app two-step, mirroring the
  // module danger zone below). Never window.confirm: this panel renders on the
  // learner-facing /learning route, where the admin kit's CSS isn't loaded.
  const [confirmingLessonId, setConfirmingLessonId] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!moduleId) return
    let cancelled = false
    setLoading(true)
    client.GET('/api/modules/{module_id}/lessons', { params: { path: { module_id: moduleId } } })
      .then(({ data }) => {
        if (cancelled) return
        setLessons(data?.lessons ?? [])
        setLoading(false)
      })
      .catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [moduleId])

  async function handleAddLesson() {
    if (!newTitle.trim()) return
    setAddError(null)
    const { data, error } = await client.POST('/api/admin/lessons', {
      body: { module_id: moduleId, title: newTitle.trim() },
    })
    if (!data) {
      setAddError(errorMessage(error, 'Failed to add lesson.'))
      return
    }
    setLessons(ls => [...ls, data])
    setNewTitle('')
    setAddingLesson(false)
    navigate(`/learning/lesson/${data.id}?edit=true`)
  }

  async function handleDelete(lessonId: string) {
    const { error } = await client.DELETE('/api/admin/lessons/{lesson_id}', {
      params: { path: { lesson_id: lessonId } },
    })
    setConfirmingLessonId(null)
    if (error) { setAddError(errorMessage(error, 'Failed to delete lesson.')); return }
    setLessons(ls => ls.filter(l => l.id !== lessonId))
  }

  async function handleDeleteModule() {
    setDeletingModule(true)
    setAddError(null)
    const { error } = await client.DELETE('/api/admin/modules/{module_id}', {
      params: { path: { module_id: moduleId } },
    })
    if (error) {
      setDeletingModule(false)
      setConfirmingDelete(false)
      setAddError(errorMessage(error, 'Failed to delete module.'))
      return
    }
    onDeleted()
  }

  async function moveLesson(lessonId: string, dir: -1 | 1) {
    const i = lessons.findIndex(l => l.id === lessonId)
    if (dir === -1 && i === 0) return
    if (dir === 1 && i === lessons.length - 1) return

    const next = [...lessons]
    ;[next[i], next[i + dir]] = [next[i + dir], next[i]]

    const { error } = await client.PUT('/api/admin/modules/{module_id}/lessons/order', {
      params: { path: { module_id: moduleId } },
      body: { lesson_ids: next.map(l => l.id) },
    })
    if (error) { setAddError(errorMessage(error, 'Failed to reorder lessons.')); return }
    setLessons(next.map((l, idx) => ({ ...l, sort_order: idx })))
  }

  const labelStyle: React.CSSProperties = {
    fontFamily: 'var(--dlw-font-ui)',
    fontWeight: 600,
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: '#8A8A8A',
  }

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: 420,
      background: '#fff', borderLeft: '1px solid #E2E2E2',
      boxShadow: '-8px 0 32px -8px rgba(16,24,32,.12)',
      display: 'flex', flexDirection: 'column',
      zIndex: 100,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '18px 20px', borderBottom: '1px solid #E2E2E2', flexShrink: 0,
      }}>
        <div>
          <p style={{ ...labelStyle, margin: '0 0 2px' }}>Module</p>
          <h2 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 17, color: '#101820', margin: 0 }}>
            {moduleName}
          </h2>
        </div>
        <button onClick={onClose} style={{
          width: 32, height: 32, borderRadius: '50%', border: '1px solid #E2E2E2',
          background: '#fff', color: '#8A8A8A', fontSize: 18, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1,
        }}>×</button>
      </div>

      {/* Lessons list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
        <p style={{ ...labelStyle, marginBottom: 12 }}>Lessons</p>
        {addError && (
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 13, color: '#C42828', background: '#FEF2F2', padding: '8px 12px', borderRadius: 6, marginBottom: 12 }}>
            {addError}
          </p>
        )}

        {loading ? (
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#8A8A8A' }}>Loading…</p>
        ) : lessons.length === 0 ? (
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A', fontStyle: 'italic' }}>
            No lessons yet. Add one below.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {lessons.map((lesson, i) => (
              <div key={lesson.id} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 14px', border: '1px solid #E2E2E2', borderRadius: 8,
                background: '#FAFAFA',
              }}>
                {/* Reorder */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <button type="button" onClick={() => moveLesson(lesson.id, -1)} disabled={i === 0}
                    style={{ padding: '1px 6px', border: '1px solid #E2E2E2', borderRadius: 3, background: '#fff', color: i === 0 ? '#D0D0D0' : '#3C3C3C', fontSize: 11, cursor: i === 0 ? 'default' : 'pointer', lineHeight: 1.4 }}>↑</button>
                  <button type="button" onClick={() => moveLesson(lesson.id, 1)} disabled={i === lessons.length - 1}
                    style={{ padding: '1px 6px', border: '1px solid #E2E2E2', borderRadius: 3, background: '#fff', color: i === lessons.length - 1 ? '#D0D0D0' : '#3C3C3C', fontSize: 11, cursor: i === lessons.length - 1 ? 'default' : 'pointer', lineHeight: 1.4 }}>↓</button>
                </div>

                {/* Title */}
                <span style={{ flex: 1, fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: '#101820', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {lesson.title}
                </span>

                {/* Actions */}
                <button type="button" onClick={() => navigate(`/learning/lesson/${lesson.id}?edit=true`)}
                  style={{ padding: '4px 12px', borderRadius: 6, border: '1.5px solid #3BC9BC', background: 'none', color: '#1D7A52', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  Edit
                </button>
                {confirmingLessonId === lesson.id ? (
                  <>
                    <button type="button" onClick={() => handleDelete(lesson.id)}
                      style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #FCA5A5', background: '#FEF2F2', color: '#C42828', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                      Delete
                    </button>
                    <button type="button" onClick={() => setConfirmingLessonId(null)}
                      style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #E2E2E2', background: '#fff', color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)', fontSize: 12, cursor: 'pointer' }}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <button type="button" onClick={() => setConfirmingLessonId(lesson.id)} title="Delete lesson"
                    style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #FCA5A5', background: '#FEF2F2', color: '#C42828', fontSize: 13, cursor: 'pointer' }}>
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Add lesson */}
        <div style={{ marginTop: 16 }}>
          {addingLesson ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                autoFocus
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleAddLesson(); if (e.key === 'Escape') { setAddingLesson(false); setNewTitle('') } }}
                placeholder="Lesson title…"
                style={{
                  flex: 1, padding: '8px 12px', border: '1.5px solid #3BC9BC', borderRadius: 8,
                  fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#101820', outline: 'none',
                }}
              />
              <button onClick={handleAddLesson} style={{
                padding: '8px 14px', borderRadius: 8, background: '#3BC9BC', border: 'none',
                color: '#fff', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, cursor: 'pointer',
              }}>Add</button>
              <button onClick={() => { setAddingLesson(false); setNewTitle(''); setAddError(null) }} style={{
                padding: '8px 10px', borderRadius: 8, border: '1px solid #E2E2E2',
                background: '#fff', color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)', fontSize: 13, cursor: 'pointer',
              }}>Cancel</button>
            </div>
          ) : (
            <button onClick={() => setAddingLesson(true)} style={{
              width: '100%', padding: '10px 0',
              border: '1.5px dashed #E2E2E2', borderRadius: 8,
              background: 'none', color: '#8A8A8A',
              fontFamily: 'var(--dlw-font-body)', fontSize: 14, cursor: 'pointer',
            }}>
              + Add lesson
            </button>
          )}
        </div>
      </div>

      {/* Danger zone */}
      <div style={{ padding: '14px 20px', borderTop: '1px solid #E2E2E2', flexShrink: 0 }}>
        {confirmingDelete ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 13, color: '#3C3C3C', margin: 0 }}>
              Delete "{moduleName}"{lessons.length > 0 && ` and its ${lessons.length} lesson${lessons.length === 1 ? '' : 's'}`}?
              This cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={() => setConfirmingDelete(false)} disabled={deletingModule} style={{
                flex: 1, padding: '9px 0', borderRadius: 8, border: '1px solid #E2E2E2',
                background: '#fff', color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
                cursor: deletingModule ? 'default' : 'pointer',
              }}>
                Cancel
              </button>
              <button type="button" onClick={handleDeleteModule} disabled={deletingModule} style={{
                flex: 1, padding: '9px 0', borderRadius: 8, border: '1px solid #FCA5A5',
                background: '#FEF2F2', color: '#C42828', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
                cursor: deletingModule ? 'default' : 'pointer', opacity: deletingModule ? 0.6 : 1,
              }}>
                {deletingModule ? 'Deleting…' : 'Yes, delete'}
              </button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setConfirmingDelete(true)} style={{
            width: '100%', padding: '10px 0', borderRadius: 8,
            border: '1px solid #FCA5A5', background: '#FEF2F2', color: '#C42828',
            fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, cursor: 'pointer',
          }}>
            Delete module
          </button>
        )}
      </div>
    </div>
  )
}
