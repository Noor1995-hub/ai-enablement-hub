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

interface ProposalDiffProps {
  base: unknown[]
  proposed: unknown[]
}

export default function ProposalDiff({ base, proposed }: ProposalDiffProps) {
  const entries = diffBlocks(base, proposed)
  const changes = entries.filter(entry => entry.kind !== 'unchanged').length

  return (
    <div className="adm-ci-sbs">
      <p className="adm-subtext">
        {entries.length} block{entries.length === 1 ? '' : 's'} · {changes} change{changes === 1 ? '' : 's'}
      </p>
      <div className="adm-ci-sbs-head">
        <span>Current lesson</span>
        <span>Proposed draft</span>
      </div>
      {entries.map(entry => (
        <div key={entry.key} className={`adm-ci-sbs-row adm-ci-sbs-${entry.kind}`}>
          <DiffCell block={entry.before} kind={entry.kind} side="before" />
          <DiffCell block={entry.after} kind={entry.kind} side="after" />
        </div>
      ))}
    </div>
  )
}

interface DiffCellProps {
  block: Block | null
  kind: DiffKind
  side: 'before' | 'after'
}

/** One side of one aligned row. An absent block on either side is what makes an
 * addition or a removal read at a glance, so it renders an explicit marker
 * rather than an empty cell. A block whose `type` changed shows the old type on
 * the left and the new one on the right, so the retype is visible without any
 * special casing — which is why the old single-cell `typeLabel` is gone. */
function DiffCell({ block, kind, side }: DiffCellProps) {
  if (block === null) {
    return (
      <div className="adm-ci-sbs-cell adm-ci-sbs-cell-empty">
        <span className="adm-ci-block-kind">{side === 'before' ? 'added' : 'removed'}</span>
      </div>
    )
  }
  return (
    <div className="adm-ci-sbs-cell">
      <div className="adm-ci-block-head">
        <span className="adm-ci-block-type">{blockType(block)}</span>
        {kind !== 'unchanged' && side === 'after' && (
          <span className="adm-ci-block-kind">{kind}</span>
        )}
      </div>
      <p className="adm-ci-block-text">{readable(block)}</p>
    </div>
  )
}

function readable(block: Block | null): string {
  if (block === null) return '(unreadable block)'
  const text = blockText(block)
  return text || '(no text in this block)'
}
