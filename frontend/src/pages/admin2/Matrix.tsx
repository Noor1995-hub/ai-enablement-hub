import { useState } from 'react'
import { levelByCode } from '../../lib/levels'
import { resolveTrackColor } from '../../lib/trackColors'
import type { AdminLearningResponseEnriched, AdminLearningUserEnriched, Track } from '../../types/domain'
import type { AssignmentKind } from './api'
import { useApplyDefaults, useSetDefaults, useToggleAssignment } from './api'
import { EmptyState } from './kit'
import type { Level } from './AssignmentsPage'

type LearningModule = AdminLearningResponseEnriched['modules'][number]
type LearningLesson = AdminLearningResponseEnriched['lessons'][number]
type CellState = 'yes' | 'def' | 'part' | ''

const CELL_CLASS: Record<CellState, string> = {
  yes: 'adm-cell-yes',
  def: 'adm-cell-def',
  part: 'adm-cell-part',
  '': '',
}

const CELL_TITLE: Record<CellState, string> = {
  yes: 'Assigned (explicit) — click to unassign',
  def: 'Assigned via project default — click to override',
  part: 'Partially assigned — drill in for detail, or click to assign all',
  '': 'Not assigned — click to assign',
}

/**
 * Cell state for one user × content-item, derived entirely client-side from the
 * enriched assignment/default arrays (spec §3.4):
 * - in `assigned_*` and NOT in `default_*` → `yes` (explicit, solid ✓)
 * - in both → `def` (via project default, tinted ✓)
 * - not assigned itself but SOME-but-not-all children assigned → `part` (◐)
 *   (tracks check their modules, modules check their lessons; lessons have none)
 * - else empty.
 */
function deriveCellState(
  kind: AssignmentKind,
  itemId: string,
  user: AdminLearningUserEnriched,
  modules: LearningModule[],
  lessons: LearningLesson[],
): CellState {
  const assigned =
    kind === 'track'
      ? user.assigned_track_ids
      : kind === 'module'
        ? user.assigned_module_ids
        : user.assigned_lesson_ids
  const defaults =
    kind === 'track'
      ? user.default_track_ids
      : kind === 'module'
        ? user.default_module_ids
        : user.default_lesson_ids

  if (assigned.includes(itemId)) {
    return defaults.includes(itemId) ? 'def' : 'yes'
  }

  // Partial is a coverage signal over the item's direct children.
  const childIds =
    kind === 'track'
      ? modules.filter(m => m.track_id === itemId).map(m => m.id)
      : kind === 'module'
        ? lessons.filter(l => l.module_id === itemId).map(l => l.id)
        : []
  if (childIds.length === 0) return ''
  const assignedChildren = new Set(kind === 'track' ? user.assigned_module_ids : user.assigned_lesson_ids)
  const covered = childIds.filter(id => assignedChildren.has(id)).length
  return covered > 0 && covered < childIds.length ? 'part' : ''
}

interface Column {
  id: string
  name: string
  levelName?: string
  dotColor?: string
}

interface MatrixProps {
  projectId: string
  level: Level
  onSelect: (level: Level) => void
  /** Assignable (non-introduction) tracks, sorted by `sort_order`. */
  tracks: Track[]
  modules: LearningModule[]
  lessons: LearningLesson[]
  users: AdminLearningUserEnriched[]
  /** Project default track ids (`useDefaults`) — drives the defaults row. */
  defaultTrackIds: string[]
}

/** The users × content matrix (spec §3.4): a project-defaults row first, then
 * one row per participant, with a breadcrumb mirroring the scope tree and an
 * always-visible legend. Prototype: docs/design-prototypes/admin-redesign
 * common.js `mountMatrix()`. */
