import { useState, type CSSProperties } from 'react'
import type { AdminLearning, AdminLearningUser, AdminSurvey, AdminUser, Track } from '../../types/domain'
import { s } from './adminStyles'
import { LevelBadge } from './adminHelpers'
import SurveyResults from './SurveyResults'
import { resolveTrackColor } from '../../lib/trackColors'
import { LEVELS, levelByCode } from '../../lib/levels'

// The three assignable pins (the scoring engine never produces 'multiplier',
// which gates nothing — so it isn't offered as an override here).
const PIN_LEVELS = LEVELS.filter(l => l.code !== 'multiplier')

interface ParticipantDetailProps {
  user: AdminUser | null
  survey: AdminSurvey | null | undefined // undefined = still loading
  loadingPanel: boolean
  learningUser: AdminLearningUser | null
  tracks: Track[]
  learningData: AdminLearning
  togglingItem: string | null
  savingMaturity: boolean
  onToggleLearning: (action: 'track' | 'module' | 'lesson', userId: string, itemId: string, currentlyAssigned: boolean) => void
  onBulkAssign: (kind: 'tracks' | 'modules' | 'lessons', userId: string, groupId: string, ids: string[], assigned: boolean) => void
  onSetMaturity: (userId: string, level: string | null) => void
}

const expanderBtn: CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px',
  fontSize: 11, color: '#8A8A8A', display: 'flex', alignItems: 'center', gap: 4,
  fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
}

const addAllBtn: CSSProperties = {
  background: 'none', border: '1px dashed #C4C4C4', borderRadius: 999,
  padding: '3px 10px', cursor: 'pointer', fontSize: 11, color: '#8A8A8A',
  fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, letterSpacing: '0.04em',
}

const unassignAllBtn: CSSProperties = {
  ...addAllBtn, border: '1px dashed #E0C0C0', color: '#B04A4A',
}

const maturityBox: CSSProperties = {
  marginTop: 14, padding: '12px 14px', background: '#FAFAF9',
  border: '1px solid #F0EFED', borderRadius: 8,
}

const pinnedTag: CSSProperties = {
  fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 10,
  letterSpacing: '0.08em', textTransform: 'uppercase',
  background: '#EEF2FF', color: '#4B5CC4', padding: '2px 8px', borderRadius: 999,
}

const maturityHint: CSSProperties = {
  fontSize: 11, fontWeight: 300, color: '#8A8A8A', margin: '8px 0 0', lineHeight: 1.5,
}

