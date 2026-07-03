import type { QuizBlock, QuizQuestion } from '../../../types/contentBlocks'

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

interface QuizEditorProps {
  block: QuizBlock
  onChange: (b: QuizBlock) => void
}

export default function QuizEditor({ block, onChange }: QuizEditorProps) {
  const questions = block.questions ?? []

  function updateQuestion(qi: number, updated: QuizQuestion) {
    onChange({ ...block, questions: questions.map((q, i) => i === qi ? updated : q) })
  }

  function addQuestion() {
    onChange({
      ...block,
      questions: [...questions, { id: crypto.randomUUID(), q: '', options: ['', '', ''], correct: 0, explanation: '' }],
    })
  }

  function removeQuestion(qi: number) {
    onChange({ ...block, questions: questions.filter((_, i) => i !== qi) })
  }

  function updateOption(qi: number, oi: number, val: string) {
    const q = questions[qi]
    const opts = q.options.map((o, i) => i === oi ? val : o)
    updateQuestion(qi, { ...q, options: opts })
  }

  function addOption(qi: number) {
    const q = questions[qi]
    updateQuestion(qi, { ...q, options: [...q.options, ''] })
  }

  function removeOption(qi: number, oi: number) {
    const q = questions[qi]
    const opts = q.options.filter((_, i) => i !== oi)
    const correct = q.correct >= opts.length ? opts.length - 1 : q.correct
    updateQuestion(qi, { ...q, options: opts, correct: Math.max(0, correct) })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {questions.map((q, qi) => (
        <div key={q.id ?? qi} style={{ border: '1px solid #E2E2E2', borderRadius: 10, padding: '14px 16px', background: '#FAFAFA' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 12, color: '#8A8A8A' }}>
              Question {qi + 1}
            </span>
            {questions.length > 1 && (
              <button type="button" onClick={() => removeQuestion(qi)} style={{
                padding: '3px 8px', borderRadius: 5, border: '1px solid #FCA5A5',
                background: '#FEF2F2', fontFamily: 'var(--dlw-font-ui)', fontSize: 11, color: '#C42828', cursor: 'pointer',
              }}>
                Remove
              </button>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={labelStyle}>Question</label>
              <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={2}
                value={q.q} onChange={e => updateQuestion(qi, { ...q, q: e.target.value })}
                placeholder="Question text…" />
            </div>

            <div>
              <label style={labelStyle}>Options — click the circle to mark correct</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {q.options.map((opt, oi) => (
                  <div key={oi} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button type="button" onClick={() => updateQuestion(qi, { ...q, correct: oi })} style={{
                      width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                      border: '2px solid', borderColor: q.correct === oi ? '#3BC9BC' : '#E2E2E2',
                      background: q.correct === oi ? '#3BC9BC' : '#fff',
                      cursor: 'pointer',
                    }} />
                    <input style={{ ...inputStyle, flex: 1 }}
                      value={opt} onChange={e => updateOption(qi, oi, e.target.value)}
                      placeholder={`Option ${oi + 1}…`} />
                    {q.options.length > 2 && (
                      <button type="button" onClick={() => removeOption(qi, oi)} style={{
                        padding: '2px 8px', borderRadius: 4, border: '1px solid #E2E2E2',
                        background: '#fff', fontFamily: 'var(--dlw-font-ui)', fontSize: 11, color: '#8A8A8A', cursor: 'pointer', flexShrink: 0,
                      }}>×</button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => addOption(qi)} style={{
                  padding: '5px 0', border: '1px dashed #E2E2E2', borderRadius: 6,
                  background: 'none', color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)', fontSize: 12, cursor: 'pointer',
                }}>
                  + Add option
                </button>
              </div>
            </div>

            <div>
              <label style={labelStyle}>Explanation (optional)</label>
              <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={2}
                value={q.explanation ?? ''} onChange={e => updateQuestion(qi, { ...q, explanation: e.target.value })}
                placeholder="Shown after answering…" />
            </div>
          </div>
        </div>
      ))}

      <button type="button" onClick={addQuestion} style={{
        padding: '8px 0', border: '1.5px dashed #E2E2E2', borderRadius: 8,
        background: 'none', color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)', fontSize: 13, cursor: 'pointer',
      }}>
        + Add question
      </button>
    </div>
  )
}
