import type { TryItYourselfBlock } from '../../../types/contentBlocks'

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

interface TryItYourselfEditorProps {
  block: TryItYourselfBlock
  onChange: (b: TryItYourselfBlock) => void
}

export default function TryItYourselfEditor({ block, onChange }: TryItYourselfEditorProps) {
  function updateStep(si: number, patch: Partial<TryItYourselfBlock['steps'][number]>) {
    onChange({ ...block, steps: block.steps.map((s, i) => i === si ? { ...s, ...patch } : s) })
  }

  function addStep() {
    onChange({ ...block, steps: [...block.steps, { id: crypto.randomUUID(), label: '', text: '' }] })
  }

  function removeStep(si: number) {
    onChange({ ...block, steps: block.steps.filter((_, i) => i !== si) })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <label style={labelStyle}>Task</label>
        <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={2}
          value={block.task} onChange={e => onChange({ ...block, task: e.target.value })}
          placeholder="What the learner does in their own tool…" />
      </div>

      <div>
        <label style={labelStyle}>Material (sample content, never real confidential data)</label>
        <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={3}
          value={block.material} onChange={e => onChange({ ...block, material: e.target.value })}
          placeholder="Made-up sample the learner uses…" />
      </div>

      <div>
        <label style={labelStyle}>Steps (prompts to run, in order)</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {block.steps.map((step, si) => (
            <div key={step.id} style={{ border: '1px solid #E2E2E2', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input style={{ ...inputStyle, flex: 1 }} value={step.label}
                  onChange={e => updateStep(si, { label: e.target.value })} placeholder="Label, e.g. Prompt A…" />
                <button type="button" onClick={() => removeStep(si)} style={removeButtonStyle}>×</button>
              </div>
              <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={2} value={step.text}
                onChange={e => updateStep(si, { text: e.target.value })} placeholder="The exact prompt text…" />
            </div>
          ))}
          <button type="button" onClick={addStep} style={addButtonStyle}>+ Add step</button>
        </div>
      </div>

      <div>
        <label style={labelStyle}>What to notice</label>
        <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={2}
          value={block.whatToNotice} onChange={e => onChange({ ...block, whatToNotice: e.target.value })}
          placeholder="What tells the learner it worked, without needing our feedback…" />
      </div>
    </div>
  )
}
