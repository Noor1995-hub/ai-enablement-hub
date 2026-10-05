// The lesson editor's save flow (B5): house-style check as a soft gate, then a
// PATCH carrying the base updated_at; a 409 lesson_changed becomes a prompt.
import { useRef, useState } from 'react'
import { client, errorMessage } from '../../api/client'
import type { components } from '../../api/schema'
import { parseConflict, removalSummary, type Finding } from '../../lib/lessonSave'
import type { ContentBlock } from '../../types/contentBlocks'

type LessonOut = components['schemas']['LessonOut']
export interface SavePayload { title?: string; content_blocks: ContentBlock[] }

export type Gate =
  | { kind: 'idle' }
  | { kind: 'busy' }
  | { kind: 'findings'; findings: Finding[]; removal: string | null; checkOnly: boolean; checkError?: string }
  | { kind: 'conflict'; updatedAt: string; updatedByName: string | null }
  | { kind: 'error'; message: string }

interface Options {
  lessonId: string
  baseUpdatedAt: string | null | undefined
  onSaved: (data: LessonOut) => void
  onReload?: () => void
}

export function useGuardedSave({ lessonId, baseUpdatedAt, onSaved, onReload }: Options) {
  const [gate, setGate] = useState<Gate>({ kind: 'idle' })
  const pending = useRef<SavePayload | null>(null)

  async function runCheck(blocks: ContentBlock[]): Promise<{ findings: Finding[] } | { error: string }> {
    try {
      const { data, error } = await client.POST('/api/admin/lessons/{lesson_id}/check', {
        params: { path: { lesson_id: lessonId } },
        body: { content_blocks: blocks },
      })
      return data ? { findings: data.findings } : { error: errorMessage(error, 'The check failed.') }
    } catch {
      return { error: 'The check could not be reached.' }
    }
  }

  async function patch(payload: SavePayload, expected: string | null | undefined) {
    setGate({ kind: 'busy' })
    // openapi-fetch REJECTS on a network failure (offline, reset) instead of
    // resolving with `error`; without this the gate stayed `busy` and Save
    // was disabled until a page reload threw the edits away.
    let result: Awaited<ReturnType<typeof sendPatch>>
    try {
      result = await sendPatch(payload, expected)
    } catch {
      setGate({ kind: 'error', message: 'The save could not be reached. Please try again.' })
      return
    }
    const { data, error } = result
    if (data) {
      pending.current = null
      setGate({ kind: 'idle' })
      onSaved(data)
      return
    }
    const conflict = parseConflict(error)
    setGate(conflict ? { kind: 'conflict', ...conflict } : { kind: 'error', message: errorMessage(error, 'Failed to save.') })
  }

  function sendPatch(payload: SavePayload, expected: string | null | undefined) {
    return client.PATCH('/api/admin/lessons/{lesson_id}', {
      params: { path: { lesson_id: lessonId } },
      body: {
        ...payload,
        ...(expected ? { expected_updated_at: expected } : {}),
      },
    })
  }

  async function save(payload: SavePayload, opts: { before?: ContentBlock[] } = {}) {
    pending.current = payload
    setGate({ kind: 'busy' })
    const result = await runCheck(payload.content_blocks)
    const removal = opts.before ? removalSummary(opts.before, payload.content_blocks) : null
    // The checks are a soft gate: a check that fails to run must not block
    // the save, it only says so and leaves the choice to the admin.
    if ('error' in result) {
      setGate({ kind: 'findings', findings: [], removal, checkOnly: false, checkError: result.error })
      return
    }
    const { findings } = result
    if (removal || findings.some(f => f.severity === 'warning')) {
      setGate({ kind: 'findings', findings, removal, checkOnly: false })
      return
    }
    await patch(payload, baseUpdatedAt)
  }

  async function check(blocks: ContentBlock[]) {
    setGate({ kind: 'busy' })
    const result = await runCheck(blocks)
    setGate('error' in result
      ? { kind: 'error', message: result.error }
      : { kind: 'findings', findings: result.findings, removal: null, checkOnly: true })
  }

  return {
    gate,
    save,
    check,
    // The panels sit inline, so the admin may keep editing while one is open:
    // the host passes what is on screen NOW, never the snapshot from Save.
    saveAnyway: (current?: SavePayload) => {
      const payload = current ?? pending.current
      if (payload) void patch(payload, baseUpdatedAt)
    },
    keepEditing: () => { pending.current = null; setGate({ kind: 'idle' }) },
    overwrite: (current?: SavePayload) => {
      const payload = current ?? pending.current
      if (payload && gate.kind === 'conflict') void patch(payload, gate.updatedAt)
    },
    reload: () => { pending.current = null; setGate({ kind: 'idle' }); onReload?.() },
  }
}
