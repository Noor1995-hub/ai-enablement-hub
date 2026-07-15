import type { KickerBlock } from '../../../types/contentBlocks'

interface KickerEditorProps {
  block: KickerBlock
  onChange: (b: KickerBlock) => void
}

export default function KickerEditor({ block, onChange }: KickerEditorProps) {
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
        Kicker text
      </label>
      <textarea
        value={block.text}
        onChange={e => onChange({ ...block, text: e.target.value })}
        placeholder="Short subtitle line under the lesson title…"
        rows={1}
        style={{
          width: '100%',
          padding: '8px 12px',
          border: '1px solid #E2E2E2',
          borderRadius: 8,
          fontFamily: 'var(--dlw-font-body)',
          fontStyle: 'italic',
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
