import { useEffect, useState } from 'react'
import { formatDate } from '../admin/adminHelpers'
import type { PromptSummary } from '../../types/domain'
import { usePrompt, usePrompts, useResetPrompt, useUpdatePrompt } from './api'
import { Card, Chip, EmptyState, ErrorState, Spinner } from './kit'
import type { ChipTone } from './kit'

/** System prompts (`/admin/prompts`) — the prompt text driving each agent
 * surface (interviewer, chat, content generation), editable per `kind` and
 * stored in the DB; falls back to the shipped file default until an admin
 * saves an override here. Not project-scoped — one page, local selection
 * state, no child route, same family as Content AI/calibration notes rather
 * than TemplatesPage's project-scoped shape (there is nothing here to scope
 * a prompt by). Row click selects a `kind`; the editor below is keyed by
 * that kind so switching prompts (or a successful save/reset) always shows
 * the right content — see PromptEditor's doc comment. */
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
  const selected = promptsQuery.data.find(p => p.kind === selectedKind) ?? null

  return (
    <div>
      <h1 className="adm-page-title">System prompts</h1>
      <p className="adm-page-sub">
        The prompt text behind each agent surface. Saving here overrides the shipped default for
        everyone, immediately — there is no project scope.
      </p>

      {promptsQuery.data.length === 0 ? (
        <EmptyState title="No prompts configured." />
      ) : (
        groups.map(([groupName, items]) => (
          <Card key={groupName} title={groupName}>
            <div className="adm-comp-list">
              {items.map(item => (
                <PromptRow
                  key={item.kind}
                  item={item}
                  selected={item.kind === selectedKind}
                  onSelect={() => setSelectedKind(item.kind)}
                />
              ))}
            </div>
          </Card>
        ))
      )}

      {/* Keyed by kind: switching prompts remounts the editor so its local
          `content` state starts fresh rather than patching a stale value. */}
      {selected && <PromptEditor key={selected.kind} kind={selected.kind} label={selected.label} />}
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

/** "Edited" (DB override in effect) vs "Default" (still the shipped file) —
 * always paired with the word itself, never color-only (same rule the kit's
 * own Chip doc states). */
function sourceTone(source: string): ChipTone {
  return source === 'db' ? 'warn' : 'default'
}

function sourceLabel(source: string): string {
  return source === 'db' ? 'Edited' : 'Default'
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
      <Chip tone={sourceTone(item.source)}>{sourceLabel(item.source)}</Chip>
      {item.updated_at && (
        <span className="adm-subtext adm-push-right">Last edited {formatDate(item.updated_at)}</span>
      )}
    </button>
  )
}

interface PromptEditorProps {
  kind: string
  label: string
}

/** The selected prompt's editor. Mounted with `key={kind}` at the call site
 * (PromptsPage above), so switching prompts unmounts/remounts this whole
 * component — `content` always starts from a clean slate rather than a stale
 * previous prompt's text. Same kind, post-save/reset: the effect below
 * reseeds `content` from `promptQuery.data` — TanStack Query's structural
 * sharing keeps that reference stable while the admin is mid-edit (an
 * unrelated background refetch that returns identical data won't re-trigger
 * this), and changes it exactly when the invalidation this mutation
 * triggers brings back new content, which is what we want to reflect. */
function PromptEditor({ kind, label }: PromptEditorProps) {
  const promptQuery = usePrompt(kind)
  const updatePrompt = useUpdatePrompt()
  const resetPrompt = useResetPrompt()
  const [content, setContent] = useState('')

  useEffect(() => {
    if (promptQuery.data) setContent(promptQuery.data.content)
  }, [promptQuery.data])

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
  const dirty = content !== data.content
  const missingTokens = data.required_tokens.filter(token => !content.includes(`{{${token}}}`))
  const canSave = dirty && content.trim() !== '' && missingTokens.length === 0
  const busy = updatePrompt.isPending || resetPrompt.isPending

  function handleSave() {
    if (!window.confirm(`This changes the live "${label}" prompt for everyone, immediately. Save?`)) return
    updatePrompt.mutate({ kind, content })
  }

  function handleReset() {
    if (
      !window.confirm(
        `This discards the edited "${label}" prompt and restores the shipped default for everyone. Reset?`,
      )
    )
      return
    resetPrompt.mutate(kind)
  }

  return (
    <Card title={label} actions={<Chip tone={sourceTone(data.source)}>{sourceLabel(data.source)}</Chip>}>
      {data.required_tokens.length > 0 && (
        <p className="adm-hint">
          Required — the save is rejected if any of these are missing:{' '}
          {data.required_tokens.map(token => (
            <code key={token} className="adm-prompt-token">{`{{${token}}}`}</code>
          ))}
        </p>
      )}

      <textarea
        className="adm-prompt-textarea"
        value={content}
        onChange={e => setContent(e.target.value)}
        spellCheck
        rows={16}
      />

      {missingTokens.length > 0 && (
        <p className="adm-form-msg adm-form-msg-err">
          Missing required token{missingTokens.length === 1 ? '' : 's'}:{' '}
          {missingTokens.map(token => `{{${token}}}`).join(', ')}
        </p>
      )}

      <div className="adm-form-actions">
        <button
          type="button"
          className="adm-btn adm-btn-primary"
          disabled={!canSave || busy}
          onClick={handleSave}
        >
          {updatePrompt.isPending ? 'Saving…' : 'Save'}
        </button>
        {data.source === 'db' && (
          <button
            type="button"
            className="adm-btn adm-btn-ghost"
            disabled={busy}
            onClick={handleReset}
          >
            {resetPrompt.isPending ? 'Resetting…' : 'Reset to default'}
          </button>
        )}
        {data.updated_at && <span className="adm-subtext">Last edited {formatDate(data.updated_at)}</span>}
      </div>

      {updatePrompt.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {updatePrompt.error instanceof Error ? updatePrompt.error.message : 'Failed to save the prompt.'}
        </p>
      )}
      {resetPrompt.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {resetPrompt.error instanceof Error ? resetPrompt.error.message : 'Failed to reset the prompt.'}
        </p>
      )}
    </Card>
  )
}
