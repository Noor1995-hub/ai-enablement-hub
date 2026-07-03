import type { ContentBlock } from '../types/contentBlocks'

/**
 * Serialises a content_blocks array to an MDX string for the admin MDX editor.
 *
 * Known limitations (lossy round-trip):
 *  - callout: the `>` prefix is re-added by blocksToMdx, but the original block
 *    text must not already start with `>` or it will be doubled on re-import.
 *  - card_group / quiz: serialised as raw JSON inside <Cards /> / <Quiz /> tags;
 *    any special characters in card/question text are not escaped.
 *  - question: has no MDX form (matches the old app, which dropped it too).
 */
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
