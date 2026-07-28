// A readable per-block diff of a lesson's content_blocks: old vs. new, matched
// on block id. Deliberately TEXTUAL, not a rendered preview — this is agent
// output and an admin is deciding whether to publish it, so every string here
// goes through a plain JSX text node. No dangerouslySetInnerHTML, no markdown.
//
// content_blocks crosses the JSONB boundary as `unknown[]`, so everything below
// is defensive: a malformed entry degrades to "(unreadable block)" rather than
// throwing inside the review UI.

type Block = Record<string, unknown>

export type DiffKind = 'unchanged' | 'changed' | 'added' | 'removed'

export interface DiffEntry {
  key: string
  kind: DiffKind
  before: Block | null
  after: Block | null
}

function asBlocks(value: unknown[]): Block[] {
  return value.filter((b): b is Block => typeof b === 'object' && b !== null && !Array.isArray(b))
}

function blockId(block: Block): string | null {
  return typeof block.id === 'string' && block.id ? block.id : null
}

function blockType(block: Block): string {
  return typeof block.type === 'string' && block.type ? block.type : 'unknown'
}

/** Every human-readable string in a block, flattened. Field names mirror
 * frontend/src/types/contentBlocks.ts; anything unrecognised is simply not
 * shown (the block's `type` still is, so a change is never invisible). */
function blockText(block: Block): string {
  const parts: string[] = []
  const push = (value: unknown) => {
    if (typeof value === 'string' && value.trim()) parts.push(value.trim())
  }
  // Surfaced explicitly: these are non-string correctness fields that `blockText`
  // would otherwise never read. A block that differs ONLY in one of them (e.g.
  // which quiz option is graded correct) would render byte-identical before/after
  // text under a "changed" badge — indistinguishable from the accepted key-reorder
  // false positive — and an admin could approve a flipped answer without ever
  // seeing it change.
  if (typeof block.level === 'number') push(`heading level ${block.level}`)
  if (typeof block.width === 'number') push(`width ${block.width}%`)
  if (typeof block.correctOptionId === 'string' && block.correctOptionId) {
    push(`correct option: ${block.correctOptionId}`)
  }
  for (const key of [
    'text', 'prompt', 'task', 'material', 'whatToNotice', 'example',
    'alt', 'caption', 'blob_path', 'url', 'size',
  ]) {
    push(block[key])
  }
  for (const key of ['cards', 'questions', 'steps', 'items', 'options', 'buckets', 'candidates']) {
    const children = block[key]
    if (!Array.isArray(children)) continue
    for (const child of children) {
      if (typeof child === 'string') {
        push(child)
        continue
      }
      if (typeof child !== 'object' || child === null) continue
      const record = child as Block
      for (const childKey of ['title', 'body', 'q', 'explanation', 'label', 'text', 'reason']) {
        push(record[childKey])
      }
      if (Array.isArray(record.options)) record.options.forEach(push)
      if (typeof record.correct === 'number') {
        const options = Array.isArray(record.options) ? record.options : []
        const chosen = options[record.correct]
        const answer = typeof chosen === 'string' && chosen.trim() ? chosen.trim() : `#${record.correct}`
        push(`correct answer: ${answer}`)
      }
      if (typeof record.bucketId === 'string' && record.bucketId) push(`bucket: ${record.bucketId}`)
      if (typeof record.isFlaw === 'boolean') push(record.isFlaw ? 'is a flaw' : 'not a flaw')
    }
  }
  return parts.join(' · ')
}

/** Match proposed blocks to base blocks by `id` (which is why the agent is told
 * to reuse ids for edits — otherwise every edit reads as a delete plus an add).
 * Proposed order wins; base blocks with no surviving id are appended as removals.
 *
 * Equality is a JSON.stringify comparison, so a block whose keys were merely
 * reordered shows as "changed". That is a false positive an admin can see
 * through in the text, and it never hides a real change. */
export function diffBlocks(base: unknown[], proposed: unknown[]): DiffEntry[] {
  const baseBlocks = asBlocks(base)
  const proposedBlocks = asBlocks(proposed)
  const baseById = new Map<string, Block>()
  for (const block of baseBlocks) {
    const id = blockId(block)
    if (id) baseById.set(id, block)
  }

  const matched = new Set<string>()
  const entries: DiffEntry[] = proposedBlocks.map((block, index) => {
    const id = blockId(block)
    const before = id ? (baseById.get(id) ?? null) : null
    if (id && before) matched.add(id)
    const kind: DiffKind =
      before === null ? 'added' : JSON.stringify(before) === JSON.stringify(block) ? 'unchanged' : 'changed'
    return { key: id ?? `added-${index}`, kind, before, after: block }
  })

  baseBlocks.forEach((block, index) => {
    const id = blockId(block)
    if (id && matched.has(id)) return
    entries.push({ key: `removed-${id ?? index}`, kind: 'removed', before: block, after: null })
  })

  return entries
}

const KIND_LABEL: Record<DiffKind, string> = {
  unchanged: 'unchanged',
  changed: 'changed',
  added: 'added',
  removed: 'removed',
}

interface ProposalDiffProps {
  base: unknown[]
  proposed: unknown[]
}

export default function ProposalDiff({ base, proposed }: ProposalDiffProps) {
  const entries = diffBlocks(base, proposed)
  const changes = entries.filter(entry => entry.kind !== 'unchanged').length

  return (
    <div className="adm-ci-diff">
      <p className="adm-subtext">
        {entries.length} block{entries.length === 1 ? '' : 's'} · {changes} change{changes === 1 ? '' : 's'}
      </p>
      {entries.map(entry => (
        <div key={entry.key} className={`adm-ci-block adm-ci-block-${entry.kind}`}>
          <div className="adm-ci-block-head">
            <span className="adm-ci-block-kind">{KIND_LABEL[entry.kind]}</span>
            <span className="adm-ci-block-type">{typeLabel(entry)}</span>
          </div>
          {entry.kind === 'changed' ? (
            <>
              <p className="adm-ci-block-text adm-ci-block-before">{readable(entry.before)}</p>
              <p className="adm-ci-block-text adm-ci-block-after">{readable(entry.after)}</p>
            </>
          ) : (
            <p className="adm-ci-block-text">{readable(entry.after ?? entry.before)}</p>
          )}
        </div>
      ))}
    </div>
  )
}

/** The type shown on a diff row's header. A RETYPE — `paragraph` → `callout`
 * with the same text — changes how the block renders for the learner but
 * leaves the two text lines identical, so showing only the new type makes it
 * indistinguishable from the accepted key-reorder false positive. Show both
 * sides when a `changed` entry's types differ. */
function typeLabel(entry: DiffEntry): string {
  const before = entry.before ? blockType(entry.before) : null
  const after = entry.after ? blockType(entry.after) : null
  if (entry.kind === 'changed' && before && after && before !== after) {
    return `${before} → ${after}`
  }
  return after ?? before ?? 'unknown'
}

function readable(block: Block | null): string {
  if (block === null) return '(unreadable block)'
  const text = blockText(block)
  return text || '(no text in this block)'
}
