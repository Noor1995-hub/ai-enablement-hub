import type {
  CalloutBlock,
  Card,
  CardGroupBlock,
  ContentBlock,
  HeadingBlock,
  ParagraphBlock,
  QuestionBlock,
  QuizBlock,
  QuizQuestion,
  WhitespaceBlock,
} from '../types/contentBlocks'

export const BLOCK_TYPES = {
  HEADING: 'heading',
  PARAGRAPH: 'paragraph',
  CALLOUT: 'callout',
  CARD_GROUP: 'card_group',
  QUIZ: 'quiz',
  QUESTION: 'question',
  WHITESPACE: 'whitespace',
} as const

export const BLOCK_LABELS: Record<ContentBlock['type'], string> = {
  heading: 'Heading',
  paragraph: 'Text',
  callout: 'Callout',
  card_group: 'Cards',
  quiz: 'Quiz',
  question: 'Question',
  whitespace: 'Whitespace',
}

export function createHeading(level: HeadingBlock['level'] = 2, text = ''): HeadingBlock {
  return { id: crypto.randomUUID(), type: BLOCK_TYPES.HEADING, level, text }
}

export function createParagraph(text = ''): ParagraphBlock {
  return { id: crypto.randomUUID(), type: BLOCK_TYPES.PARAGRAPH, text }
}

export function createCallout(text = ''): CalloutBlock {
  return { id: crypto.randomUUID(), type: BLOCK_TYPES.CALLOUT, text }
}

// Incoming cards/questions (MDX import, DB JSONB) may lack ids.
type CardInput = Omit<Card, 'id'> & { id?: string }
type QuizQuestionInput = Omit<QuizQuestion, 'id'> & { id?: string }

export function createCardGroup(cards: CardInput[] = []): CardGroupBlock {
  const normalised: Card[] = cards.length
    ? cards.map((c) => (c.id ? (c as Card) : { id: crypto.randomUUID(), ...c }))
    : [{ id: crypto.randomUUID(), title: '', body: '' }]
  return { id: crypto.randomUUID(), type: BLOCK_TYPES.CARD_GROUP, cards: normalised }
}

export function createQuiz(questions: QuizQuestionInput[] = []): QuizBlock {
  const normalised: QuizQuestion[] = questions.length
    ? questions.map((q) => (q.id ? (q as QuizQuestion) : { id: crypto.randomUUID(), ...q }))
    : [{ id: crypto.randomUUID(), q: '', options: ['', '', ''], correct: 0, explanation: '' }]
  return { id: crypto.randomUUID(), type: BLOCK_TYPES.QUIZ, questions: normalised }
}

export function createWhitespace(size: WhitespaceBlock['size'] = 'md'): WhitespaceBlock {
  return { id: crypto.randomUUID(), type: BLOCK_TYPES.WHITESPACE, size }
}

export function createQuestion(prompt = ''): QuestionBlock {
  return { id: crypto.randomUUID(), type: BLOCK_TYPES.QUESTION, prompt }
}

export const BLOCK_FACTORIES: Record<ContentBlock['type'], () => ContentBlock> = {
  [BLOCK_TYPES.HEADING]: () => createHeading(),
  [BLOCK_TYPES.PARAGRAPH]: () => createParagraph(),
  [BLOCK_TYPES.CALLOUT]: () => createCallout(),
  [BLOCK_TYPES.CARD_GROUP]: () => createCardGroup(),
  [BLOCK_TYPES.QUIZ]: () => createQuiz(),
  [BLOCK_TYPES.QUESTION]: () => createQuestion(),
  [BLOCK_TYPES.WHITESPACE]: () => createWhitespace(),
}
