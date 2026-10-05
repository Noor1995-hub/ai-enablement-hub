import { useMemo, useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { filterTree, moveInList, type TreeTrack } from '../../lib/contentTree'
import { useContentMutation, useContentTree } from './api'
import ContentDetail, { type Selection } from './ContentDetail'
import { Card, EmptyState, ErrorState, Spinner } from './kit'
import { useScope } from './useScope'

/** Admin → Content (spec 2026-10-05, B4): tree of tracks → modules → lessons
 * on the left, the selected item's settings on the right. Power admins edit;
 * project admins read, plus "assign new lessons" for their project. */
export default function ContentPage() {
  const { isPowerAdmin } = useAuth()
  const { projectId } = useScope()
  const tree = useContentTree()
  const mutate = useContentMutation()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState<Set<string>>(new Set())
  const [selection, setSelection] = useState<Selection | null>(null)
  const [newTrack, setNewTrack] = useState('')
  const visible = useMemo(() => filterTree(tree.data ?? [], query), [tree.data, query])

  if (tree.isLoading) return <div className="adm-loading"><Spinner /></div>
  if (tree.error || !tree.data) {
    return <ErrorState message={tree.error?.message ?? 'Failed to load the content.'} onRetry={() => void tree.refetch()} />
  }
  const tracks = tree.data
  const filtering = query.trim() !== ''
  const isOpen = (id: string) => filtering || open.has(id)
  // The name selects and opens; only the arrow collapses (clicking a selected,
  // open track to view its settings must not fold it away).
  const reveal = (id: string) => setOpen(prev => (prev.has(id) ? prev : new Set(prev).add(id)))
  const toggle = (id: string) =>
    setOpen(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  const selected = (kind: Selection['kind'], id: string) => selection?.kind === kind && selection.id === id

  function moveTrack(track: TreeTrack, direction: -1 | 1) {
    const order = moveInList(tracks.map(t => t.id), track.id, direction)
    if (order) mutate.mutate({ kind: 'reorderTracks', trackIds: order })
  }

  return (
    <div>
      <div className="adm-page-head">
        <div>
          <h1 className="adm-page-title">Content</h1>
          <p className="adm-page-sub">
            {isPowerAdmin ? 'Tracks, modules and lessons, shared by every project.' : 'Read-only. You can assign new lessons to your project’s learners.'}
          </p>
        </div>
      </div>

      {mutate.error && <p className="adm-form-msg adm-form-msg-err" role="alert">{mutate.error.message}</p>}

      <div className="adm-content-layout">
        <Card>
          <div className="adm-content-tree-head">
            <input className="adm-field-input" placeholder="Filter by name…" aria-label="Filter by name" value={query} onChange={e => setQuery(e.target.value)} />
          </div>
          {visible.length === 0 ? (
            <EmptyState title="Nothing matches" hint="Try another name." />
          ) : (
            <ul className="adm-content-outline">
              {visible.map(track => (
                <li key={track.id}>
                  <div className={`adm-content-row${selected('track', track.id) ? ' active' : ''}`}>
                    <Disclosure open={isOpen(track.id)} label={track.name} onToggle={() => toggle(track.id)} />
                    <button type="button" className="adm-content-name" onClick={() => { reveal(track.id); setSelection({ kind: 'track', id: track.id }) }}>
                      {track.name}
                    </button>
                    <span className="adm-subtext">{track.modules.length} · {track.modules.reduce((n, m) => n + m.lesson_count, 0)}</span>
                    {isPowerAdmin && !filtering && (
                      <MoveButtons label={track.name} onMove={d => moveTrack(track, d)} />
                    )}
                  </div>
                  {isOpen(track.id) && (
                    <ul>
                      {track.modules.map(module => (
                        <li key={module.id}>
                          <div className={`adm-content-row adm-content-depth-1${selected('module', module.id) ? ' active' : ''}`}>
                            <Disclosure open={isOpen(module.id)} label={module.title} onToggle={() => toggle(module.id)} />
                            <button type="button" className="adm-content-name" onClick={() => { reveal(module.id); setSelection({ kind: 'module', id: module.id }) }}>
                              {module.title}
                            </button>
                            <span className="adm-subtext">{module.lesson_count}</span>
                            {isPowerAdmin && !filtering && (
                              <MoveButtons
                                label={module.title}
                                onMove={d => {
                                  const order = moveInList(track.modules.map(m => m.id), module.id, d)
                                  if (order) mutate.mutate({ kind: 'reorderModules', trackId: track.id, moduleIds: order })
                                }}
                              />
                            )}
                          </div>
                          {isOpen(module.id) && (
                            <ul>
                              {module.lessons.map(lesson => (
                                <li key={lesson.id}>
                                  <div className={`adm-content-row adm-content-depth-2${selected('lesson', lesson.id) ? ' active' : ''}`}>
                                    <button type="button" className="adm-content-name" onClick={() => setSelection({ kind: 'lesson', id: lesson.id })}>
                                      {lesson.title}
                                    </button>
                                    {isPowerAdmin && !filtering && (
                                      <MoveButtons
                                        label={lesson.title}
                                        onMove={d => {
                                          const order = moveInList(module.lessons.map(l => l.id), lesson.id, d)
                                          if (order) mutate.mutate({ kind: 'reorderLessons', moduleId: module.id, lessonIds: order })
                                        }}
                                      />
                                    )}
                                  </div>
                                </li>
                              ))}
                              {isPowerAdmin && (
                                <li><AddInline label="+ Lesson" onAdd={title => mutate.mutate({ kind: 'createLesson', moduleId: module.id, title })} /></li>
                              )}
                            </ul>
                          )}
                        </li>
                      ))}
                      {isPowerAdmin && (
                        <li><AddInline label="+ Module" onAdd={title => mutate.mutate({ kind: 'createModule', body: { track_id: track.id, title, prerequisite_ids: [] } })} /></li>
                      )}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
          {isPowerAdmin && (
            <div className="adm-content-add-track">
              <input className="adm-field-input" placeholder="New track name" aria-label="New track name" value={newTrack} onChange={e => setNewTrack(e.target.value)} />
              <button
                type="button"
                className="adm-btn adm-btn-ghost adm-btn-sm"
                disabled={newTrack.trim() === ''}
                onClick={() => { mutate.mutate({ kind: 'createTrack', body: { name: newTrack.trim(), track_type: 'general' } }); setNewTrack('') }}
              >
                + Track
              </button>
            </div>
          )}
        </Card>

        <Card>
          {selection ? (
            <ContentDetail selection={selection} tree={tracks} canEdit={isPowerAdmin} projectId={projectId} onSelect={setSelection} />
          ) : (
            <EmptyState title="Pick something on the left" hint="A track, module or lesson." />
          )}
        </Card>
      </div>
    </div>
  )
}

function Disclosure({ open, label, onToggle }: { open: boolean; label: string; onToggle: () => void }) {
  return (
    <button type="button" className="adm-content-disclosure" aria-expanded={open} aria-label={`${open ? 'Collapse' : 'Expand'} ${label}`} onClick={onToggle}>
      <span aria-hidden="true">{open ? '▾' : '▸'}</span>
    </button>
  )
}

function MoveButtons({ label, onMove }: { label: string; onMove: (direction: -1 | 1) => void }) {
  return (
    <span className="adm-content-move">
      <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" aria-label={`Move ${label} up`} onClick={() => onMove(-1)}>↑</button>
      <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" aria-label={`Move ${label} down`} onClick={() => onMove(1)}>↓</button>
    </span>
  )
}

function AddInline({ label, onAdd }: { label: string; onAdd: (title: string) => void }) {
  const [title, setTitle] = useState('')
  const [adding, setAdding] = useState(false)
  if (!adding) {
    return <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm adm-content-depth-1" onClick={() => setAdding(true)}>{label}</button>
  }
  return (
    <form
      className="adm-content-add"
      onSubmit={e => {
        e.preventDefault()
        if (!title.trim()) return
        onAdd(title.trim())
        setTitle('')
        setAdding(false)
      }}
    >
      <input className="adm-field-input" autoFocus aria-label={`${label} title`} value={title} onChange={e => setTitle(e.target.value)} />
      <button type="submit" className="adm-btn adm-btn-ghost adm-btn-sm">Add</button>
      <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" onClick={() => setAdding(false)}>Cancel</button>
    </form>
  )
}
