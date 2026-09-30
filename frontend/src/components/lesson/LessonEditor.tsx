import { useState, useEffect, useRef, Fragment, type ComponentType } from 'react'
import { client, errorMessage } from '../../api/client'
import { BLOCK_TYPES, BLOCK_LABELS, BLOCK_FACTORIES } from '../../lib/contentBlocks'
import { useUnsavedGuard } from '../../lib/useUnsavedGuard'
import type { ContentBlock } from '../../types/contentBlocks'
import HeadingEditor   from './editors/HeadingEditor'
import ParagraphEditor from './editors/ParagraphEditor'
import CalloutEditor   from './editors/CalloutEditor'
import KickerEditor    from './editors/KickerEditor'
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
  [BLOCK_TYPES.KICKER]:     KickerEditor,
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
  BLOCK_TYPES.KICKER,
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

// Media cannot be ADDED from an embedded instance. The content-review pane's
// accept path runs `check_media_immutable`, which refuses any media locator
// that is not already in the lesson — so adding an Image/Video block there
// uploads a real blob and then makes Accept fail every time. Offering the
// action at all is the defect; the backend rule is deliberate (the review pane
// revises wording and structure, media is managed in the lesson editor).
// This only removes the ADD affordance: existing media blocks in a draft stay
// fully visible, editable and deletable, since copying one through unchanged
// or dropping it are both allowed by that same check.
const EMBEDDED_TYPE_ORDER: ContentBlock['type'][] = TYPE_ORDER.filter(
  type => type !== BLOCK_TYPES.IMAGE && type !== BLOCK_TYPES.VIDEO,
)

// Compact block-type chooser. Renders in-place wherever a block can be
// inserted (the between-block plus buttons, and the bottom "+ Add block").
// A tight two-column grid keeps it small instead of the old tall list.
function BlockPicker({ types, onPick, onCancel }: {
  types: ContentBlock['type'][]
  onPick: (type: ContentBlock['type']) => void
  onCancel: () => void
}) {
  return (
    <div style={{
      border: '1px solid #E2E2E2', borderRadius: 10, background: '#fff',
      boxShadow: '0 4px 16px rgba(0,0,0,0.10)', padding: 6, margin: '4px 0',
      display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 4,
    }}>
      {types.map(type => (
        <button key={type} type="button" onClick={() => onPick(type)} style={{
          textAlign: 'left', padding: '6px 9px', borderRadius: 6,
          background: '#FAFAFA', border: '1px solid #F0EFED',
          fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 12.5,
          lineHeight: 1.25, color: '#3C3C3C', cursor: 'pointer',
        }}>
          {BLOCK_LABELS[type]}
        </button>
      ))}
      <button type="button" onClick={onCancel} style={{
        gridColumn: '1 / -1', textAlign: 'center', padding: '5px',
        background: 'none', border: 'none', borderTop: '1px solid #F0EFED',
        marginTop: 2, fontFamily: 'var(--dlw-font-body)', fontSize: 12,
        color: '#8A8A8A', cursor: 'pointer',
      }}>
        Cancel
      </button>
    </div>
  )
}

