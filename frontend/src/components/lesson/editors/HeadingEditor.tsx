import type { HeadingBlock } from '../../../types/contentBlocks'

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--dlw-font-ui)',
  fontWeight: 600,
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: '#8A8A8A',
  marginBottom: 6,
  display: 'block',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  border: '1px solid #E2E2E2',
  borderRadius: 8,
  fontFamily: 'var(--dlw-font-body)',
  fontSize: 14,
  color: '#101820',
  outline: 'none',
  boxSizing: 'border-box',
}

interface HeadingEditorProps {
  block: HeadingBlock
  onChange: (b: HeadingBlock) => void
}

export default function HeadingEditor({ block, onChange }: HeadingEditorProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <span style={labelStyle}>Level</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {([1, 2, 3] as const).map(lvl => (
            <button key={lvl} type="button" onClick={() => onChange({ ...block, level: lvl })} style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: '1.5px solid',
              borderColor: block.level === lvl ? '#3BC9BC' : '#E2E2E2',
              background: block.level === lvl ? '#F0FAF9' : '#fff',
              color: block.level === lvl ? '#1D7A52' : '#8A8A8A',
              fontFamily: 'var(--dlw-font-ui)',
              fontWeight: 700,
              fontSize: 13,
              cursor: 'pointer',
            }}>
              H{lvl}
            </button>
          ))}
        </div>
      </div>
      <div>
        <label style={labelStyle}>Text</label>
        <input
          style={inputStyle}
          value={block.text}
          onChange={e => onChange({ ...block, text: e.target.value })}
          placeholder="Heading text…"
        />
      </div>
    </div>
  )
}
