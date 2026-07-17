import { useState, useEffect, type CSSProperties } from 'react'
import type { QuizBlock as QuizBlockType, QuizQuestion } from '../../../types/contentBlocks'

function shuffleQuestions(questions: QuizQuestion[]): QuizQuestion[] {
  return questions.map(q => {
    const correctText = q.options[q.correct]
    const shuffled = [...q.options].sort(() => Math.random() - 0.5)
    return { ...q, options: shuffled, correct: shuffled.indexOf(correctText) }
  })
}

interface QuizBlockProps {
  block: QuizBlockType
  onComplete?: () => void
}

export default function QuizBlock({ block, onComplete }: QuizBlockProps) {
  const [shuffledQuestions, setShuffledQuestions] = useState<QuizQuestion[]>(block.questions ?? [])
  const [currentIndex, setCurrentIndex]     = useState(0)
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [showFeedback, setShowFeedback]     = useState(false)
  const [answers, setAnswers]               = useState<(number | null)[]>([])
  const [phase, setPhase]                   = useState<'quiz' | 'results'>('quiz')

  const isLast     = currentIndex === shuffledQuestions.length - 1
  const score      = answers.filter((a, i) => a === shuffledQuestions[i]?.correct).length
  const allCorrect = shuffledQuestions.length > 0 && answers.length === shuffledQuestions.length && score === shuffledQuestions.length

  // Shuffle runs client-only after mount to avoid SSR/hydration mismatch
  useEffect(() => {
    if (shuffledQuestions.length > 0) setShuffledQuestions(shuffleQuestions(shuffledQuestions))
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only shuffle, same as the old app
  }, [])

  // Answering the final question unlocks completion: once its feedback shows,
  // every question has been answered once, so "Mark as complete" appears at the
  // same moment "See results" does — the learner does not have to click through
  // to the results screen first. Reaching results also unlocks it (belt and
  // braces). The quiz stays obligatory (you must answer every question once),
  // but score is irrelevant and Retake stays optional.
  useEffect(() => {
    if (phase === 'results' || (isLast && showFeedback)) {
      onComplete?.()
    }
  }, [phase, isLast, showFeedback, onComplete])

  if (!shuffledQuestions.length) return null

  const q = shuffledQuestions[currentIndex]

  function handleSelect(oi: number) {
    if (showFeedback) return
    setSelectedOption(oi)
    setShowFeedback(true)
  }

  function handleNext() {
    const next = [...answers, selectedOption]
    setAnswers(next)
    if (isLast) {
      setPhase('results')
    } else {
      setCurrentIndex(i => i + 1)
      setSelectedOption(null)
      setShowFeedback(false)
    }
  }

  function handleRetake() {
    setShuffledQuestions(shuffleQuestions(block.questions ?? []))
    setCurrentIndex(0)
    setSelectedOption(null)
    setShowFeedback(false)
    setAnswers([])
    setPhase('quiz')
  }

  const card: CSSProperties = {
    background: '#fff',
    border: '1px solid #E2E2E2',
    borderRadius: 12,
    boxShadow: '0 1px 4px rgba(0,0,0,.05)',
    padding: '24px 28px',
    margin: '0 0 24px',
  }

  if (phase === 'results') {
    return (
      <div style={card}>
        <h2 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 18, color: '#101820', margin: '0 0 4px' }}>
          Quiz results
        </h2>
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 36, color: allCorrect ? '#1D7A52' : '#B45309', margin: '0 0 4px' }}>
          {score}/{shuffledQuestions.length}
        </p>
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: '0 0 20px' }}>
          {allCorrect
            ? 'You answered everything correctly. Scroll down to continue.'
            : `You got ${score} out of ${shuffledQuestions.length} right. You can continue below, or retake the quiz to improve your score.`}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
          {shuffledQuestions.map((qq, i) => {
            const correct = answers[i] === qq.correct
            return (
              <div key={i} style={{
                display: 'flex', gap: 12, padding: '10px 14px',
                borderRadius: 8,
                background: correct ? '#EDFAF4' : '#FEF2F2',
              }}>
                <span style={{ fontWeight: 700, flexShrink: 0, color: correct ? '#1D7A52' : '#C42828' }}>
                  {correct ? '✓' : '✗'}
                </span>
                <div>
                  <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, color: correct ? '#1D7A52' : '#991B1B', margin: '0 0 2px' }}>
                    {qq.q}
                  </p>
                  <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 13, color: '#8A8A8A', margin: 0 }}>
                    {correct
                      ? `Your answer: ${qq.options[answers[i] ?? -1]}`
                      : `Correct answer: ${qq.options[qq.correct]}`}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {allCorrect ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#1D7A52', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14 }}>
            <span>✓</span> All correct — scroll down to continue
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
            <button onClick={handleRetake} className="btn-ghost" style={{
              padding: '10px 22px', borderRadius: 999,
              border: '1.5px solid #E2E2E2', background: '#fff',
              color: '#3C3C3C', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14,
              cursor: 'pointer',
            }}>
              Retake quiz
            </button>
            <span style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: '#3C3C3C' }}>
              or scroll down to continue ↓
            </span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 18, color: '#101820', margin: 0 }}>
          Quiz
        </h2>
        <span style={{ fontFamily: 'var(--dlw-font-ui)', fontSize: 12, color: '#8A8A8A' }}>
          {currentIndex + 1} / {shuffledQuestions.length}
        </span>
      </div>

      <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 15, color: '#101820', margin: '0 0 16px' }}>
        {q.q}
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
        {q.options.map((opt, oi) => {
          const isSelected  = selectedOption === oi
          const isCorrectOpt = q.correct === oi
          let bg = '#fff', border = '1px solid #E2E2E2', color = '#3C3C3C'

          if (showFeedback) {
            if (isCorrectOpt)      { bg = '#EDFAF4'; border = '1.5px solid #1D7A52'; color = '#1D7A52' }
            else if (isSelected)   { bg = '#FEF2F2'; border = '1.5px solid #C42828'; color = '#991B1B' }
            else                   { border = '1px solid #F0EFED'; color = '#B0B0B0' }
          }

          return (
            <button key={oi} onClick={() => handleSelect(oi)} style={{
              width: '100%', textAlign: 'left', padding: '12px 16px',
              borderRadius: 8, border, background: bg, color,
              fontFamily: 'var(--dlw-font-body)', fontSize: 14,
              cursor: showFeedback ? 'default' : 'pointer',
              transition: 'border-color 0.15s, background 0.15s',
            }}>
              {opt}
            </button>
          )
        })}
      </div>

      {showFeedback && q.explanation && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 16,
          background: selectedOption === q.correct ? '#EDFAF4' : '#FEF2F2',
          color: selectedOption === q.correct ? '#1D7A52' : '#991B1B',
        }}>
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, margin: '0 0 4px' }}>
            {selectedOption === q.correct ? '✓ Correct' : '✗ Not quite'}
          </p>
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 13, margin: 0 }}>
            {q.explanation}
          </p>
        </div>
      )}

      {showFeedback && (
        <button onClick={handleNext} className="lesson-cta" style={{
          padding: '11px 18px', borderRadius: 8,
          background: '#C42828', border: 'none', color: '#fff',
          fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
          cursor: 'pointer',
        }}>
          {isLast ? 'See results' : 'Next question →'}
        </button>
      )}
    </div>
  )
}
