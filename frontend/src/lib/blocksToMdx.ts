import type { ContentBlock } from '../types/contentBlocks'

/**
 * Serialises a content_blocks array to an MDX string for the admin MDX editor.
 *
 * Known limitations (lossy round-trip):
 *  - callout: the `>` prefix is re-added by blocksToMdx, but the original block
 *    text must not already start with `>` or it will be doubled on re-import.
 *  - kicker: serialised as a bare `*text*` line; the block's own text must not
 *    already be wrapped in a single pair of asterisks, and must stay on one
 *    line, or it will misparse on re-import.
 *  - a paragraph or callout LINE starting with `#`, `>` or a lone `*…*`
 *    re-parses as a heading, callout or kicker — inherent to MDX. The editor
 *    warns before a save that would remove blocks (B5, lib/lessonSave.ts).
 *  - card_group / quiz / question / interactive / try_it_yourself:
 *    base64-encoded inside <Cards /> / <Quiz /> / <Question /> / <Interactive /> /
 *    <TryItYourself /> tags (#60: card_group and quiz used raw JSON in single
 *    quotes, truncated by the first apostrophe; question was dropped) so their nested id references (bucketId,
 *    correctOptionId) and free-text prompts survive the round-trip intact.
 *    Not hand-editable as text — author these with the block editor.
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

        case 'kicker':
          return `*${block.text}*`

        // Base64 like Interactive (#60): the old raw-JSON-in-single-quotes form
        // was truncated by the first apostrophe in any card or question text.
        case 'card_group':
          return `<Cards data="${encodeBlock(block)}" />`

        case 'quiz':
          return `<Quiz data="${encodeBlock(block)}" />`

        case 'whitespace':
          return `<Spacer size="${block.size ?? 'md'}" />`

        case 'interactive':
          return `<Interactive data="${encodeBlock(block)}" />`

        case 'try_it_yourself':
          return `<TryItYourself data="${encodeBlock(block)}" />`

        // Strip the ephemeral SAS `url` before encoding — it's re-stamped on read
        // and must never be persisted. (encodeBlock → JSON.stringify drops the
        // `url: undefined` key.) blob_path is the only persisted image locator.
        case 'image':
          return `<Image data="${encodeBlock({ ...block, url: undefined })}" />`

        // Same for a blob-sourced video; an embed video's `url` IS persisted data
        // (the normalized provider embed URL) so it is kept as-is.
        case 'video':
          return block.source === 'blob'
            ? `<Video data="${encodeBlock({ ...block, url: undefined })}" />`
            : `<Video data="${encodeBlock(block)}" />`

        case 'question':
          return `<Question data="${encodeBlock(block)}" />`

        default: {
          const exhaustive: never = block
          return exhaustive
        }
      }
    })
    .filter(Boolean)
    .join('\n\n')
}