export default function Matrix({
  projectId,
  level,
  onSelect,
  tracks,
  modules,
  lessons,
  users,
  defaultTrackIds,
}: MatrixProps) {
  const toggle = useToggleAssignment()
  const setDefaults = useSetDefaults()
  const applyDefaults = useApplyDefaults()
  const [showApplyHint, setShowApplyHint] = useState(false)

  const kind: AssignmentKind =
    level.level === 'tracks' ? 'track' : level.level === 'modules' ? 'module' : 'lesson'

  const trackName = 'trackId' in level ? (tracks.find(t => t.id === level.trackId)?.name ?? '—') : ''
  const moduleName =
    level.level === 'lessons' ? (modules.find(m => m.id === level.moduleId)?.title ?? '—') : ''

  const columns: Column[] =
    level.level === 'tracks'
      ? tracks.map(track => ({
          id: track.id,
          name: track.name,
          levelName: levelByCode(track.required_level)?.name,
          dotColor: resolveTrackColor(track),
        }))
      : level.level === 'modules'
        ? modules
            .filter(module => module.track_id === level.trackId)
            .map(module => ({ id: module.id, name: module.title }))
        : lessons
            .filter(lesson => lesson.module_id === level.moduleId)
            .map(lesson => ({ id: lesson.id, name: lesson.title }))

  // Defaults are track-level only. At track scope each column toggles its own
  // default; at module/lesson scope the whole row is read-only and tinted iff
  // the (single) parent track is a default.
  const parentTrackIsDefault = 'trackId' in level && defaultTrackIds.includes(level.trackId)

  function handleCellClick(userId: string, itemId: string, state: CellState) {
    const assigned = !(state === 'yes' || state === 'def')
    toggle.mutate({ userId, kind, id: itemId, assigned })
  }

  function handleDefaultToggle(trackId: string, isDefault: boolean) {
    const trackIds = isDefault ? defaultTrackIds.filter(id => id !== trackId) : [...defaultTrackIds, trackId]
    setDefaults.mutate({ projectId, trackIds }, { onSuccess: () => setShowApplyHint(true) })
  }

  const errorMsg = toggle.isError
    ? toggle.error instanceof Error
      ? toggle.error.message
      : 'Failed to update assignment.'
    : setDefaults.isError
      ? setDefaults.error instanceof Error
        ? setDefaults.error.message
        : 'Failed to save default tracks.'
      : applyDefaults.isError
        ? applyDefaults.error instanceof Error
          ? applyDefaults.error.message
          : 'Failed to apply default tracks.'
        : null

  const hint =
    level.level === 'tracks'
      ? 'track-level assignment'
      : level.level === 'modules'
        ? `modules of ${trackName}`
        : 'lesson-level assignment'

  return (
    <div className="adm-matrix-side">
      <div className="adm-matrix-nav">
        <button
          type="button"
          className={`adm-crumb${level.level === 'tracks' ? ' here' : ''}`}
          onClick={() => onSelect({ level: 'tracks' })}
        >
          All tracks
        </button>
        {'trackId' in level && (
          <>
            <span className="adm-crumb-sep">
              <ChevronIcon />
            </span>
            <button
              type="button"
              className={`adm-crumb${level.level === 'modules' ? ' here' : ''}`}
              onClick={() => onSelect({ level: 'modules', trackId: level.trackId })}
            >
              {trackName}
            </button>
          </>
        )}
        {level.level === 'lessons' && (
          <>
            <span className="adm-crumb-sep">
              <ChevronIcon />
            </span>
            <span className="adm-crumb here">{moduleName}</span>
          </>
        )}
        <span className="adm-matrix-hint">{hint}</span>
      </div>

      {errorMsg && (
        <div className="adm-matrix-msg">
          <p className="adm-form-msg adm-form-msg-err">{errorMsg}</p>
        </div>
      )}

      {showApplyHint && (
        <div className="adm-apply-hint">
          <span>Applies to new participants — Apply to existing?</span>
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm"
            disabled={applyDefaults.isPending}
            onClick={() => applyDefaults.mutate(projectId, { onSuccess: () => setShowApplyHint(false) })}
          >
            Apply now
          </button>
        </div>
      )}

      {columns.length === 0 ? (
        <div className="adm-matrix-msg">
          <EmptyState
            title={
              level.level === 'tracks'
                ? 'No tracks available'
                : level.level === 'modules'
                  ? 'No modules in this track'
                  : 'No lessons in this module'
            }
          />
        </div>
      ) : (
        <div className="adm-matrix-wrap">
          <table className="adm-matrix">
            <thead>
              <tr>
                <th className="adm-matrix-rowhead">Participant</th>
                {columns.map(col => (
                  <th key={col.id}>
                    {col.name}
                    {col.levelName && (
                      <span className="adm-matrix-lvl">
                        <span className="adm-matrix-lvl-dot" style={{ background: col.dotColor }} />
                        {col.levelName}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="adm-defaults-row">
                <td className="adm-matrix-rowhead">
                  Project defaults
                  <br />
                  <span className="adm-subtext adm-defaults-label">new participants inherit these</span>
                </td>
                {columns.map(col => {
                  if (level.level === 'tracks') {
                    const isDefault = defaultTrackIds.includes(col.id)
                    return (
                      <td key={col.id}>
                        <button
                          type="button"
                          className={`adm-cell${isDefault ? ' adm-cell-yes' : ''}`}
                          title="Project default — new participants inherit this; click to toggle"
                          disabled={setDefaults.isPending}
                          onClick={() => handleDefaultToggle(col.id, isDefault)}
                        >
                          {isDefault && <CheckIcon />}
                        </button>
                      </td>
                    )
                  }
                  return (
                    <td key={col.id}>
                      <button
                        type="button"
                        className={`adm-cell${parentTrackIsDefault ? ' adm-cell-def' : ''}`}
                        title="Defaults are track-level"
                        disabled
                      >
                        {parentTrackIsDefault && <CheckIcon />}
                      </button>
                    </td>
                  )
                })}
              </tr>

              {users.map(user => (
                <tr key={user.id}>
                  <td className="adm-matrix-rowhead">
                    <div className="adm-user-cell">
                      <span className="adm-user-avatar">{initials(`${user.first_name} ${user.last_name}`)}</span>
                      <span className="adm-user-name">
                        {user.first_name} {user.last_name}
                      </span>
                    </div>
                  </td>
                  {columns.map(col => {
                    const state = deriveCellState(kind, col.id, user, modules, lessons)
                    return (
                      <td key={col.id}>
                        <button
                          type="button"
                          className={`adm-cell${CELL_CLASS[state] ? ` ${CELL_CLASS[state]}` : ''}`}
                          title={CELL_TITLE[state]}
                          onClick={() => handleCellClick(user.id, col.id, state)}
                        >
                          {(state === 'yes' || state === 'def') && <CheckIcon />}
                          {state === 'part' && '◐'}
                        </button>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {users.length === 0 && (
            <div className="adm-matrix-msg">
              <EmptyState title="No participants in this project yet" hint="Invite people from the People screen." />
            </div>
          )}
        </div>
      )}

      <div className="adm-legend">
        <span className="adm-legend-item">
          <span className="adm-cell adm-cell-yes">
            <CheckIcon />
          </span>{' '}
          assigned
        </span>
        <span className="adm-legend-item">
          <span className="adm-cell adm-cell-def">
            <CheckIcon />
          </span>{' '}
          via project default
        </span>
        <span className="adm-legend-item">
          <span className="adm-cell adm-cell-part">◐</span> partial — narrow the scope for detail
        </span>
        <span className="adm-legend-item">
          <span className="adm-cell" /> not assigned
        </span>
        <span className="adm-legend-spacer">Click a cell to toggle</span>
      </div>
    </div>
  )
}

function initials(name: string): string {
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function CheckIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}
