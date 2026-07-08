import type { ContentBlock } from '../types/contentBlocks'

/**
 * Serialises a content_blocks array to an MDX string for the admin MDX editor.
 *
 * Known limitations (lossy round-trip):
 *  - callout: the `>` prefix is re-added by blocksToMdx, but the original block
 *    text must not already start with `>` or it will be doubled on re-import.
 *  - card_group / quiz: serialised as raw JSON inside <Cards /> / <Quiz /> tags;
 *    any special characters in card/question text are not escaped.
 *  - interactive / try_it_yourself: base64-encoded inside <Interactive /> /
 *    <TryItYourself /> tags so their nested id references (bucketId,
 *    correctOptionId) and free-text prompts survive the round-trip intact.
 *    Not hand-editable as text — author these with the block editor.
 *  - question: has no MDX form — dropped on serialise (matches the old app,
 *    which dropped it too; it carries only a prompt string).
 */
// UTF-8-safe base64: TextEncoder handles multi-byte chars, and base64's
// [A-Za-z0-9+/=] alphabet can't be broken by a quote, backtick or `>` inside
// the content (unlike Cards/Quiz's raw-JSON attribute).
function encodeBlock(block: ContentBlock): string {
  const bytes = new TextEncoder().encode(JSON.stringify(block))
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary)
}

export function blocksToMdx(blocks: ContentBlock[] | null | undefined): string {
  if (!blocks?.length) return ''

  return blocks
    .map((block) => {
      switch (block.type) {
        case 'heading':
          return `${'#'.repeat(block.level)} ${block.text}`

        case 'paragraph':
          return block.text

        case 'callout':
          return block.text
            .split('\n')
            .map((line) => `> ${line}`)
            .join('\n')

        case 'card_group':
          return `<Cards data='${JSON.stringify(block.cards)}' />`

        case 'quiz':
          return `<Quiz data='${JSON.stringify(block.questions)}' />`

        case 'whitespace':
          return `<Spacer size="${block.size ?? 'md'}" />`

        case 'interactive':
          return `<Interactive data="${encodeBlock(block)}" />`

        case 'try_it_yourself':
          return `<TryItYourself data="${encodeBlock(block)}" />`

        case 'question':
          return ''

        default: {
          const exhaustive: never = block
          return exhaustive
        }
      }
    })
    .filter(Boolean)
    .join('\n\n')
}
