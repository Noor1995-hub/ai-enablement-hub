// The key type of the codebase: the discriminated union for lessons.content_blocks
// (JSONB boundary). Verified against app/src/lib/contentBlocks.js — 7 types
// including `question` (design-frontend.md §3), plus `interactive` (predict-or-sort).

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

// predict-or-sort: one component, three modes, sharing one behaviour contract
// (immediate per-item feedback with a one-line reason, forgiving retries,
// non-gating). Click-based rather than drag-based so keyboard/screen-reader
// support comes from native button/select semantics rather than custom ARIA.
export type SortItem = { id: string; text: string; bucketId: string; reason: string }
export type SortBucket = { id: string; label: string }
export type SortBlock = {
  id: string
  type: 'interactive'
  mode: 'sort'
  prompt: string
  buckets: SortBucket[]
  items: SortItem[]
}

export type PredictOption = { id: string; label: string; reason: string }
export type PredictBlock = {
  id: string
  type: 'interactive'
  mode: 'predict'
  prompt: string
  options: PredictOption[]
  correctOptionId: string
}

export type FlawCandidate = { id: string; text: string; isFlaw: boolean; reason: string }
export type SpotTheFlawBlock = {
  id: string
  type: 'interactive'
  mode: 'spot_the_flaw'
  prompt: string
  example: string
  candidates: FlawCandidate[]
}

export type InteractiveBlock = SortBlock | PredictBlock | SpotTheFlawBlock

// "Try it yourself": an optional, non-interactive hands-on exercise the
// learner runs in their own AI tool (no state, no grading — presentational
// only, styled like a card rather than a callout so it reads as one
// self-contained unit instead of a label followed by bare prose).
export type ExerciseStep = { id: string; label: string; text: string }
export type TryItYourselfBlock = {
  id: string
  type: 'try_it_yourself'
  task: string
  material: string
  steps: ExerciseStep[]
  whatToNotice: string
}

export type ContentBlock =
  | HeadingBlock
  | ParagraphBlock
  | CalloutBlock
  | CardGroupBlock
  | QuizBlock
  | QuestionBlock
  | WhitespaceBlock
  | InteractiveBlock
  | TryItYourselfBlock

export type ContentBlockType = ContentBlock['type']
