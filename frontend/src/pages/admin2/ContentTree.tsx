import { Fragment } from 'react'
import { resolveTrackColor } from '../../lib/trackColors'
import type { AdminLearningResponseEnriched, Track } from '../../types/domain'
import type { Level } from './AssignmentsPage'

type LearningModule = AdminLearningResponseEnriched['modules'][number]

interface ContentTreeProps {
  /** Assignable (non-introduction) tracks, sorted by `sort_order`. */
  tracks: Track[]
  /** All modules, sorted by `sort_order` (filtered per track for expansion). */
  modules: LearningModule[]
  level: Level
  onSelect: (level: Level) => void
}

/** The content scope tree (spec §3.4): an "All tracks" root plus one item per
 * non-intro track (level-color dot via `resolveTrackColor`); the selected track
 * expands its modules as sub-items. Selecting a node sets the matrix columns.
 * Prototype: docs/design-prototypes/admin-redesign/common.js `treeHTML()`. */
export default function ContentTree({ tracks, modules, level, onSelect }: ContentTreeProps) {
  return (
    <nav className="adm-content-tree">
      <div className="adm-tree-title">Content scope</div>

      <button
        type="button"
        className={`adm-tree-item root${level.level === 'tracks' ? ' active' : ''}`}
        onClick={() => onSelect({ level: 'tracks' })}
      >
        <GridIcon /> All tracks
      </button>

      {tracks.map(track => {
        const open = 'trackId' in level && level.trackId === track.id
        const trackActive = open && level.level === 'modules'
        return (
          <Fragment key={track.id}>
            <button
              type="button"
              className={`adm-tree-item${trackActive ? ' active' : ''}`}
              onClick={() => onSelect({ level: 'modules', trackId: track.id })}
            >
              <span className="adm-tree-dot" style={{ background: resolveTrackColor(track) }} />
              {track.name}
              <span className={`adm-tree-chev${open ? ' open' : ''}`}>
                <ChevronIcon />
              </span>
            </button>
            {open &&
              modules
                .filter(module => module.track_id === track.id)
                .map(module => {
                  const moduleActive = level.level === 'lessons' && level.moduleId === module.id
                  return (
                    <button
                      key={module.id}
                      type="button"
                      className={`adm-tree-item sub${moduleActive ? ' active' : ''}`}
                      onClick={() => onSelect({ level: 'lessons', trackId: track.id, moduleId: module.id })}
                    >
                      {module.title}
                    </button>
                  )
                })}
          </Fragment>
        )
      })}

      <div className="adm-tree-foot">
        Pick a track for its modules,
        <br />a module for its lessons.
      </div>
    </nav>
  )
}

function GridIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x={3} y={3} width={7} height={7} rx={1} />
      <rect x={14} y={3} width={7} height={7} rx={1} />
      <rect x={14} y={14} width={7} height={7} rx={1} />
      <rect x={3} y={14} width={7} height={7} rx={1} />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}
