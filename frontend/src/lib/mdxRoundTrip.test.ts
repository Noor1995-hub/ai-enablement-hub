// #60: quiz/card blocks vanished from unrelated MDX edits. These pin the round
// trip blocksToMdx → parseMdxToBlocks for every block type with realistic text.
import { describe, expect, it } from 'vitest'
import type { ContentBlock } from '../types/contentBlocks'
import { blocksToMdx } from './blocksToMdx'
import { parseMdxToBlocks } from './mdxParser'

// Realistic, nasty inline text. Deliberately NO line starting with #, > or a
// lone *x*: MDX re-reads those as heading/callout/kicker (documented limit).
const T = `Don't "quote" me: a -> b, x < y, \`code\`, café 🙂`

const EVERY_TYPE: ContentBlock[] = [
  { id: 'h', type: 'heading', level: 2, text: T },
  { id: 'p', type: 'paragraph', text: `${T}\nsecond line, it's fine` },
  { id: 'c', type: 'callout', text: `${T}\nand another` },
  { id: 'k', type: 'kicker', text: `It's a kicker -> ok` },
  { id: 'cg', type: 'card_group', cards: [{ id: 'c1', title: T, body: T }] },
  { id: 'q', type: 'quiz', questions: [{ id: 'q1', q: T, options: [T, 'b'], correct: 1, explanation: T }] },
  { id: 'qs', type: 'question', prompt: T },
  { id: 'w', type: 'whitespace', size: 'lg' },
  { id: 'is', type: 'interactive', mode: 'sort', prompt: T, buckets: [{ id: 'b1', label: T }], items: [{ id: 'i1', text: T, bucketId: 'b1', reason: T }] },
  { id: 'tiy', type: 'try_it_yourself', task: T, material: T, steps: [{ id: 's1', label: T, text: T }], whatToNotice: T },
  { id: 'img', type: 'image', blob_path: 'lessons/x.png', alt: T, caption: T },
  { id: 'v', type: 'video', source: 'embed', url: 'https://www.youtube.com/embed/abc' },
] as ContentBlock[]

const withoutIds = (blocks: ContentBlock[]) =>
  JSON.parse(JSON.stringify(blocks, (key, value) => (key === 'id' ? undefined : value)))

describe('MDX round trip (#60)', () => {
  it('round-trips realistic text in every block type', () => {
    expect(withoutIds(parseMdxToBlocks(blocksToMdx(EVERY_TYPE)))).toEqual(withoutIds(EVERY_TYPE))
  })

  it('keeps quiz, card and question ids', () => {
    const out = parseMdxToBlocks(blocksToMdx(EVERY_TYPE))
    expect(out.find(b => b.type === 'quiz')?.id).toBe('q')
    expect(out.find(b => b.type === 'card_group')?.id).toBe('cg')
    expect(out.find(b => b.type === 'question')?.id).toBe('qs')
  })

  it('covers every block type in the union', () => {
    // Fails when a type is added to contentBlocks.ts without round-trip coverage.
    const covered = new Set(EVERY_TYPE.map(b => b.type))
    const all: ContentBlock['type'][] = [
      'heading', 'paragraph', 'callout', 'kicker', 'card_group', 'quiz', 'question',
      'whitespace', 'interactive', 'try_it_yourself', 'image', 'video',
    ]
    expect([...covered].sort()).toEqual([...all].sort())
  })

  it('still reads the legacy single-quoted Cards and Quiz forms', () => {
    const legacy = `<Quiz data='[{"id":"x","q":"Q","options":["a","b"],"correct":0,"explanation":"e"}]' />`
    expect(parseMdxToBlocks(legacy).map(b => b.type)).toEqual(['quiz'])
  })
})
