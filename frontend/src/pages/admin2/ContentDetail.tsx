import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { gapLabel, impactLabel, type TreeModule, type TreeTrack } from '../../lib/contentTree'
import { useAssignmentGap, useContentMutation, useModuleImpact, useTrackImpact } from './api'
import { ConfirmButton } from './kit'

export type Selection = { kind: 'track'; id: string } | { kind: 'module'; id: string } | { kind: 'lesson'; id: string }

interface Props {
  selection: Selection
  tree: TreeTrack[]
  canEdit: boolean
  projectId: string | null
  onSelect: (selection: Selection | null) => void
}

const LEVELS = ['explore', 'practitioner', 'integrator', 'multiplier'] as const

/** The right-hand panel of Admin → Content: the selected track, module or lesson. */
export default function ContentDetail({ selection, tree, canEdit, projectId, onSelect }: Props) {
  const modules = tree.flatMap(t => t.modules.map(m => ({ ...m, trackId: t.id, trackName: t.name })))
  if (selection.kind === 'track') {
    const track = tree.find(t => t.id === selection.id)
    return track ? <TrackPanel key={track.id} track={track} canEdit={canEdit} onDeleted={() => onSelect(null)} /> : null
  }
  if (selection.kind === 'module') {
    const module = modules.find(m => m.id === selection.id)
    return module ? (
      <ModulePanel key={module.id} module={module} trackId={module.trackId} tree={tree} canEdit={canEdit} projectId={projectId} onDeleted={() => onSelect(null)} />
    ) : null
  }
  const owner = modules.find(m => m.lessons.some(l => l.id === selection.id))
  const lesson = owner?.lessons.find(l => l.id === selection.id)
  return owner && lesson ? (
    <LessonPanel key={lesson.id} lesson={lesson} moduleId={owner.id} modules={modules} canEdit={canEdit} onDeleted={() => onSelect(null)} />
  ) : null
}

