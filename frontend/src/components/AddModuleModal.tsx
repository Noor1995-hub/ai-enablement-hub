import { useState, useEffect } from 'react'
import { client, errorMessage } from '../api/client'
import type { ModuleOut, Track, TrackModule } from '../types/domain'

// ⚠ Contract note: the design doc's `POST /api/modules {…, col_offset, …}` is
// stale — the real endpoint is POST /api/admin/modules (ModuleCreateRequest),
// which has NO col_offset (the column never existed). sort_order + prerequisite
// links happen server-side in one transaction; omitting after_module_id appends
// at the end of the track, matching the old modal's max(sort_order)+1 insert.

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
  textTransform: 'uppercase', letterSpacing: '0.08em', color: '#8A8A8A',
  marginBottom: 6, display: 'block',
}

const selectStyle: React.CSSProperties = {
  width: '100%', padding: '10px 12px', border: '1.5px solid #E2E2E2',
  borderRadius: 8, fontFamily: 'var(--dlw-font-body)', fontSize: 14,
  color: '#101820', outline: 'none', boxSizing: 'border-box', background: '#fff',
}

interface AddModuleModalProps {
  onClose: () => void
  onAdded: (module: ModuleOut) => void
}

export default function AddModuleModal({ onClose, onAdded }: AddModuleModalProps) {
  const [allTracks, setAllTracks]       = useState<Track[]>([])
  const [trackId, setTrackId]           = useState('')
  const [trackModules, setTrackModules] = useState<TrackModule[]>([])
  const [title, setTitle]               = useState('')
  const [predecessorIds, setPredecessorIds] = useState<string[]>([])
  const [loadingTracks, setLoadingTracks]   = useState(true)
  const [loadingModules, setLoadingModules] = useState(false)
  const [saving, setSaving]             = useState(false)
  const [error, setError]               = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    client.GET('/api/tracks')
      .then(({ data }) => {
        if (cancelled) return
        const sorted = data ? [...data].sort((a, b) => a.sort_order - b.sort_order) : []
        setAllTracks(sorted)
        if (sorted.length) setTrackId(sorted[0].id)
        setLoadingTracks(false)
      })
      .catch(() => { if (!cancelled) setLoadingTracks(false) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!trackId) return
    let cancelled = false
    setLoadingModules(true)
    client.GET('/api/tracks/{track_id}/modules', { params: { path: { track_id: trackId } } })
      .then(({ data }) => {
        if (cancelled) return
        setTrackModules(data ?? [])
        setPredecessorIds([])
        setLoadingModules(false)
      })
      .catch(() => { if (!cancelled) setLoadingModules(false) })
    return () => { cancelled = true }
  }, [trackId])

  function togglePredecessor(id: string) {
    setPredecessorIds(ids => ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id])
  }

  async function handleSubmit() {
    if (!title.trim()) { setError('Module title is required.'); return }
    if (!trackId) { setError('Please select a track.'); return }
    setSaving(true)
    setError(null)

    try {
      const { data, error: err } = await client.POST('/api/admin/modules', {
        body: { track_id: trackId, title: title.trim(), prerequisite_ids: predecessorIds },
      })
      setSaving(false)
      if (!data) { setError(errorMessage(err, 'Failed to add module.')); return }
      onAdded(data)
    } catch {
      setSaving(false)
      setError('Network error.')
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(16,24,32,0.45)', zIndex: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#fff', borderRadius: 16, boxShadow: '0 24px 64px -12px rgba(16,24,32,.28)', width: 480, maxWidth: '90vw', padding: 28 }}>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <h2 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 20, color: '#101820', margin: 0 }}>Add Module</h2>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: '50%', border: '1px solid #E2E2E2', background: '#fff', color: '#8A8A8A', fontSize: 18, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1 }}>×</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

          <div>
            <label style={labelStyle}>Module title</label>
            <input
              autoFocus
              value={title}
              onChange={e => setTitle(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="e.g. Copilot basics"
              style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #E2E2E2', borderRadius: 8, fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#101820', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={labelStyle}>Track</label>
            {loadingTracks ? (
              <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#8A8A8A', margin: 0 }}>Loading tracks…</p>
            ) : allTracks.length === 0 ? (
              <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#C42828', margin: 0 }}>No tracks found. Add a track first.</p>
            ) : (
              <select value={trackId} onChange={e => setTrackId(e.target.value)} style={selectStyle}>
                {allTracks.map(t => (
                  <option key={t.id} value={t.id}>{t.name} ({t.track_type})</option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label style={labelStyle}>Prerequisites (in this track)</label>
            {loadingModules ? (
              <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#8A8A8A', margin: 0 }}>Loading modules…</p>
            ) : trackModules.length === 0 ? (
              <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#8A8A8A', margin: 0 }}>No modules in this track yet — this will be the first.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 180, overflowY: 'auto', border: '1.5px solid #E2E2E2', borderRadius: 8, padding: 10 }}>
                {trackModules.map(m => (
                  <label key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#101820', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={predecessorIds.includes(m.id)}
                      onChange={() => togglePredecessor(m.id)}
                    />
                    {m.title}
                  </label>
                ))}
              </div>
            )}
            <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 12, color: '#8A8A8A', margin: '6px 0 0' }}>
              The new module unlocks once every selected prerequisite is completed. Leave empty to start the track.
            </p>
          </div>

        </div>

        {error && (
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 13, color: '#C42828', background: '#FEF2F2', padding: '8px 12px', borderRadius: 6, margin: '16px 0 0' }}>
            {error}
          </p>
        )}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 24 }}>
          <button onClick={onClose}
            style={{ padding: '10px 20px', borderRadius: 8, border: '1.5px solid #E2E2E2', background: '#fff', color: '#3C3C3C', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={saving || allTracks.length === 0}
            style={{ padding: '10px 20px', borderRadius: 8, border: 'none', background: '#3BC9BC', color: '#fff', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, cursor: (saving || allTracks.length === 0) ? 'default' : 'pointer', opacity: (saving || allTracks.length === 0) ? 0.7 : 1 }}>
            {saving ? 'Adding…' : 'Add Module'}
          </button>
        </div>

      </div>
    </div>
  )
}
