import type { WhitespaceBlock } from '../../../types/contentBlocks'

const SIZES: { value: WhitespaceBlock['size']; label: string }[] = [
  { value: 'sm', label: 'S' },
  { value: 'md', label: 'M' },
  { value: 'lg', label: 'L' },
]

interface SpacerEditorProps {
  block: WhitespaceBlock
  onChange: (b: WhitespaceBlock) => void
}

export default function SpacerEditor({ block, onChange }: SpacerEditorProps) {
  const current = block.size ?? 'md'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span style={{
        fontFamily: 'var(--dlw-font-ui)', fontSize: 12, color: '#8A8A8A',
        fontWeight: 500,
      }}>
        Size
      </span>
      <div style={{ display: 'flex', gap: 6 }}>
        {SIZES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => onChange({ ...block, size: value })}
            style={{
              padding: '4px 14px', borderRadius: 6,
              border: current === value ? '1.5px solid #3BC9BC' : '1px solid #E2E2E2',
              background: current === value ? '#F0FFFE' : '#fff',
              color: current === value ? '#3BC9BC' : '#3C3C3C',
              fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