// The thin insertion slot that lives in the gap between two blocks (and above
// the first one). Shows a small, subtle + that lights up on hover; clicking it
// opens the compact picker in place.
function InsertZone({ open, types, onOpen, onPick, onCancel }: {
  open: boolean
  types: ContentBlock['type'][]
  onOpen: () => void
  onPick: (type: ContentBlock['type']) => void
  onCancel: () => void
}) {
  const [hovered, setHovered] = useState(false)

  if (open) return <BlockPicker types={types} onPick={onPick} onCancel={onCancel} />

  return (
    <div
      onClick={onOpen}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title="Add block here"
      style={{
        position: 'relative', height: 20, cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div style={{
        position: 'absolute', left: 0, right: 0, height: 2, borderRadius: 2,
        background: hovered ? '#3BC9BC' : 'transparent', transition: 'background 0.12s',
      }} />
      <div style={{
        position: 'relative', zIndex: 1,
        width: 20, height: 20, borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: hovered ? '#3BC9BC' : '#fff',
        border: `1.5px solid ${hovered ? '#3BC9BC' : '#DADADA'}`,
        color: hovered ? '#fff' : '#B0B0B0',
        fontSize: 15, lineHeight: 1, fontWeight: 600,
        boxShadow: hovered ? '0 1px 4px rgba(0,0,0,0.12)' : 'none',
        transition: 'all 0.12s',
      }}>
        +
      </div>
    </div>
  )
}

export interface EditedLesson {
  title: string
  content_blocks: ContentBlock[]
}

// The minimal structural shape this component actually reads (lesson.id,
// lesson.title, lesson.content_blocks). Narrowed from a full LessonDetail so
// a caller can pass a synthetic lesson (e.g. built from an AI proposal)
// without fabricating an entire LessonDetail — any real lesson still
// satisfies this structurally, so existing callers are unaffected.
interface EditableLesson {
  id: string
  title: string
  content_blocks: unknown[]
}

interface LessonEditorProps {
  lesson: EditableLesson
  onSave?: (updated: EditedLesson) => void
  onLiveChange?: (updated: EditedLesson) => void
  // When true, this instance is embedded in another surface (e.g. the content
  // review pane) that owns saving: the toolbar's dirty label and Save button
  // are not rendered, so `save()` — which PATCHes /api/admin/lessons/{id} —
  // is never reachable from that surface.
  embedded?: boolean
}

export default function LessonEditor({ lesson, onSave, onLiveChange, embedded = false }: LessonEditorProps) {
  const [title, setTitle]     = useState(lesson.title ?? '')
  const [blocks, setBlocks]   = useState<ContentBlock[]>((lesson.content_blocks as ContentBlock[] | undefined) ?? [])
  const [dirty, setDirty]     = useState(false)
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState<string | null>(null)
  // Index at which the block picker is open (a new block is inserted here);
  // null = closed. blocks.length = the bottom "+ Add block" (append).
  const [addAt, setAddAt]     = useState<number | null>(null)
  const mounted = useRef(false)
  // Which block types the picker offers — see EMBEDDED_TYPE_ORDER above.
  const pickerTypes = embedded ? EMBEDDED_TYPE_ORDER : TYPE_ORDER
  // `dirty` tracks every block/title edit and clears only on a successful save.
  // Embedded instances have no Save, so their `dirty` never clears — guarding
  // them would nag even after the host has saved. The host guards instead.
  useUnsavedGuard(dirty && !embedded)

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

  function addBlock(type: ContentBlock['type'], index: number) {
    setBlocks(bs => {
      const next = [...bs]
      next.splice(index, 0, BLOCK_FACTORIES[type]())
      return next
    })
    setDirty(true)
    setAddAt(null)
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

      {/* Toolbar — embedded instances (e.g. the content review pane) own
          saving themselves, so neither the dirty label nor the Save button
          (the only call site of `save()`) is rendered here. */}
      {!embedded && (
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
      )}

      {error && (
        <div style={{ padding: '10px 20px', background: '#FEF2F2', color: '#C42828', fontFamily: 'var(--dlw-font-body)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>

        {/* Lesson title — embedded instances don't carry it: onLiveChange's
            consumer (the review pane) only reads content_blocks, and the
            accept path never writes a title, so an edit here would be
            silently discarded. The title has its own editing path in the
            full (non-embedded) editor, where it belongs. */}
        {!embedded && (
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
        )}

        {/* Blocks — an insertion slot sits above each block (the first one is
            the "plus at the top"); the bottom "+ Add block" handles append. */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {blocks.map((block, i) => {
            // TS can't correlate block.type with block across the map lookup;
            // the mapped type above guarantees the pairing, so one widening cast
            // (same pattern as LessonView's RENDERERS).
            const Editor = EDITORS[block.type] as ComponentType<{ block: ContentBlock; onChange: (b: ContentBlock) => void }>
            if (!Editor) return null // content_blocks is JSONB — tolerate unknown types
            return (
              <Fragment key={block.id}>
              <InsertZone
                open={addAt === i}
                types={pickerTypes}
                onOpen={() => setAddAt(i)}
                onPick={type => addBlock(type, i)}
                onCancel={() => setAddAt(null)}
              />
              <div style={{
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
              </Fragment>
            )
          })}
        </div>

        {/* Add block (append at the end) */}
        <div style={{ marginTop: 12 }}>
          {addAt === blocks.length ? (
            <BlockPicker
              types={pickerTypes}
              onPick={type => addBlock(type, blocks.length)}
              onCancel={() => setAddAt(null)}
            />
          ) : (
            <button type="button" onClick={() => setAddAt(blocks.length)} style={{
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
