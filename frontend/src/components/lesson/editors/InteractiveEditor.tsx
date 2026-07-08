import type { InteractiveBlock } from '../../../types/contentBlocks'
import { createPredictMode, createSortMode, createSpotTheFlawMode } from '../../../lib/contentBlocks'

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--dlw-font-ui)',
  fontWeight: 600,
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: '#8A8A8A',
  marginBottom: 4,
  display: 'block',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  border: '1px solid #E2E2E2',
  borderRadius: 6,
  fontFamily: 'var(--dlw-font-body)',
  fontSize: 13,
  color: '#101820',
  outline: 'none',
  boxSizing: 'border-box',
}

const removeButtonStyle: React.CSSProperties = {
  padding: '2px 8px', borderRadius: 4, border: '1px solid #E2E2E2',
  background: '#fff', fontFamily: 'var(--dlw-font-ui)', fontSize: 11, color: '#8A8A8A', cursor: 'pointer', flexShrink: 0,
}

const addButtonStyle: React.CSSProperties = {
  padding: '5px 0', border: '1px dashed #E2E2E2', borderRadius: 6,
  background: 'none', color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)', fontSize: 12, cursor: 'pointer',
}

interface InteractiveEditorProps {
  block: InteractiveBlock
  onChange: (b: InteractiveBlock) => void
}

function ModeSwitch({ block, onChange }: InteractiveEditorProps) {
  return (
    <div>
      <label style={labelStyle}>Mode</label>
      <select
        style={{ ...inputStyle, width: 'auto' }}
        value={block.mode}
        onChange={e => {
          const mode = e.target.value
          if (mode === 'sort') onChange(createSortMode())
          else if (mode === 'predict') onChange(createPredictMode())
          else onChange(createSpotTheFlawMode())
        }}
      >
        <option value="sort">Sort</option>
        <option value="predict">Predict</option>
        <option value="spot_the_flaw">Spot the flaw</option>
      </select>
    </div>
  )
}

