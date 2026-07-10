import type { ContentBlock, ImageBlock, InteractiveBlock, TryItYourselfBlock, VideoBlock } from '../types/contentBlocks'
import {
  createCallout,
  createCardGroup,
  createHeading,
  createParagraph,
  createQuiz,
  createWhitespace,
} from './contentBlocks'

// Inverse of blocksToMdx's encodeBlock: base64 → the original block verbatim
// (top-level and nested ids preserved, so bucketId/correctOptionId references
// still resolve after the round-trip).
function decodeBlock<T>(data: string): T {
  const binary = atob(data)
  const bytes = Uint8Array.from(binary, (ch) => ch.charCodeAt(0))
  return JSON.parse(new TextDecoder().decode(bytes)) as T
}

/**
 * Parses a raw MDX string into a content_blocks array compatible with the lesson editor.
 *
 * Handles:
 *   - <Cards data='[...]' />  or  <Cards data={`[...]`} />
 *   - <Quiz data='[...]' />   or  <Quiz data={`[...]`} />
 *   - <Spacer size="sm|md|lg" />
 *   - <Interactive data="<base64>" /> and <TryItYourself data="<base64>" />
 *   - Markdown headings (# / ## / ###)
 *   - Blockquotes (> text)
 *   - Plain paragraphs
 */
export function parseMdxToBlocks(mdx: string): ContentBlock[] {
  if (!mdx || !mdx.trim()) return []

  const blocks: ContentBlock[] = []

  // Split on self-closing component tags (base64 payloads contain no `>`, so
  // the [^>] tag matcher stays intact for Interactive/TryItYourself too)
  const segments = mdx.split(/(<(?:Cards|Quiz|Spacer|Interactive|TryItYourself|Image|Video)\s[^>]*?\/>)/g)

  for (const seg of segments) {
    const cardsMatch = seg.match(/^<Cards\s+data='([^']*)'/)
      ?? seg.match(/^<Cards\s+data=\{`([^`]*)`\}/)
    const quizMatch = seg.match(/^<Quiz\s+data='([^']*)'/)
      ?? seg.match(/^<Quiz\s+data=\{`([^`]*)`\}/)

    if (cardsMatch) {
      try {
        const cards = JSON.parse(cardsMatch[1])
        blocks.push(createCardGroup(cards))
      } catch {
        // malformed JSON — skip
      }
      continue
    }

    if (quizMatch) {
      try {
        const questions = JSON.parse(quizMatch[1])
        blocks.push(createQuiz(questions))
      } catch {
        // malformed JSON — skip
      }
      continue
    }

    const spacerMatch = seg.match(/^<Spacer\s+size="(sm|md|lg)"/)
    if (spacerMatch) {
      blocks.push(createWhitespace(spacerMatch[1] as 'sm' | 'md' | 'lg'))
      continue
    }

    const interactiveMatch = seg.match(/^<Interactive\s+data="([^"]*)"/)
    if (interactiveMatch) {
      try {
        blocks.push(decodeBlock<InteractiveBlock>(interactiveMatch[1]))
      } catch {
        // malformed payload — skip
      }
      continue
    }

    const tryItMatch = seg.match(/^<TryItYourself\s+data="([^"]*)"/)
    if (tryItMatch) {
      try {
        blocks.push(decodeBlock<TryItYourselfBlock>(tryItMatch[1]))
      } catch {
        // malformed payload — skip
      }
      continue
    }

    const imageMatch = seg.match(/^<Image\s+data="([^"]*)"/)
    if (imageMatch) {
      try {
        // No ephemeral `url` in the payload (stripped on serialise); the backend
        // re-stamps a SAS on the next read.
        blocks.push(decodeBlock<ImageBlock>(imageMatch[1]))
      } catch {
        // malformed payload — skip
      }
      continue
    }

    const videoMatch = seg.match(/^<Video\s+data="([^"]*)"/)
    if (videoMatch) {
      try {
        blocks.push(decodeBlock<VideoBlock>(videoMatch[1]))
      } catch {
        // malformed payload — skip
      }
      continue
    }

    // Plain markdown segment — parse line by line
    const lines = seg.split('\n')
    let paragraphLines: string[] = []

    function flushParagraph() {
      const text = paragraphLines.join('\n').trim()
      if (text) blocks.push(createParagraph(text))
      paragraphLines = []
    }

    for (const line of lines) {
      const h3 = line.match(/^###\s+(.+)/)
      const h2 = line.match(/^##\s+(.+)/)
      const h1 = line.match(/^#\s+(.+)/)
      const bq = line.match(/^>\s*(.*)/)

      if (h1 || h2 || h3) {
        flushParagraph()
        const level = h3 ? 3 : h2 ? 2 : 1
        const text = (h3 ?? h2 ?? h1)![1].trim()
        blocks.push(createHeading(level, text))
      } else if (bq) {
        flushParagraph()
        blocks.push(createCallout(bq[1].trim()))
      } else {
        paragraphLines.push(line)
      }
    }

    flushParagraph()
  }

  return blocks.filter((b) => {
    if (b.type === 'paragraph') return b.text.trim().length > 0
    if (b.type === 'heading') return b.text.trim().length > 0
    if (b.type === 'callout') return b.text.trim().length > 0
    return true
  })
}
