// The key type of the codebase: the discriminated union for lessons.content_blocks
// (JSONB boundary). Verified against app/src/lib/contentBlocks.js — 7 types
// including `question` (design-frontend.md §3).

export type HeadingBlock = { id: string; type: 'heading'; level: 1 | 2 | 3; text: string }
export type ParagraphBlock = { id: string; type: 'paragraph'; text: string }
export type CalloutBlock = { id: string; type: 'callout'; text: string }
export type Card = { id: string; title: string; body: string }
export type CardGroupBlock = { id: string; type: 'card_group'; cards: Card[] }
export type QuizQuestion = {
  id: string
  q: string
  options: string[]
  correct: number
  explanation: string
}
export type QuizBlock = { id: string; type: 'quiz'; questions: QuizQuestion[] }
export type QuestionBlock = { id: string; type: 'question'; prompt: string }
export type WhitespaceBlock = { id: string; type: 'whitespace'; size: 'sm' | 'md' | 'lg' }

export type ContentBlock =
  | HeadingBlock
  | ParagraphBlock
  | CalloutBlock
  | CardGroupBlock
  | QuizBlock
  | QuestionBlock
  | WhitespaceBlock

export type ContentBlockType = ContentBlock['type']
