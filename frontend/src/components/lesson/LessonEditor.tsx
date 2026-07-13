import { useState, useEffect, useRef, type ComponentType } from 'react'
import { client, errorMessage } from '../../api/client'
import { BLOCK_TYPES, BLOCK_LABELS, BLOCK_FACTORIES } from '../../lib/contentBlocks'
import type { ContentBlock } from '../../types/contentBlocks'
import HeadingEditor   from './editors/HeadingEditor'
import ParagraphEditor from './editors/ParagraphEditor'
import CalloutEditor   from './editors/CalloutEditor'
import CardGroupEditor from './editors/CardGroupEditor'
import QuizEditor      from './editors/QuizEditor'
import QuestionEditor  from './editors/QuestionEditor'
import SpacerEditor    from './editors/SpacerEditor'
import InteractiveEditor from './editors/InteractiveEditor'
import TryItYourselfEditor from './editors/TryItYourselfEditor'
import ImageEditor      from './editors/ImageEditor'
import VideoEditor      from './editors/VideoEditor'

// Exhaustively keyed on the discriminated union, mirroring LessonView's
// RENDERERS map: an 8th block type breaks this at compile time.
const EDITORS: {
  [K in ContentBlock['type']]: ComponentType<{
    block: Extract<ContentBlock, { type: K }>
    onChange: (b: Extract<ContentBlock, { type: K }>) => void
  }>
} = {
  [BLOCK_TYPES.HEADING]:    HeadingEditor,
  [BLOCK_TYPES.PARAGRAPH]:  ParagraphEditor,
  [BLOCK_TYPES.CALLOUT]:    CalloutEditor,
  [BLOCK_TYPES.CARD_GROUP]: CardGroupEditor,
  [BLOCK_TYPES.QUIZ]:       QuizEditor,
  [BLOCK_TYPES.QUESTION]:   QuestionEditor,
  [BLOCK_TYPES.WHITESPACE]: SpacerEditor,
  [BLOCK_TYPES.INTERACTIVE]: InteractiveEditor,
  [BLOCK_TYPES.TRY_IT_YOURSELF]: TryItYourselfEditor,
  [BLOCK_TYPES.IMAGE]:      ImageEditor,
  [BLOCK_TYPES.VIDEO]:      VideoEditor,
}

const TYPE_ORDER: ContentBlock['type'][] = [
  BLOCK_TYPES.HEADING,
  BLOCK_TYPES.PARAGRAPH,
  BLOCK_TYPES.CALLOUT,
  BLOCK_TYPES.CARD_GROUP,
  BLOCK_TYPES.QUIZ,
  BLOCK_TYPES.QUESTION,
  BLOCK_TYPES.WHITESPACE,
  BLOCK_TYPES.INTERACTIVE,
  BLOCK_TYPES.TRY_IT_YOURSELF,
  BLOCK_TYPES.IMAGE,
  BLOCK_TYPES.VIDEO,
]

export interface EditedLesson {
  title: string
  content_blocks: ContentBlock[]
}

interface LessonEditorProps {
  lesson: { id: string; title: string; content_blocks: ContentBlock[] }
  onSave?: (updated: EditedLesson) => void
  onLiveChange?: (updated: EditedLesson) => void
}

