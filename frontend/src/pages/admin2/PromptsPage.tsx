import { useState } from 'react'
import type { PromptSummary } from '../../types/domain'
import { useHealth, usePrompt, usePrompts } from './api'
import { Card, EmptyState, ErrorState, Spinner } from './kit'

const REPO = 'https://github.com/DLW-INT-BTA-BELUX/ai-enablement-hub'

/** System prompts (`/admin/prompts`) — READ-ONLY since 2026-09-23: git
 * (`backend/prompts/*.md`) is the only source of truth for prompt text, and
 * the admin PUT/DELETE editor this page used to host is gone (Task 5 of the
 * 2026-09-23 git-only-prompts rewrite; backend Task 1 removed the write
 * routes, which now 405). Not project-scoped — one page, local selection
 * state, no child route, same family as Content AI/calibration notes rather
 * than TemplatesPage's project-scoped shape (there is nothing here to scope
 * a prompt by). Master–detail layout: the grouped list on the left, the
 * selected `kind`'s raw content in the right pane beside it. Row click
 * selects a `kind`; until then (or if the selection somehow doesn't match a
 * loaded prompt) it falls back to the first group's first row, so the right
 * pane is never empty. */
export default function PromptsPage() {
  const promptsQuery = usePrompts()
  const [selectedKind, setSelectedKind] = useState<string | null>(null)

  if (promptsQuery.isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (promptsQuery.isError || !promptsQuery.data) {
    return (
      <ErrorState
        message={promptsQuery.error?.message ?? 'Failed to load prompts.'}
        onRetry={() => void promptsQuery.refetch()}
      />
    )
  }

  const groups = groupByGroup(promptsQuery.data)
  // Auto-select the first group's first row until the admin picks one.
  const firstKind = groups[0]?.[1]?.[0]?.kind ?? null
  const effectiveKind = selectedKind ?? firstKind
  const selected = promptsQuery.data.find(p => p.kind === effectiveKind) ?? null

  return (
    <div>
      <h1 className="adm-page-title">System prompts</h1>
      <p className="adm-page-sub">
        The prompt text behind each agent surface. Git is the source of truth for every prompt —
        change it with a pull request, then deploy.
      </p>

      {promptsQuery.data.length === 0 ? (
        <EmptyState title="No prompts configured." />
      ) : (
        <div className="adm-prompts-layout">
          <div className="adm-prompts-list">
            {groups.map(([groupName, items]) => (
              <Card key={groupName} title={groupName}>
                <div className="adm-comp-list">
                  {items.map(item => (
                    <PromptRow
                      key={item.kind}
                      item={item}
                      selected={item.kind === effectiveKind}
                      onSelect={() => setSelectedKind(item.kind)}
                    />
                  ))}
                </div>
              </Card>
            ))}
          </div>

          <div className="adm-prompts-detail">
            {/* Keyed by kind: switching prompts remounts the viewer so it always
                shows the newly selected prompt's content rather than a stale one. */}
            {selected && <PromptViewer key={selected.kind} kind={selected.kind} label={selected.label} />}
          </div>
        </div>
      )}
    </div>
  )
}

/** Stable-order grouping — the list already arrives grouped (backend orders
 * by kind registration), so this only folds repeated group names together
 * without re-sorting; a group not yet seen is appended in the order it first
 * appears. */
function groupByGroup(prompts: PromptSummary[]): [string, PromptSummary[]][] {
  const order: string[] = []
  const byGroup = new Map<string, PromptSummary[]>()
  for (const prompt of prompts) {
    if (!byGroup.has(prompt.group)) {
      order.push(prompt.group)
      byGroup.set(prompt.group, [])
    }
    byGroup.get(prompt.group)!.push(prompt)
  }
  return order.map(name => [name, byGroup.get(name) ?? []])
}

interface PromptRowProps {
  item: PromptSummary
  selected: boolean
  onSelect: () => void
}

function PromptRow({ item, selected, onSelect }: PromptRowProps) {
  return (
    <button
      type="button"
      className={`adm-prompt-row${selected ? ' selected' : ''}`}
      onClick={onSelect}
    >
      <span className="adm-comp-name">{item.label}</span>
    </button>
  )
}

interface PromptViewerProps {
  kind: string
  label: string
}

/** The selected prompt's read-only content. Mounted with `key={kind}` at the
 * call site (PromptsPage above), so switching prompts unmounts/remounts this
 * whole component rather than patching stale state in place. `liveUrl` points
 * at the exact deployed commit when known (`useHealth`'s `build_sha`, the
 * same hook SetupPage's Deployment card reads — no separate fetch here) and
 * falls back to `main` locally, where health reports the sentinel `"dev"`. */
function PromptViewer({ kind, label }: PromptViewerProps) {
  const promptQuery = usePrompt(kind)
  const healthQuery = useHealth()

  if (promptQuery.isLoading) {
    return (
      <Card title={label}>
        <div className="adm-loading">
          <Spinner />
        </div>
      </Card>
    )
  }

  if (promptQuery.isError || !promptQuery.data) {
    return (
      <Card title={label}>
        <ErrorState
          message={promptQuery.error?.message ?? 'Failed to load the prompt.'}
          onRetry={() => void promptQuery.refetch()}
        />
      </Card>
    )
  }

  const data = promptQuery.data
  const sha = healthQuery.data?.build_sha
  const liveUrl =
    sha && sha !== 'dev' ? `${REPO}/blob/${sha}/${data.path}` : `${REPO}/blob/main/${data.path}`

  return (
    <Card title={label}>
      <pre className="adm-prompt-text">{data.content}</pre>
      <p className="adm-muted">
        Source of truth: <code>{data.path}</code> in git. Change it with a pull request, then deploy.{' '}
        <a href={liveUrl} target="_blank" rel="noreferrer">View live version</a>{' · '}
        <a href={`${REPO}/edit/main/${data.path}`} target="_blank" rel="noreferrer">Edit on GitHub</a>
      </p>
    </Card>
  )
}
