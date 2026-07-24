// frontend/src/pages/DevChat.tsx
//
// TEMPORARY Batch A verification harness for the AI chat foundation. This
// whole page — including the AI-enable/disable control at the top — is a
// throwaway dev tool: it exists only so the chatbot surface can be flipped on
// and chatted with in one place, without touching the real admin panel (a
// colleague is editing Admin.tsx / ProjectDetailView.tsx on a concurrent
// branch, and Batch B's real admin AI-toggle UI belongs there, not here).
// Delete this file (and its /dev-chat route in App.tsx) once Batch B mounts
// ChatPanel for real (floating icon / assessment / lesson mounts) and the
// admin panel grows its own AI-enable controls.
import { useState } from 'react'
import { client, errorMessage } from '../api/client'
import ChatPanel from '../components/ChatPanel'
import { type ChatKind } from '../lib/useChat'

const KINDS: ChatKind[] = ['chatbot', 'assessment', 'lesson', 'interview']

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export default function DevChat() {
  const [projectId, setProjectId] = useState('')
  const [settings, setSettings] = useState<Record<string, { enabled: boolean }> | null>(null)
  const [loadedProjectId, setLoadedProjectId] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [togglingKind, setTogglingKind] = useState<ChatKind | null>(null)
  const [toggleMessage, setToggleMessage] = useState<string | null>(null)
  const [toggleIsError, setToggleIsError] = useState(false)

  const trimmedId = projectId.trim()
  const validId = UUID_RE.test(trimmedId)
  // The displayed `settings` were fetched for `loadedProjectId`, which can go
  // stale the moment the input is edited without re-clicking "Load state".
  // Toggling against a mismatched id would write to the wrong project, so the
  // toggle buttons stay disabled until the id in the box matches what's shown.
  const idMismatch = settings !== null && trimmedId !== loadedProjectId

  const loadState = async () => {
    if (!UUID_RE.test(trimmedId)) {
      setLoadError('Enter a valid project id (UUID) first.')
      setSettings(null)
      setLoadedProjectId(null)
      return
    }
    setLoading(true)
    setLoadError(null)
    try {
      const { data, error } = await client.GET('/api/admin/projects/{project_id}/ai', {
        params: { path: { project_id: trimmedId } },
      })
      if (data) {
        setSettings(data.settings)
        setLoadedProjectId(trimmedId)
      } else {
        setSettings(null)
        setLoadedProjectId(null)
        setLoadError(errorMessage(error, 'Failed to load AI settings.'))
      }
    } catch {
      setSettings(null)
      setLoadedProjectId(null)
      setLoadError('Network error while loading AI settings.')
    } finally {
      setLoading(false)
    }
  }

  const toggleKind = async (kind: ChatKind) => {
    if (!UUID_RE.test(trimmedId) || trimmedId !== loadedProjectId) {
      setLoadError('Load state for this project id first.')
      return
    }
    const current = settings?.[kind]?.enabled ?? false
    const next = !current
    setTogglingKind(kind)
    setToggleMessage(null)
    setToggleIsError(false)
    try {
      const { error } = await client.PUT('/api/admin/projects/{project_id}/ai/{kind}', {
        params: { path: { project_id: trimmedId, kind } },
        body: { enabled: next },
      })
      if (error) {
        setToggleIsError(true)
        setToggleMessage(errorMessage(error, `Failed to ${next ? 'enable' : 'disable'} ${kind}.`))
      } else {
        setToggleMessage(`${kind}: ${next ? 'enabled' : 'disabled'}.`)
        await loadState()
      }
    } catch {
      setToggleIsError(true)
      setToggleMessage('Network error while updating the AI setting.')
    } finally {
      setTogglingKind(null)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24, padding: 24, background: '#fafafa', fontFamily: 'var(--dlw-font-body)' }}>
      <div style={{ width: 480, border: '1px solid #E2E2E2', borderRadius: 12, background: '#fff', padding: 16 }}>
        <h2 style={{ margin: '0 0 8px', fontSize: 16 }}>Dev only: AI surface toggle (temporary)</h2>
        <p style={{ fontSize: 12, color: '#8A8A8A', margin: '0 0 12px' }}>
          Paste the project id (UUID) of the project whose AI surface you want to toggle, then
          "Load state". This calls the admin-only settings endpoint directly — /api/me does not
          expose project_id, so manual entry is expected for this dev harness.
        </p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            placeholder="project id (uuid)"
            style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid #E2E2E2' }}
          />
          <button type="button" onClick={() => void loadState()} disabled={loading || !validId}>
            {loading ? 'Loading…' : 'Load state'}
          </button>
        </div>

        {loadError && <div style={{ color: '#C42828', fontSize: 13, marginBottom: 8 }}>{loadError}</div>}
        {toggleMessage && (
          <div style={{ color: toggleIsError ? '#C42828' : '#1A1A1A', fontSize: 13, marginBottom: 8 }}>
            {toggleMessage}
          </div>
        )}

        {settings && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {idMismatch && (
              <div style={{ color: '#8A8A8A', fontSize: 12 }}>
                Input no longer matches the loaded project. Load state for this project id first.
              </div>
            )}
            {KINDS.map((kind) => {
              const enabled = settings[kind]?.enabled ?? false
              return (
                <div key={kind} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14 }}>
                    {kind}: <strong>{enabled ? 'enabled' : 'disabled'}</strong>
                  </span>
                  <button
                    type="button"
                    onClick={() => void toggleKind(kind)}
                    disabled={togglingKind === kind || idMismatch}
                  >
                    {togglingKind === kind ? '…' : enabled ? 'Disable' : 'Enable'}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div style={{ height: '70vh', width: 480, border: '1px solid #E2E2E2', borderRadius: 12, background: '#fff' }}>
        <ChatPanel kind="chatbot" />
      </div>
    </div>
  )
}
