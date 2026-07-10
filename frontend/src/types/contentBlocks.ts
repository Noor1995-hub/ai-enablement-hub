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

// Image / video media blocks. `url` is EPHEMERAL: the backend stamps a fresh
// SAS `url` onto image and blob-sourced video blocks at read time and strips it
// again on write, so `blob_path` is the only persisted locator for uploads. An
// embed video carries no blob — its `url` is a normalized provider embed URL and
// IS persisted data. One `video` type with a `source` discriminator (precedent:
// interactive.mode); embed↔upload is an editor toggle, not two block types.
export type ImageBlock = {
  id: string
  type: 'image'
  blob_path: string          // ONLY persisted locator, e.g. "images/6f0c….png"
  alt: string
  caption?: string
  width?: number             // % of content column, 25–100; absent = 100
  url?: string               // EPHEMERAL — backend-stamped SAS, stripped on write
}

export type VideoBlock = { id: string; type: 'video'; caption?: string } & (
  | { source: 'embed'; url: string }                     // persisted embed URL
  | { source: 'blob'; blob_path: string; url?: string }  // url EPHEMERAL
)

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
  | ImageBlock
  | VideoBlock

export type ContentBlockType = ContentBlock['type']