function TrackPanel({ track, canEdit, onDeleted }: { track: TreeTrack; canEdit: boolean; onDeleted: () => void }) {
  const mutate = useContentMutation()
  const impact = useTrackImpact(canEdit ? track.id : null)
  const [name, setName] = useState(track.name)
  const [color, setColor] = useState(track.color ?? '')
  const [type, setType] = useState(track.track_type)
  const [level, setLevel] = useState(track.required_level)
  // Reset to the saved values only when they change: a refetch (any mutation,
  // a window refocus) hands us a new object and must not wipe unsaved typing.
  useEffect(() => {
    setName(track.name); setColor(track.color ?? ''); setType(track.track_type); setLevel(track.required_level)
  }, [track.id, track.name, track.color, track.track_type, track.required_level])

  return (
    <section aria-label={track.name} className="adm-content-detail">
      <h2 className="adm-card-title">Track: {track.name}</h2>
      <MutationError error={mutate.error} />
      {canEdit ? (
        <>
          <Field id="track-name" label="Name"><input id="track-name" className="adm-field-input" value={name} onChange={e => setName(e.target.value)} /></Field>
          <Field id="track-color" label="Colour"><input id="track-color" className="adm-field-input" value={color} placeholder="#3BC9BC" onChange={e => setColor(e.target.value)} /></Field>
          <Field id="track-type" label="Type">
            <select id="track-type" className="adm-field-input" value={type} onChange={e => setType(e.target.value)}>
              <option value="general">General</option>
              <option value="tool">Tool</option>
            </select>
          </Field>
          <Field id="track-level" label="Required level">
            <select id="track-level" className="adm-field-input" value={level} onChange={e => setLevel(e.target.value)}>
              {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </Field>
          <p className="adm-hint">Changing the level changes who can open this track, in every project, straight away.</p>
          <div className="adm-content-actions">
            <button
              type="button"
              className="adm-btn adm-btn-red"
              disabled={!name.trim() || mutate.isPending}
              onClick={() => mutate.mutate({
                kind: 'updateTrack',
                trackId: track.id,
                body: { name: name.trim(), color: color.trim() || null, track_type: type as 'general' | 'tool', required_level: level as (typeof LEVELS)[number] },
              })}
            >
              Save
            </button>
          </div>
          <DangerZone label="Delete track" impact={impact.data ? impactLabel(impact.data) : null} busy={mutate.isPending}
            onConfirm={() => mutate.mutate({ kind: 'deleteTrack', trackId: track.id }, { onSuccess: onDeleted })} />
        </>
      ) : (
        <p className="adm-hint">{track.track_type} · {track.required_level} · {track.modules.length} modules</p>
      )}
    </section>
  )
}

function ModulePanel({ module, trackId, tree, canEdit, projectId, onDeleted }: {
  module: TreeModule; trackId: string; tree: TreeTrack[]; canEdit: boolean; projectId: string | null; onDeleted: () => void
}) {
  const mutate = useContentMutation()
  const impact = useModuleImpact(canEdit ? module.id : null)
  const gap = useAssignmentGap(module.id, projectId)
  const [title, setTitle] = useState(module.title)
  const [description, setDescription] = useState(module.description ?? '')
  const [prereqs, setPrereqs] = useState<Set<string>>(new Set(module.prerequisite_ids))
  const savedPrereqs = module.prerequisite_ids.join(',')
  // As in TrackPanel: reset on saved-value changes only, never on a bare refetch.
  useEffect(() => {
    setTitle(module.title); setDescription(module.description ?? ''); setPrereqs(new Set(savedPrereqs ? savedPrereqs.split(',') : []))
  }, [module.id, module.title, module.description, savedPrereqs])
  const gapText = gap.data ? gapLabel(gap.data) : null

  return (
    <section aria-label={module.title} className="adm-content-detail">
      <h2 className="adm-card-title">Module: {module.title}</h2>
      <MutationError error={mutate.error} />

      {gapText && gap.data && (
        <div className="adm-note-banner">
          <p>{gapText}</p>
          <button
            type="button"
            className="adm-btn adm-btn-red adm-btn-sm"
            disabled={mutate.isPending}
            onClick={() => mutate.mutate({ kind: 'assignGap', moduleId: module.id, projectId })}
          >
            Assign to the {gap.data.learner_count} learner{gap.data.learner_count === 1 ? '' : 's'}
          </button>
        </div>
      )}

      {canEdit ? (
        <>
          <Field id="module-title" label="Title"><input id="module-title" className="adm-field-input" value={title} onChange={e => setTitle(e.target.value)} /></Field>
          <Field id="module-description" label="Description">
            <textarea id="module-description" className="adm-field-input" rows={3} value={description} onChange={e => setDescription(e.target.value)} />
          </Field>
          <Field id="module-track" label="Track">
            <select
              id="module-track"
              className="adm-field-input"
              value={trackId}
              onChange={e => mutate.mutate({ kind: 'updateModule', moduleId: module.id, body: { track_id: e.target.value } })}
            >
              {tree.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </Field>
          <div className="adm-content-actions">
            <button
              type="button"
              className="adm-btn adm-btn-red"
              disabled={!title.trim() || mutate.isPending}
              onClick={() => mutate.mutate({ kind: 'updateModule', moduleId: module.id, body: { title: title.trim(), description: description.trim() || null } })}
            >
              Save
            </button>
          </div>

          <fieldset className="adm-content-prereqs">
            <legend>Unlocks after</legend>
            {tree.map(t => (
              <div key={t.id}>
                <div className="adm-subtext">{t.name}</div>
                {t.modules.filter(m => m.id !== module.id).map(m => (
                  <label key={m.id} className="adm-check-row">
                    <input
                      type="checkbox"
                      checked={prereqs.has(m.id)}
                      onChange={() => setPrereqs(prev => {
                        const next = new Set(prev)
                        if (next.has(m.id)) next.delete(m.id)
                        else next.add(m.id)
                        return next
                      })}
                    />
                    {m.title}
                  </label>
                ))}
              </div>
            ))}
            <button
              type="button"
              className="adm-btn adm-btn-ghost adm-btn-sm"
              disabled={mutate.isPending}
              onClick={() => mutate.mutate({ kind: 'setPrerequisites', moduleId: module.id, prerequisiteIds: [...prereqs] })}
            >
              Save prerequisites
            </button>
          </fieldset>

          <DangerZone label="Delete module" impact={impact.data ? impactLabel(impact.data) : null} busy={mutate.isPending}
            onConfirm={() => mutate.mutate({ kind: 'deleteModule', moduleId: module.id }, { onSuccess: onDeleted })} />
        </>
      ) : (
        <p className="adm-hint">{module.lesson_count} lessons</p>
      )}
    </section>
  )
}

function LessonPanel({ lesson, moduleId, modules, canEdit, onDeleted }: {
  lesson: { id: string; title: string }
  moduleId: string
  modules: (TreeModule & { trackName: string })[]
  canEdit: boolean
  onDeleted: () => void
}) {
  const mutate = useContentMutation()
  const [title, setTitle] = useState(lesson.title)
  useEffect(() => setTitle(lesson.title), [lesson.id, lesson.title])

  return (
    <section aria-label={lesson.title} className="adm-content-detail">
      <h2 className="adm-card-title">Lesson: {lesson.title}</h2>
      <MutationError error={mutate.error} />
      {canEdit && (
        <>
          <Link className="adm-btn adm-btn-ghost adm-btn-sm" to={`/learning/lesson/${lesson.id}?edit=true`}>Edit content</Link>
          <Field id="lesson-title" label="Title"><input id="lesson-title" className="adm-field-input" value={title} onChange={e => setTitle(e.target.value)} /></Field>
          <Field id="lesson-module" label="Module">
            <select
              id="lesson-module"
              className="adm-field-input"
              value={moduleId}
              onChange={e => mutate.mutate({ kind: 'updateLesson', lessonId: lesson.id, body: { module_id: e.target.value } })}
            >
              {modules.map(m => <option key={m.id} value={m.id}>{m.trackName} · {m.title}</option>)}
            </select>
          </Field>
          <p className="adm-hint">Moving keeps its learners. Learners of the new module get it when you press Assign there.</p>
          <div className="adm-content-actions">
            <button type="button" className="adm-btn adm-btn-red" disabled={!title.trim() || mutate.isPending}
              onClick={() => mutate.mutate({ kind: 'updateLesson', lessonId: lesson.id, body: { title: title.trim() } })}>
              Save
            </button>
          </div>
          <DangerZone label="Delete lesson" impact={null} busy={mutate.isPending}
            onConfirm={() => mutate.mutate({ kind: 'deleteLesson', lessonId: lesson.id }, { onSuccess: onDeleted })} />
        </>
      )}
    </section>
  )
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className="adm-field">
      <label className="adm-field-label" htmlFor={id}>{label}</label>
      {children}
    </div>
  )
}

function DangerZone({ label, impact, busy, onConfirm }: { label: string; impact: string | null; busy: boolean; onConfirm: () => void }) {
  return (
    <div className="adm-content-danger">
      {impact && <p className="adm-form-msg adm-form-msg-err">{impact}</p>}
      <ConfirmButton label={label} confirmLabel="Yes, delete" onConfirm={onConfirm} busy={busy} />
    </div>
  )
}

/** A refused save (e.g. a prerequisite cycle) must be visible, not a silent revert. */
function MutationError({ error }: { error: Error | null }) {
  return error ? <p className="adm-form-msg adm-form-msg-err" role="alert">{error.message}</p> : null
}
