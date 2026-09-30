import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { silenceRenderErrors } from '../../test/silenceRenderErrors'
import type { ContentBlock } from '../../types/contentBlocks'
import LessonView from './LessonView'

const BLOCK_FALLBACK = "This part of the lesson couldn't be displayed."

// The malformed quiz below throws inside QuizBlock on purpose.
const consoleError = silenceRenderErrors()

const before: ContentBlock = { id: 'p-before', type: 'paragraph', text: 'Paragraph before' }
const after: ContentBlock = { id: 'p-after', type: 'paragraph', text: 'Paragraph after' }
// content_blocks is JSONB: a quiz whose `options` is null (a hand edit, or an
// AI proposal) type-checks nowhere but arrives anyway, and throws while QuizBlock
// renders its options. Parsed from JSON, as the real row would be.
const brokenQuiz: ContentBlock = JSON.parse(
  '{"id":"q-broken","type":"quiz","questions":[{"q":"Broken on purpose","options":null,"correct":0}]}',
)

describe('LessonView per-block error boundary', () => {
  it('contains a throwing block to one inline notice; the blocks around it still render', () => {
    render(<LessonView blocks={[before, brokenQuiz, after]} />)
    expect(screen.getAllByText(BLOCK_FALLBACK)).toHaveLength(1)
    expect(screen.getByText('Paragraph before')).toBeInTheDocument()
    expect(screen.getByText('Paragraph after')).toBeInTheDocument()
    expect(consoleError()).toHaveBeenCalledWith('[ErrorBoundary]', expect.any(TypeError), expect.any(String))
  })

  it('shows no notice when every block is well-formed', () => {
    render(<LessonView blocks={[before, after]} />)
    expect(screen.queryByText(BLOCK_FALLBACK)).not.toBeInTheDocument()
    expect(consoleError()).not.toHaveBeenCalled()
  })

  it('still hands onQuizComplete through to a working quiz', () => {
    const onQuizComplete = vi.fn()
    const quiz: ContentBlock = {
      id: 'q-ok',
      type: 'quiz',
      questions: [{ id: 'qq-1', q: 'Pick the only option', options: ['The only option'], correct: 0, explanation: '' }],
    }
    render(<LessonView blocks={[quiz]} onQuizComplete={onQuizComplete} />)
    fireEvent.click(screen.getByText('The only option'))
    expect(onQuizComplete).toHaveBeenCalled()
  })
})
