import type { ComponentType } from 'react'
import type { ContentBlock } from '../../types/contentBlocks'
import HeadingBlock   from './blocks/HeadingBlock'
import ParagraphBlock from './blocks/ParagraphBlock'
import CalloutBlock   from './blocks/CalloutBlock'
import CardsBlock     from './blocks/CardsBlock'
import QuizBlock      from './blocks/QuizBlock'
import QuestionBlock  from './blocks/QuestionBlock'
import SpacerBlock    from './blocks/SpacerBlock'
import InteractiveBlock from './blocks/InteractiveBlock'
import TryItYourselfBlock from './blocks/TryItYourselfBlock'

interface BlockExtraProps {
  onComplete?: () => void
  answer?: string
  onAnswerChange?: (blockId: string, text: string) => void
}

// Exhaustively keyed on the discriminated union: adding an 8th block type to
// ContentBlock breaks this map at compile time until a renderer is registered.
const RENDERERS: {
  [K in ContentBlock['type']]: ComponentType<{ block: Extract<ContentBlock, { type: K }> } & BlockExtraProps>
} = {
  heading:    HeadingBlock,
  paragraph:  ParagraphBlock,
  callout:    CalloutBlock,
  card_group: CardsBlock,
  quiz:       QuizBlock,
  question:   QuestionBlock,
  whitespace: SpacerBlock,
  interactive: InteractiveBlock,
  try_it_yourself: TryItYourselfBlock,
}

interface LessonViewProps {
  blocks?: ContentBlock[]
  onQuizComplete?: () => void
  answers?: Record<string, string>
  onAnswerChange?: (blockId: string, text: string) => void
}

export default function LessonView({ blocks = [], onQuizComplete, answers, onAnswerChange }: LessonViewProps) {
  if (!blocks.length) {
    return (
      <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 15, color: '#8A8A8A', fontStyle: 'italic' }}>
        No content yet.
      </p>
    )
  }

  return (
    <div>
      {blocks.map(block => {
        // TS can't correlate block.type with block across the map lookup;
        // the mapped type above guarantees the pairing, so one widening cast.
        const Component = RENDERERS[block.type] as ComponentType<{ block: ContentBlock } & BlockExtraProps>
        if (!Component) return null // content_blocks is JSONB — tolerate unknown types
        return (
          <Component
            key={block.id}
            block={block}
            onComplete={block.type === 'quiz' ? onQuizComplete : undefined}
            answer={block.type === 'question' ? answers?.[block.id] : undefined}
            onAnswerChange={block.type === 'question' ? onAnswerChange : undefined}
          />
        )
      })}
    </div>
  )
}
