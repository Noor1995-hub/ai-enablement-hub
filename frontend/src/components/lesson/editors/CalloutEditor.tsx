import type { CalloutBlock } from '../../../types/contentBlocks'

interface CalloutEditorProps {
  block: CalloutBlock
  onChange: (b: CalloutBlock) => void
}

export default function CalloutEditor({ block, onChange }: CalloutEditorProps) {
  return (
    <div>
      <label style={{
        fontFamily: 'var(--dlw-font-ui)',
        fontWeight: 600,
        fontSize: 11,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: '#8A8A8A',
        marginBottom: 6,
        display: 'block',
      }}>
        Callout text
      </label>
      <textarea
        value={block.text}
        onChange={e => onChange({ ...block, text: e.target.value })}
        placeholder="Callout message…"
        rows={3}
        style={{
          width: '100%',
          padding: '8px 12px',
          border: '1px solid #E2E2E2',
          borderLeft: '4px solid #C42828',
          borderRadius: '0 8px 8px 0',
          fontFamily: 'var(--dlw-font-body)',
          fontSize: 14,
          color: '#101820',
          lineHeight: 1.6,
          resize: 'vertical',
          outline: 'none',
          boxSizing: 'border-box',
        }}
      />
    </div>
  )
}
