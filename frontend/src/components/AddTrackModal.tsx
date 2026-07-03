import { useState } from 'react'
import { client, errorMessage } from '../api/client'
import type { Track } from '../types/domain'

// The old modal computed sort_order client-side from a `tracks` prop;
// POST /api/admin/tracks assigns it server-side (fixes A4), so the prop is gone.

const PRESET_COLORS = ['#3BC9BC', '#C42828', '#8A3BC9', '#2878C4', '#1D7A52', '#C4852A', '#EF463C']

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
  textTransform: 'uppercase', letterSpacing: '0.08em', color: '#8A8A8A',
  marginBottom: 6, display: 'block',
}

interface AddTrackModalProps {
  onClose: () => void
  onAdded: (track: Track) => void
}

export default function AddTrackModal({ onClose, onAdded }: AddTrackModalProps) {
  const [name, setName]           = useState('')
  const [trackType, setTrackType] = useState<'tool' | 'general'>('tool')
  const [color, setColor]         = useState('#3BC9BC')
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState<string | null>(null)

  async function handleSubmit() {
    if (!name.trim()) { setError('Track name is required.'); return }
    setSaving(true)
    setError(null)
    try {
      const { data, error: err } = await client.POST('/api/admin/tracks', {
        body: { name: name.trim(), track_type: trackType, color },
      })
      setSaving(false)
      if (!data) { setError(errorMessage(err, 'Failed to add track.')); return }
      onAdded(data)
    } catch {
      setSaving(false)
      setError('Network error.')
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(16,24,32,0.45)', zIndex: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#fff', borderRadius: 16, boxShadow: '0 24px 64px -12px rgba(16,24,32,.28)', width: 440, maxWidth: '90vw', padding: 28 }}>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <h2 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 20, color: '#101820', margin: 0 }}>Add Track</h2>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: '50%', border: '1px solid #E2E2E2', background: '#fff', color: '#8A8A8A', fontSize: 18, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1 }}>×</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

          <div>
            <label style={labelStyle}>Track name</label>
            <input
              autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="e.g. Microsoft Teams"
              style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #E2E2E2', borderRadius: 8, fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#101820', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={labelStyle}>Track type</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {([
                { value: 'tool',    label: 'Tool (branch)' },
                { value: 'general', label: 'General (main trunk)' },
              ] as const).map(opt => (
                <button key={opt.value} type="button" onClick={() => setTrackType(opt.value)}
                  style={{
                    flex: 1, padding: '10px 0', borderRadius: 8, cursor: 'pointer',
                    border: trackType === opt.value ? '2px solid #3BC9BC' : '1.5px solid #E2E2E2',
                    background: trackType === opt.value ? '#F0FAF9' : '#fff',
                    color: trackType === opt.value ? '#1D7A52' : '#3C3C3C',
                    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
                  }}>
                  {opt.label}
                </button>
              ))}
            </div>
            <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 12, color: '#8A8A8A', margin: '6px 0 0' }}>
              {trackType === 'general'
                ? 'The central vertical path — usually one per graph.'
                : 'A specialised branch that appears below the general track.'}
            </p>
          </div>

          <div>
            <label style={labelStyle}>Label colour</label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              {PRESET_COLORS.map(c => (
                <button key={c} type="button" onClick={() => setColor(c)}
                  style={{
                    width: 28, height: 28, borderRadius: '50%', background: c,
                    border: color === c ? `3px solid ${c}` : '2px solid transparent',
                    outline: color === c ? `2px solid #fff` : 'none',
                    outlineOffset: -4,
                    cursor: 'pointer', padding: 0, flexShrink: 0,
                  }} />
              ))}
              <input type="color" value={color} onChange={e => setColor(e.target.value)}
                title="Custom colour"
                style={{ width: 28, height: 28, border: '1.5px solid #E2E2E2', borderRadius: 6, cursor: 'pointer', padding: 2, background: '#fff' }} />
            </div>
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
          <button onClick={handleSubmit} disabled={saving}
            style={{ padding: '10px 20px', borderRadius: 8, border: 'none', background: '#3BC9BC', color: '#fff', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, cursor: saving ? 'default' : 'pointer', opacity: saving ? 0.7 : 1 }}>
            {saving ? 'Adding…' : 'Add Track'}
          </button>
        </div>

      </div>
    </div>
  )
}
