import type { QuestionBlock as QuestionBlockType } from '../../../types/contentBlocks'
import { renderInline } from './renderInline'

interface QuestionBlockProps {
  block: QuestionBlockType
  answer?: string
  onAnswerChange?: (blockId: string, text: string) => void
}

export default function QuestionBlock({ block, answer, onAnswerChange }: QuestionBlockProps) {
  return (
    <div style={{
      background: '#fff',
      border: '1px solid #E2E2E2',
      borderRadius: 12,
      padding: '24px 28px',
      margin: '0 0 24px',
    }}>
      <p style={{
        fontFamily: 'var(--dlw-font-body)',
        fontWeight: 600,
        fontSize: 15,
        color: '#101820',
        margin: '0 0 12px',
      }}>
        {renderInline(block.prompt)}
      </p>
      <textarea
        value={answer ?? ''}
        onChange={e => onAnswerChange?.(block.id, e.target.value)}
        placeholder="Type your answer…"
        rows={4}
        style={{
          width: '100%',
          padding: '10px 14px',
          border: '1px solid #E2E2E2',
          borderRadius: 8,
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
