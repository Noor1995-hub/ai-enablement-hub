import type { CalloutBlock as CalloutBlockType } from '../../../types/contentBlocks'
import { renderInline } from './renderInline'

export default function CalloutBlock({ block }: { block: CalloutBlockType }) {
  return (
    <div style={{
      borderLeft: '4px solid #C42828',
      background: '#fff',
      borderRadius: '0 10px 10px 0',
      padding: '16px 20px',
      margin: '0 0 16px',
    }}>
      <p style={{
        fontFamily: 'var(--dlw-font-body)',
        fontWeight: 400,
        fontSize: 15,
        lineHeight: 1.6,
        color: '#3C3C3C',
        margin: 0,
      }}>
        {renderInline(block.text)}
      </p>
    </div>
  )
}