export default function ParticipantDetail({
  user, survey, loadingPanel, learningUser,
  tracks, learningData, togglingItem, savingMaturity,
  onToggleLearning, onBulkAssign, onSetMaturity,
}: ParticipantDetailProps) {
  const [expandedTracks, setExpandedTracks] = useState<Set<string>>(new Set())
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set())

  // Introduction tracks are mandatory/implicit — never per-user assignable.
  const assignableTracks = tracks.filter(t => !t.is_introduction)

  if (!user) return null

  function toggleExpanded(trackId: string) {
    setExpandedTracks(prev => {
      const next = new Set(prev)
      if (next.has(trackId)) next.delete(trackId); else next.add(trackId)
      return next
    })
  }

  function toggleModuleExpanded(moduleId: string) {
    setExpandedModules(prev => {
      const next = new Set(prev)
      if (next.has(moduleId)) next.delete(moduleId); else next.add(moduleId)
      return next
    })
  }

  return (
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

        {/* Maturity level — pin (or fall back to the assessment). The pin is
            only a starting point: completing modules can still raise the
            effective level above it (never below what's earned). */}
        <div style={maturityBox}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 10 }}>
            <span style={s.surveyQLabel as CSSProperties}>Maturity level</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              {user.effective_maturity
                ? <LevelBadge level={user.effective_maturity} />
                : <span style={{ fontSize: 12, color: '#C4C4C4' }}>none yet</span>}
              {user.maturity_override && <span style={pinnedTag}>pinned</span>}
            </span>
          </div>
          <select
            style={{ ...s.select, ...(savingMaturity ? { opacity: 0.5, cursor: 'wait' } : {}) }}
            disabled={savingMaturity}
            value={user.maturity_override ?? ''}
            onChange={e => onSetMaturity(user.id, e.target.value || null)}
          >
            <option value="">
              From assessment{survey?.score_level ? ` (${levelByCode(survey.score_level)?.name ?? survey.score_level})` : ''}
            </option>
            {PIN_LEVELS.map(l => (
              <option key={l.code} value={l.code}>Pin to {l.name}</option>
            ))}
          </select>
          <p style={maturityHint}>
            A pin sets the starting level; finishing a level's modules still advances it.
          </p>
        </div>
      </div>

      {/* track assignment with inline module + lesson selection */}
      {learningUser && (
        <div style={s.panelSection}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <p style={s.panelSectionTitle}>Track assignment</p>
            <div style={{ display: 'flex', gap: 6 }}>
              {(() => {
                const allTrackIds = assignableTracks.map(t => t.id)
                const assignedCount = allTrackIds.filter(id => learningUser.assigned_track_ids.includes(id)).length
                const bulkBusy = togglingItem === `bulk-tracks-${learningUser.id}-all`
                return (
                  <>
                    {assignedCount < allTrackIds.length && (
                      <button
                        type="button"
                        style={{ ...addAllBtn, ...(bulkBusy ? s.toggleBusy : {}) }}
                        onClick={() => onBulkAssign('tracks', learningUser.id, 'all', allTrackIds, true)}
                        disabled={bulkBusy}
                      >
                        {bulkBusy ? '…' : '+ add all tracks'}
                      </button>
                    )}
                    {assignedCount > 0 && (
                      <button
                        type="button"
                        style={{ ...unassignAllBtn, ...(bulkBusy ? s.toggleBusy : {}) }}
                        onClick={() => {
                          onBulkAssign('tracks', learningUser.id, 'all', allTrackIds, false)
                          setExpandedTracks(new Set())
                        }}
                        disabled={bulkBusy}
                      >
                        {bulkBusy ? '…' : '− unassign all'}
                      </button>
                    )}
                  </>
                )
              })()}
            </div>
          </div>
          {assignableTracks.map(track => {
            const assigned = learningUser.assigned_track_ids.includes(track.id)
            const busy = togglingItem === `track-${learningUser.id}-${track.id}`
            const trackModules = learningData.modules.filter(m => m.track_id === track.id)
            const expanded = expandedTracks.has(track.id)
            const unassignedModuleIds = trackModules
              .filter(m => !learningUser.assigned_module_ids.includes(m.id))
              .map(m => m.id)
            const bulkModulesBusy = togglingItem === `bulk-modules-${learningUser.id}-${track.id}`
            return (
              <div key={track.id} style={{ borderBottom: '1px solid #F5F5F5' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: resolveTrackColor(track), flexShrink: 0 }} />
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#101820' }}>{track.name}</span>
                    <span style={{ fontSize: 10, color: '#C4C4C4', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--dlw-font-ui)' }}>{track.track_type}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {assigned && trackModules.length > 0 && (
                      <button
                        type="button"
                        style={expanderBtn}
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
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                        {unassignedModuleIds.length > 0 && (
                          <button
                            type="button"
                            style={{ ...addAllBtn, ...(bulkModulesBusy ? s.toggleBusy : {}) }}
                            onClick={() => onBulkAssign('modules', learningUser.id, track.id, trackModules.map(m => m.id), true)}
                            disabled={bulkModulesBusy}
                          >
                            {bulkModulesBusy ? '…' : '+ add all modules'}
                          </button>
                        )}
                        {unassignedModuleIds.length < trackModules.length && (
                          <button
                            type="button"
                            style={{ ...unassignAllBtn, ...(bulkModulesBusy ? s.toggleBusy : {}) }}
                            onClick={() => {
                              onBulkAssign('modules', learningUser.id, track.id, trackModules.map(m => m.id), false)
                              setExpandedModules(prev => {
                                const n = new Set(prev)
                                trackModules.forEach(m => n.delete(m.id))
                                return n
                              })
                            }}
                            disabled={bulkModulesBusy}
                          >
                            {bulkModulesBusy ? '…' : '− unassign all'}
                          </button>
                        )}
                    </div>
                    {trackModules.map(mod => {
                      const modAssigned = learningUser.assigned_module_ids.includes(mod.id)
                      const modBusy = togglingItem === `module-${learningUser.id}-${mod.id}`
                      const moduleLessons = learningData.lessons.filter(l => l.module_id === mod.id)
                      const assignedLessonCount = moduleLessons
                        .filter(l => learningUser.assigned_lesson_ids.includes(l.id)).length
                      const modExpanded = expandedModules.has(mod.id)
                      const bulkLessonsBusy = togglingItem === `bulk-lessons-${learningUser.id}-${mod.id}`
                      return (
                        <div key={mod.id} style={{ background: '#FAFAF9', borderRadius: 6, border: '1px solid #F0EFED' }}>
                          <div style={{ ...s.moduleItem, background: 'none', border: 'none' }}>
                            <span style={s.moduleTitle}>{mod.title}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              {modAssigned && moduleLessons.length > 0 && (
                                <button
                                  type="button"
                                  style={expanderBtn}
                                  onClick={() => toggleModuleExpanded(mod.id)}
                                >
                                  {assignedLessonCount}/{moduleLessons.length} lessons {modExpanded ? '▲' : '▼'}
                                </button>
                              )}
                              <button
                                style={{ ...(modAssigned ? s.toggleAssigned : s.toggleUnassigned), ...(modBusy ? s.toggleBusy : {}) }}
                                onClick={() => {
                                  onToggleLearning('module', learningUser.id, mod.id, modAssigned)
                                  if (modAssigned) setExpandedModules(prev => { const n = new Set(prev); n.delete(mod.id); return n })
                                  else if (moduleLessons.length > 0) setExpandedModules(prev => new Set(prev).add(mod.id))
                                }}
                                disabled={modBusy}
                              >
                                {modBusy ? '…' : modAssigned ? 'assigned' : '—'}
                              </button>
                            </div>
                          </div>
                          {modAssigned && modExpanded && moduleLessons.length > 0 && (
                            <div style={{ padding: '0 14px 10px 26px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                                {assignedLessonCount < moduleLessons.length && (
                                  <button
                                    type="button"
                                    style={{ ...addAllBtn, ...(bulkLessonsBusy ? s.toggleBusy : {}) }}
                                    onClick={() => onBulkAssign('lessons', learningUser.id, mod.id, moduleLessons.map(l => l.id), true)}
                                    disabled={bulkLessonsBusy}
                                  >
                                    {bulkLessonsBusy ? '…' : '+ add all lessons'}
                                  </button>
                                )}
                                {assignedLessonCount > 0 && (
                                  <button
                                    type="button"
                                    style={{ ...unassignAllBtn, ...(bulkLessonsBusy ? s.toggleBusy : {}) }}
                                    onClick={() => onBulkAssign('lessons', learningUser.id, mod.id, moduleLessons.map(l => l.id), false)}
                                    disabled={bulkLessonsBusy}
                                  >
                                    {bulkLessonsBusy ? '…' : '− unassign all'}
                                  </button>
                                )}
                              </div>
                              {moduleLessons.map(lesson => {
                                const lessonAssigned = learningUser.assigned_lesson_ids.includes(lesson.id)
                                const lessonBusy = togglingItem === `lesson-${learningUser.id}-${lesson.id}`
                                return (
                                  <div key={lesson.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <span style={{ fontSize: 12, fontWeight: 300, color: '#3C3C3C' }}>{lesson.title}</span>
                                    <button
                                      style={{ ...(lessonAssigned ? s.toggleAssigned : s.toggleUnassigned), ...(lessonBusy ? s.toggleBusy : {}), padding: '2px 10px', fontSize: 10 }}
                                      onClick={() => onToggleLearning('lesson', learningUser.id, lesson.id, lessonAssigned)}
                                      disabled={lessonBusy}
                                    >
                                      {lessonBusy ? '…' : lessonAssigned ? 'assigned' : '—'}
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
            )
          })}
        </div>
      )}

    </div>
  )
}
