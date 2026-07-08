import type { TryItYourselfBlock as TryItYourselfBlockType } from '../../../types/contentBlocks'
import { renderInline } from './renderInline'

const ACCENT = '#B45309' // amber — distinct from the red/teal/purple already in use for callouts/cards/interactive

interface TryItYourselfBlockProps {
  block: TryItYourselfBlockType
}

export default function TryItYourselfBlock({ block }: TryItYourselfBlockProps) {
  return (
    <div style={{
      background: '#fff',
      borderLeft: `4px solid ${ACCENT}`,
      borderRadius: '0 10px 10px 0',
      padding: '20px 24px',
      margin: '0 0 24px',
    }}>
      <span style={{
        fontFamily: 'var(--dlw-font-ui)',
        fontWeight: 700,
        fontSize: 11,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: ACCENT,
        display: 'block',
        marginBottom: 10,
      }}>
        Try it yourself · optional
      </span>

      {block.task && (
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 15, color: '#101820', margin: '0 0 14px' }}>
          {renderInline(block.task)}
        </p>
      )}

      {block.material && (
        <div style={{
          background: '#FAFAFA', border: '1px solid #E2E2E2', borderRadius: 8,
          padding: '12px 16px', marginBottom: 14,
        }}>
          <span style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#8A8A8A', display: 'block', marginBottom: 4 }}>
            Material
          </span>
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#3C3C3C', margin: 0, lineHeight: 1.6 }}>
            {renderInline(block.material)}
          </p>
        </div>
      )}

      {block.steps.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
          {block.steps.map(step => (
            <div key={step.id} style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 8, padding: '12px 16px' }}>
              <span style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: ACCENT, display: 'block', marginBottom: 4 }}>
                {step.label}
              </span>
              <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#3C3C3C', margin: 0, lineHeight: 1.6, fontStyle: 'italic' }}>
                {renderInline(step.text)}
              </p>
            </div>
          ))}
        </div>
      )}

      {block.whatToNotice && (
        <div>
          <span style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#8A8A8A', display: 'block', marginBottom: 4 }}>
            What to notice
          </span>
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#3C3C3C', margin: 0, lineHeight: 1.6 }}>
            {renderInline(block.whatToNotice)}
          </p>
        </div>
      )}
    </div>
  )
}
