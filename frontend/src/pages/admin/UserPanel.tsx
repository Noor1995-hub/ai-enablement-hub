import { useState } from 'react'
import type { AdminLearning, AdminLearningUser, AdminSurvey, AdminUser, Track } from '../../types/domain'
import { s } from './adminStyles'
import SurveyResults from './SurveyResults'

interface UserPanelProps {
  user: AdminUser | null
  survey: AdminSurvey | null | undefined // undefined = still loading
  loadingPanel: boolean
  learningUser: AdminLearningUser | null
  tracks: Track[]
  learningData: AdminLearning
  togglingItem: string | null
  onToggleLearning: (action: 'track' | 'module', userId: string, itemId: string, currentlyAssigned: boolean) => void
  onClose: () => void
}

export default function UserPanel({
  user, survey, loadingPanel, learningUser,
  tracks, learningData, togglingItem,
  onToggleLearning, onClose,
}: UserPanelProps) {
  const [expandedTracks, setExpandedTracks] = useState<Set<string>>(new Set())

  if (!user) return null

  function toggleExpanded(trackId: string) {
    setExpandedTracks(prev => {
      const next = new Set(prev)
      if (next.has(trackId)) next.delete(trackId); else next.add(trackId)
      return next
    })
  }

  return (
    <div style={s.panelOverlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={s.panel}>
        {/* header */}
        <div style={s.panelHeader}>
          <div>
            <p style={s.panelName}>{user.first_name} {user.last_name}</p>
            <p style={s.panelMeta}>{user.email}</p>
          </div>
          <button type="button" style={s.panelClose} onClick={onClose}>×</button>
        </div>

        <div style={s.panelBody}>

          {/* survey results */}
          <div style={s.panelSection}>
            <p style={s.panelSectionTitle}>Assessment results</p>
            {loadingPanel ? (
              <p style={s.noSurvey}>loading…</p>
            ) : !survey ? (
              <p style={s.noSurvey}>No completed assessment yet.</p>
            ) : (
              <SurveyResults survey={survey} />
            )}
          </div>

          {/* track assignment with inline module selection */}
          {learningUser && (
            <div style={s.panelSection}>
              <p style={s.panelSectionTitle}>Track assignment</p>
              {tracks.map(track => {
                const assigned = learningUser.assigned_track_ids.includes(track.id)
                const busy = togglingItem === `track-${learningUser.id}-${track.id}`
                const trackModules = learningData.modules.filter(m => m.track_id === track.id)
                const expanded = expandedTracks.has(track.id)
                return (
                  <div key={track.id} style={{ borderBottom: '1px solid #F5F5F5' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {track.color && <span style={{ width: 8, height: 8, borderRadius: '50%', background: track.color, flexShrink: 0 }} />}
                        <span style={{ fontSize: 14, fontWeight: 600, color: '#101820' }}>{track.name}</span>
                        <span style={{ fontSize: 10, color: '#C4C4C4', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--dlw-font-ui)' }}>{track.track_type}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {assigned && trackModules.length > 0 && (
                          <button
                            type="button"
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px', fontSize: 11, color: '#8A8A8A', display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600 }}
                            onClick={() => toggleExpanded(track.id)}
                          >
                            {trackModules.length} modules {expanded ? '▲' : '▼'}
                          </button>
                        )}
                        <button
                          style={{ ...(assigned ? s.toggleAssigned : s.toggleUnassigned), ...(busy ? s.toggleBusy : {}) }}
                          onClick={() => {
                            onToggleLearning('track', learningUser.id, track.id, assigned)
                            if (assigned) setExpandedTracks(prev => { const n = new Set(prev); n.delete(track.id); return n })
                          }}
                          disabled={busy}
                        >
                          {busy ? '…' : assigned ? 'assigned' : '—'}
                        </button>
                      </div>
                    </div>
                    {assigned && expanded && trackModules.length > 0 && (
                      <div style={{ ...s.moduleList, paddingLeft: 16, paddingBottom: 12 }}>
                        {trackModules.map(mod => {
                          const modAssigned = learningUser.assigned_module_ids.includes(mod.id)
                          const modBusy = togglingItem === `module-${learningUser.id}-${mod.id}`
                          return (
                            <div key={mod.id} style={s.moduleItem}>
                              <span style={s.moduleTitle}>{mod.title}</span>
                              <button
                                style={{ ...(modAssigned ? s.toggleAssigned : s.toggleUnassigned), ...(modBusy ? s.toggleBusy : {}) }}
                                onClick={() => onToggleLearning('module', learningUser.id, mod.id, modAssigned)}
                                disabled={modBusy}
                              >
                                {modBusy ? '…' : modAssigned ? 'assigned' : '—'}
                              </button>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