export default function LessonEditor({ lesson, onSave, onLiveChange }: LessonEditorProps) {
  const [title, setTitle]     = useState(lesson.title ?? '')
  const [blocks, setBlocks]   = useState<ContentBlock[]>(lesson.content_blocks ?? [])
  const [dirty, setDirty]     = useState(false)
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [addOpen, setAddOpen] = useState(false)
  const mounted = useRef(false)

  useEffect(() => {
    if (!mounted.current) { mounted.current = true; return }
    onLiveChange?.({ title, content_blocks: blocks })
  }, [blocks, title, onLiveChange])

  function updateBlock(id: string, updated: ContentBlock) {
    setBlocks(bs => bs.map(b => b.id === id ? updated : b))
    setDirty(true)
  }

  function deleteBlock(id: string) {
    setBlocks(bs => bs.filter(b => b.id !== id))
    setDirty(true)
  }

  function moveBlock(id: string, dir: -1 | 1) {
    setBlocks(bs => {
      const i = bs.findIndex(b => b.id === id)
      if (i < 0) return bs
      if (dir === -1 && i === 0) return bs
      if (dir === 1 && i === bs.length - 1) return bs
      const next = [...bs]
      ;[next[i], next[i + dir]] = [next[i + dir], next[i]]
      return next
    })
    setDirty(true)
  }

  function addBlock(type: ContentBlock['type']) {
    setBlocks(bs => [...bs, BLOCK_FACTORIES[type]()])
    setDirty(true)
    setAddOpen(false)
  }

  async function save() {
    setSaving(true)
    setError(null)
    const { data, error: err } = await client.PATCH('/api/admin/lessons/{lesson_id}', {
      params: { path: { lesson_id: lesson.id } },
      body: { title, content_blocks: blocks },
    })

    setSaving(false)
    if (err || !data) {
      setError(errorMessage(err, 'Failed to save.'))
    } else {
      setDirty(false)
      // Hand up the backend's stamped content_blocks (the write strips
      // ephemeral SAS urls; the response re-stamps them) so the just-saved
      // preview shows working media instead of placeholders.
      onSave?.({ title: data.title, content_blocks: data.content_blocks as ContentBlock[] })
    }
  }

  const headerStyle: React.CSSProperties = {
    fontFamily: 'var(--dlw-font-ui)',
    fontWeight: 600,
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: '#8A8A8A',
    marginBottom: 6,
    display: 'block',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 20px', borderBottom: '1px solid #E2E2E2', flexShrink: 0,
        background: '#fff',
      }}>
        <span style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: dirty ? '#B45309' : '#8A8A8A' }}>
          {dirty ? 'Unsaved changes' : 'Saved'}
        </span>
        <button
          onClick={save}
          disabled={!dirty || saving}
          style={{
            padding: '7px 20px', borderRadius: 999,
            background: dirty ? '#3BC9BC' : '#E2E2E2',
            border: 'none', color: dirty ? '#fff' : '#8A8A8A',
            fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14,
            cursor: dirty ? 'pointer' : 'default',
          }}
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>

      {error && (
        <div style={{ padding: '10px 20px', background: '#FEF2F2', color: '#C42828', fontFamily: 'var(--dlw-font-body)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>

        {/* Lesson title */}
        <div style={{ marginBottom: 24 }}>
          <label style={headerStyle}>Lesson title</label>
          <input
            value={title}
            onChange={e => { setTitle(e.target.value); setDirty(true) }}
            style={{
              width: '100%', padding: '9px 12px',
              border: '1px solid #E2E2E2', borderRadius: 8,
              fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 16,
              color: '#101820', outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Blocks */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {blocks.map((block, i) => {
            // TS can't correlate block.type with block across the map lookup;
            // the mapped type above guarantees the pairing, so one widening cast
            // (same pattern as LessonView's RENDERERS).
            const Editor = EDITORS[block.type] as ComponentType<{ block: ContentBlock; onChange: (b: ContentBlock) => void }>
            if (!Editor) return null // content_blocks is JSONB — tolerate unknown types
            return (
              <div key={block.id} style={{
                border: '1px solid #E2E2E2', borderRadius: 10,
                background: '#FAFAFA', overflow: 'hidden',
              }}>
                {/* Block header */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 14px', borderBottom: '1px solid #E2E2E2', background: '#fff',
                }}>
                  <span style={{
                    fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 11,
                    textTransform: 'uppercase', letterSpacing: '0.08em', color: '#3BC9BC',
                  }}>
                    {BLOCK_LABELS[block.type]}
                  </span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button type="button" onClick={() => moveBlock(block.id, -1)} disabled={i === 0}
                      style={{ padding: '2px 8px', borderRadius: 4, border: '1px solid #E2E2E2', background: '#fff', color: i === 0 ? '#D0D0D0' : '#3C3C3C', fontSize: 13, cursor: i === 0 ? 'default' : 'pointer' }}>↑</button>
                    <button type="button" onClick={() => moveBlock(block.id, 1)} disabled={i === blocks.length - 1}
                      style={{ padding: '2px 8px', borderRadius: 4, border: '1px solid #E2E2E2', background: '#fff', color: i === blocks.length - 1 ? '#D0D0D0' : '#3C3C3C', fontSize: 13, cursor: i === blocks.length - 1 ? 'default' : 'pointer' }}>↓</button>
                    <button type="button" onClick={() => deleteBlock(block.id)}
                      style={{ padding: '2px 8px', borderRadius: 4, border: '1px solid #FCA5A5', background: '#FEF2F2', color: '#C42828', fontSize: 13, cursor: 'pointer' }}>×</button>
                  </div>
                </div>

                {/* Editor */}
                <div style={{ padding: '14px 16px' }}>
                  <Editor block={block} onChange={updated => updateBlock(block.id, updated)} />
                </div>
              </div>
            )
          })}
        </div>

        {/* Add block */}
        <div style={{ marginTop: 16 }}>
          {addOpen ? (
            <div style={{
              border: '1px solid #E2E2E2', borderRadius: 10,
              overflow: 'hidden', background: '#fff',
            }}>
              {TYPE_ORDER.map((type, i) => (
                <button key={type} type="button" onClick={() => addBlock(type)} style={{
                  display: 'block', width: '100%', textAlign: 'left',
                  padding: '11px 16px', background: 'none', border: 'none',
                  borderBottom: i < TYPE_ORDER.length - 1 ? '1px solid #F0EFED' : 'none',
                  fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14,
                  color: '#3C3C3C', cursor: 'pointer',
                }}>
                  {BLOCK_LABELS[type]}
                </button>
              ))}
              <button type="button" onClick={() => setAddOpen(false)} style={{
                display: 'block', width: '100%', textAlign: 'center',
                padding: '9px 16px', background: '#FAFAFA', border: 'none',
                borderTop: '1px solid #F0EFED',
                fontFamily: 'var(--dlw-font-body)', fontSize: 13, color: '#8A8A8A', cursor: 'pointer',
              }}>
                Cancel
              </button>
            </div>
          ) : (
            <button type="button" onClick={() => setAddOpen(true)} style={{
              width: '100%', padding: '10px 0',
              border: '1.5px dashed #E2E2E2', borderRadius: 8,
              background: 'none', color: '#8A8A8A',
              fontFamily: 'var(--dlw-font-body)', fontSize: 14, cursor: 'pointer',
            }}>
              + Add block
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