function SortEditor({ block, onChange }: { block: Extract<InteractiveBlock, { mode: 'sort' }>; onChange: (b: InteractiveBlock) => void }) {
  function updateBucket(bi: number, label: string) {
    onChange({ ...block, buckets: block.buckets.map((b, i) => i === bi ? { ...b, label } : b) })
  }

  function addBucket() {
    onChange({ ...block, buckets: [...block.buckets, { id: crypto.randomUUID(), label: '' }] })
  }

  function removeBucket(bi: number) {
    const removed = block.buckets[bi]
    onChange({
      ...block,
      buckets: block.buckets.filter((_, i) => i !== bi),
      items: block.items.map(item => item.bucketId === removed.id ? { ...item, bucketId: '' } : item),
    })
  }

  function updateItem(ii: number, patch: Partial<typeof block.items[number]>) {
    onChange({ ...block, items: block.items.map((it, i) => i === ii ? { ...it, ...patch } : it) })
  }

  function addItem() {
    onChange({ ...block, items: [...block.items, { id: crypto.randomUUID(), text: '', bucketId: block.buckets[0]?.id ?? '', reason: '' }] })
  }

  function removeItem(ii: number) {
    onChange({ ...block, items: block.items.filter((_, i) => i !== ii) })
  }

  return (
    <>
      <div>
        <label style={labelStyle}>Buckets</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {block.buckets.map((bucket, bi) => (
            <div key={bucket.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input style={{ ...inputStyle, flex: 1 }} value={bucket.label}
                onChange={e => updateBucket(bi, e.target.value)} placeholder={`Bucket ${bi + 1} label…`} />
              {block.buckets.length > 2 && (
                <button type="button" onClick={() => removeBucket(bi)} style={removeButtonStyle}>×</button>
              )}
            </div>
          ))}
          {block.buckets.length < 3 && (
            <button type="button" onClick={addBucket} style={addButtonStyle}>+ Add bucket</button>
          )}
        </div>
      </div>

      <div>
        <label style={labelStyle}>Items</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {block.items.map((item, ii) => (
            <div key={item.id} style={{ border: '1px solid #E2E2E2', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input style={{ ...inputStyle, flex: 1 }} value={item.text}
                  onChange={e => updateItem(ii, { text: e.target.value })} placeholder="Item text…" />
                <button type="button" onClick={() => removeItem(ii)} style={removeButtonStyle}>×</button>
              </div>
              <select style={inputStyle} value={item.bucketId} onChange={e => updateItem(ii, { bucketId: e.target.value })}>
                <option value="">Correct bucket…</option>
                {block.buckets.map(b => <option key={b.id} value={b.id}>{b.label || '(unlabelled)'}</option>)}
              </select>
              <input style={inputStyle} value={item.reason}
                onChange={e => updateItem(ii, { reason: e.target.value })} placeholder="One-line reason shown on reveal…" />
            </div>
          ))}
          <button type="button" onClick={addItem} style={addButtonStyle}>+ Add item</button>
        </div>
      </div>
    </>
  )
}

function PredictEditor({ block, onChange }: { block: Extract<InteractiveBlock, { mode: 'predict' }>; onChange: (b: InteractiveBlock) => void }) {
  function updateOption(oi: number, patch: Partial<typeof block.options[number]>) {
    onChange({ ...block, options: block.options.map((o, i) => i === oi ? { ...o, ...patch } : o) })
  }

  function addOption() {
    onChange({ ...block, options: [...block.options, { id: crypto.randomUUID(), label: '', reason: '' }] })
  }

  function removeOption(oi: number) {
    const removed = block.options[oi]
    onChange({
      ...block,
      options: block.options.filter((_, i) => i !== oi),
      correctOptionId: block.correctOptionId === removed.id ? '' : block.correctOptionId,
    })
  }

  return (
    <div>
      <label style={labelStyle}>Options — click the circle to mark the actual outcome</label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {block.options.map((opt, oi) => (
          <div key={opt.id} style={{ border: '1px solid #E2E2E2', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button type="button" onClick={() => onChange({ ...block, correctOptionId: opt.id })} style={{
                width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                border: '2px solid', borderColor: block.correctOptionId === opt.id ? '#3BC9BC' : '#E2E2E2',
                background: block.correctOptionId === opt.id ? '#3BC9BC' : '#fff',
                cursor: 'pointer',
              }} />
              <input style={{ ...inputStyle, flex: 1 }} value={opt.label}
                onChange={e => updateOption(oi, { label: e.target.value })} placeholder={`Option ${oi + 1}…`} />
              {block.options.length > 2 && (
                <button type="button" onClick={() => removeOption(oi)} style={removeButtonStyle}>×</button>
              )}
            </div>
            <input style={inputStyle} value={opt.reason}
              onChange={e => updateOption(oi, { reason: e.target.value })} placeholder="One-line reason shown on reveal…" />
          </div>
        ))}
        <button type="button" onClick={addOption} style={addButtonStyle}>+ Add option</button>
      </div>
    </div>
  )
}

function SpotTheFlawEditor({ block, onChange }: { block: Extract<InteractiveBlock, { mode: 'spot_the_flaw' }>; onChange: (b: InteractiveBlock) => void }) {
  function updateCandidate(ci: number, patch: Partial<typeof block.candidates[number]>) {
    onChange({ ...block, candidates: block.candidates.map((c, i) => i === ci ? { ...c, ...patch } : c) })
  }

  function addCandidate() {
    onChange({ ...block, candidates: [...block.candidates, { id: crypto.randomUUID(), text: '', isFlaw: false, reason: '' }] })
  }

  function removeCandidate(ci: number) {
    onChange({ ...block, candidates: block.candidates.filter((_, i) => i !== ci) })
  }

  return (
    <>
      <div>
        <label style={labelStyle}>Worked example</label>
        <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={4}
          value={block.example} onChange={e => onChange({ ...block, example: e.target.value })}
          placeholder="The prompt or output the learner reviews…" />
      </div>

      <div>
        <label style={labelStyle}>Candidates — mark which one is the planted flaw</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {block.candidates.map((candidate, ci) => (
            <div key={candidate.id} style={{ border: '1px solid #E2E2E2', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button type="button" onClick={() => updateCandidate(ci, { isFlaw: true })} style={{
                  width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                  border: '2px solid', borderColor: candidate.isFlaw ? '#3BC9BC' : '#E2E2E2',
                  background: candidate.isFlaw ? '#3BC9BC' : '#fff',
                  cursor: 'pointer',
                }} />
                <input style={{ ...inputStyle, flex: 1 }} value={candidate.text}
                  onChange={e => updateCandidate(ci, { text: e.target.value })} placeholder="Candidate text…" />
                <button type="button" onClick={() => removeCandidate(ci)} style={removeButtonStyle}>×</button>
              </div>
              <input style={inputStyle} value={candidate.reason}
                onChange={e => updateCandidate(ci, { reason: e.target.value })} placeholder="One-line reason shown on reveal…" />
            </div>
          ))}
          <button type="button" onClick={addCandidate} style={addButtonStyle}>+ Add candidate</button>
        </div>
      </div>
    </>
  )
}

export default function InteractiveEditor({ block, onChange }: InteractiveEditorProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <ModeSwitch block={block} onChange={onChange} />

      <div>
        <label style={labelStyle}>Prompt</label>
        <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={2}
          value={block.prompt} onChange={e => onChange({ ...block, prompt: e.target.value })}
          placeholder="What the learner is asked to do…" />
      </div>

      {block.mode === 'sort' && <SortEditor block={block} onChange={onChange} />}
      {block.mode === 'predict' && <PredictEditor block={block} onChange={onChange} />}
      {block.mode === 'spot_the_flaw' && <SpotTheFlawEditor block={block} onChange={onChange} />}
    </div>
  )
}
