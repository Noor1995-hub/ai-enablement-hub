import type { KickerBlock as KickerBlockType } from '../../../types/contentBlocks'
import { renderInline } from './renderInline'

export default function KickerBlock({ block }: { block: KickerBlockType }) {
  return (
    <p style={{
      fontFamily: 'var(--dlw-font-body)',
      fontStyle: 'italic',
      fontWeight: 300,
      fontSize: 16,
      lineHeight: 1.5,
      color: '#8A8A8A',
      margin: '0 0 16px',
    }}>
      {renderInline(block.text)}
    </p>
  )
}
