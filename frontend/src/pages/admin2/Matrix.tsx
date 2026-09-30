import { memo, useCallback, useMemo, useState } from 'react'
import { levelByCode } from '../../lib/levels'
import { resolveTrackColor } from '../../lib/trackColors'
import type { AdminLearningUserEnriched, Track } from '../../types/domain'
import type { AssignmentKind } from './api'
import { useApplyDefaults, useSetDefaults, useToggleAssignment } from './api'
import { EmptyState } from './kit'
import type { Level } from './AssignmentsPage'
import type { CellState, ChildIdIndex, LearningLesson, LearningModule } from './matrixCells'
import { buildChildIdIndex, deriveCellState } from './matrixCells'

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
  const toggleMutate = toggle.mutate
  const setDefaults = useSetDefaults()
  const applyDefaults = useApplyDefaults()
  const [showApplyHint, setShowApplyHint] = useState(false)

  const kind: AssignmentKind =
    level.level === 'tracks' ? 'track' : level.level === 'modules' ? 'module' : 'lesson'

  const childIds = useMemo(() => buildChildIdIndex(modules, lessons), [modules, lessons])

  const trackName = 'trackId' in level ? (tracks.find(t => t.id === level.trackId)?.name ?? '—') : ''
  const moduleName =
    level.level === 'lessons' ? (modules.find(m => m.id === level.moduleId)?.title ?? '—') : ''

  const columns: Column[] = useMemo(() => {
    if (level.level === 'tracks') {
      return tracks.map(track => ({
        id: track.id,
        name: track.name,
        levelName: levelByCode(track.required_level)?.name,
        dotColor: resolveTrackColor(track),
      }))
    }
    if (level.level === 'modules') {
      return modules
        .filter(module => module.track_id === level.trackId)
        .map(module => ({ id: module.id, name: module.title }))
    }
    return lessons
      .filter(lesson => lesson.module_id === level.moduleId)
      .map(lesson => ({ id: lesson.id, name: lesson.title }))
  }, [level, tracks, modules, lessons])

  // Defaults are track-level only. At track scope each column toggles its own
  // default; at module/lesson scope the whole row is read-only and tinted iff
  // the (single) parent track is a default.
  const parentTrackIsDefault = 'trackId' in level && defaultTrackIds.includes(level.trackId)

  // Depend on `toggleMutate`, not `toggle`: TanStack v5 returns a new result object
  // every render and only `mutate` is stable, so `toggle` would defeat MatrixRow's memo.
  const handleCellClick = useCallback(
    (userId: string, itemId: string, state: CellState) => {
      const assigned = !(state === 'yes' || state === 'def')
      toggleMutate({ userId, kind, id: itemId, assigned })
    },
    [toggleMutate, kind],
  )

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
                <MatrixRow
                  key={user.id}
                  user={user}
                  columns={columns}
                  kind={kind}
                  childIds={childIds}
                  onCellClick={handleCellClick}
                />
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

interface MatrixRowProps {
  user: AdminLearningUserEnriched
  columns: Column[]
  kind: AssignmentKind
  childIds: ChildIdIndex
  onCellClick: (userId: string, itemId: string, state: CellState) => void
}

/** One participant row. `memo` is the point: `useToggleAssignment`'s optimistic
 * patch rebuilds only the toggled user's object (`api.ts` `cascadeToggleUser`
 * inside `users.map`), so every other row keeps its identity and skips
 * re-rendering — with `columns`/`childIds`/`onCellClick` all memo-stable above,
 * a click now re-derives one row instead of the whole grid. */
const MatrixRow = memo(function MatrixRow({ user, columns, kind, childIds, onCellClick }: MatrixRowProps) {
  return (
    <tr>
      <td className="adm-matrix-rowhead">
        <div className="adm-user-cell">
          <span className="adm-user-avatar">{initials(`${user.first_name} ${user.last_name}`)}</span>
          <span className="adm-user-name">
            {user.first_name} {user.last_name}
          </span>
        </div>
      </td>
      {columns.map(col => {
        const state = deriveCellState(kind, col.id, user, childIds)
        return (
          <td key={col.id}>
            <button
              type="button"
              className={`adm-cell${CELL_CLASS[state] ? ` ${CELL_CLASS[state]}` : ''}`}
              title={CELL_TITLE[state]}
              onClick={() => onCellClick(user.id, col.id, state)}
            >
              {(state === 'yes' || state === 'def') && <CheckIcon />}
              {state === 'part' && '◐'}
            </button>
          </td>
        )
      })}
    </tr>
  )
})

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
