import type { QuestionBlock } from '../../../types/contentBlocks'

interface QuestionEditorProps {
  block: QuestionBlock
  onChange: (b: QuestionBlock) => void
}

export default function QuestionEditor({ block, onChange }: QuestionEditorProps) {
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
        Question prompt
      </label>
      <textarea
        value={block.prompt}
        onChange={e => onChange({ ...block, prompt: e.target.value })}
        placeholder="What would you like the learner to reflect on?"
        rows={3}
        style={{
          width: '100%',
          padding: '8px 12px',
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
      <p style={{
        marginTop: 6, fontFamily: 'var(--dlw-font-body)', fontWeight: 300,
        fontSize: 12, color: '#8A8A8A',
      }}>
        Learners will get a free-text box under this prompt. Their answer is saved with their progress when they complete the lesson.
      </p>
    </div>
  )
}
