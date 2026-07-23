# Participant Inline Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the admin Participants table's fixed right-side slide-out panel with an inline, accordion-style expansion directly under the clicked participant's row.

**Architecture:** `Admin.tsx` keeps owning all the detail-panel state and data fetching (it's the documented data-orchestrator for this page); only the *rendering location* moves. `ProjectDetailView.tsx` renders the detail content inline (reusing the `React.Fragment` + conditional `<tr><td colSpan={7}>` pattern it already uses for the reset-link row) instead of `Admin.tsx` rendering a fixed-overlay `<UserPanel>` as a sibling of the table. `UserPanel.tsx` is stripped of its overlay/header chrome and renamed `ParticipantDetail.tsx` since it's no longer a "panel."

**Tech Stack:** React 18 + TypeScript (Vite), plain inline `style={}` objects (`adminStyles.ts`'s `s` object) — no CSS framework in this codebase.

## Global Constraints

- **No test framework exists for this frontend** (confirmed: no `*.test.*`/`*.spec.*` files under `frontend/src`). The project's real verification gate, used for every prior admin-UI change, is `npm run typecheck && npm run lint && npm run build` (run inside `frontend/`) plus manual browser verification — do not introduce a new test framework as part of this change.
- Frontend checks command (run after every task, inside `frontend/`): `npm run typecheck && npm run lint && npm run build`.
- Spec: `docs/superpowers/specs/2026-07-23-participant-inline-detail-design.md` — behavior contract for accordion semantics (one row open at a time), full-width layout, and "no separate close button" (chevron/name-click only).
- One deliberate deviation from the spec's literal prop list, called out in Task 2: `Admin.tsx`'s `panelUserData` state is dropped entirely rather than threaded through. It existed only to hand `UserPanel` a copy of the clicked user's data — but `ProjectDetailView.tsx` already holds that exact same `AdminUser` object in its `projectUsers` row loop (the `u` in `projectUsers.map(u => ...)`), so passing `user={u}` directly into the new inline `<ParticipantDetail>` is a strict simplification: one fewer state variable, and the "keep `panelUserData` in sync with `projectUsers` on every maturity update" duplication in `handleSetMaturity` goes away. Nothing in the spec's behavior contract depends on `panelUserData` being a separate value.
- A second minor deviation: the spec suggested adding a new named style to `adminStyles.ts` for the inline expansion's `<td>` container. Task 2 instead writes that padding/border inline in the JSX, matching how the existing reset-link row (the direct precedent for this whole mechanic) already does it — that row's container style has never lived in `adminStyles.ts` either. Same visual result, more consistent with the file's existing convention.

---

### Task 1: Create `ParticipantDetail.tsx` (repurposed, un-chromed `UserPanel.tsx`)

**Files:**
- Create: `frontend/src/pages/admin/ParticipantDetail.tsx`
- Read for reference (not modified this task): `frontend/src/pages/admin/UserPanel.tsx`

**Interfaces:**
- Produces: `ParticipantDetail` (default export), `ParticipantDetailProps` — identical to today's `UserPanelProps` (in `UserPanel.tsx`) **minus `onClose: () => void`**. Props: `user: AdminUser | null`, `survey: AdminSurvey | null | undefined`, `loadingPanel: boolean`, `learningUser: AdminLearningUser | null`, `tracks: Track[]`, `learningData: AdminLearning`, `togglingItem: string | null`, `savingMaturity: boolean`, `onToggleLearning: (action: 'track' | 'module' | 'lesson', userId: string, itemId: string, currentlyAssigned: boolean) => void`, `onBulkAssign: (kind: 'tracks' | 'modules' | 'lessons', userId: string, groupId: string, ids: string[], assigned: boolean) => void`, `onSetMaturity: (userId: string, level: string | null) => void`.
- Behavior is otherwise byte-for-byte identical to `UserPanel.tsx`'s body content (survey results, maturity box, track/module/lesson accordions) — only the overlay wrapper, the header (name/email/close button), and the `onClose` prop are removed. `UserPanel.tsx` itself is untouched by this task (deleted in Task 2, once nothing imports it).

- [ ] **Step 1: Create the new file with the un-chromed component**

Write `frontend/src/pages/admin/ParticipantDetail.tsx`:

```tsx
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
  marginTop: 18, padding: '14px 16px', background: '#FAFAF9',
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
            A pin sets the starting level; finishing a level’s modules still advances it.
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
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0' }}>
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
```

- [ ] **Step 2: Run frontend checks**

Run (inside `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all three pass. The new file is not imported anywhere yet, so this only proves it's self-consistent (correct types, no lint violations) — nothing else in the app changes behavior yet.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/ParticipantDetail.tsx
git commit -m "Add ParticipantDetail component (un-chromed UserPanel content)"
```

---

### Task 2: Wire the inline expansion through `ProjectDetailView.tsx` + `Admin.tsx`, retire `UserPanel.tsx`

**Files:**
- Modify: `frontend/src/pages/admin/ProjectDetailView.tsx`
- Modify: `frontend/src/pages/Admin.tsx`
- Modify: `frontend/src/pages/admin/adminStyles.ts`
- Delete: `frontend/src/pages/admin/UserPanel.tsx`

**Interfaces:**
- Consumes: `ParticipantDetail` / `ParticipantDetailProps` from Task 1 (`frontend/src/pages/admin/ParticipantDetail.tsx`).
- Produces: `ProjectDetailView`'s new `panel` prop (type `UserDetailPanelProps`, defined in this task) and renamed `handlers.onToggleUserPanel` — both are used only by `Admin.tsx`, which this same task updates, so nothing outside this task depends on these names.

- [ ] **Step 1: Add the `panel` prop group and imports to `ProjectDetailView.tsx`**

In `frontend/src/pages/admin/ProjectDetailView.tsx`, change the type imports (currently line 4):

```tsx
import type { AdminLearning, AdminLearningUser, AdminSurvey, AdminUser, ComponentState, EmailStatus, Track } from '../../types/domain'
```

Add a new import for the detail component (after the existing `EmailTemplatesCard` import, currently line 9):

```tsx
import EmailTemplatesCard from './EmailTemplatesCard'
import ParticipantDetail from './ParticipantDetail'
```

Add a new prop-group interface, right after the existing `Handlers` interface (currently lines 51–62):

```tsx
interface UserDetailPanelProps {
  expandedUserId: string | null
  survey: AdminSurvey | null | undefined
  loading: boolean
  learningUser: AdminLearningUser | null
  tracks: Track[]
  learningData: AdminLearning
  togglingItem: string | null
  savingMaturity: boolean
  onToggleLearning: (action: 'track' | 'module' | 'lesson', userId: string, itemId: string, currentlyAssigned: boolean) => void
  onBulkAssign: (kind: 'tracks' | 'modules' | 'lessons', userId: string, groupId: string, ids: string[], assigned: boolean) => void
  onSetMaturity: (userId: string, level: string | null) => void
}
```

Update the `Handlers` interface: replace

```tsx
  onOpenUserPanel: (user: AdminUser) => void
```

with

```tsx
  onToggleUserPanel: (user: AdminUser) => void
```

Add `panel: UserDetailPanelProps` to `ProjectDetailViewProps` (currently lines 64–69):

```tsx
interface ProjectDetailViewProps {
  project: SelectedProject
  participants: ParticipantsProps
  componentAccess: ComponentAccessProps
  panel: UserDetailPanelProps
  handlers: Handlers
}
```

- [ ] **Step 2: Destructure the new prop and update the component signature**

Update the function signature (currently lines 78–83):

```tsx
export default function ProjectDetailView({
  project,
  participants,
  componentAccess,
  panel,
  handlers,
}: ProjectDetailViewProps) {
```

Add a destructure for `panel` right after the existing `componentAccess` destructure (currently lines 89–92):

```tsx
  const {
    expandedUserId, survey: panelSurvey, loading: loadingPanel, learningUser: panelLearningUser,
    tracks: panelTracks, learningData: panelLearningData, togglingItem: panelTogglingItem,
    savingMaturity: panelSavingMaturity, onToggleLearning, onBulkAssign, onSetMaturity,
  } = panel
```

Update the `handlers` destructure (currently lines 94–98): replace `onOpenUserPanel` with `onToggleUserPanel`:

```tsx
  const {
    onBack, onToggleComponent, onRoleChange, onDelete, onSetConfirmDelete,
    onGenerateResetLink, onCopyResetLink, onDismissResetLink, onToggleUserPanel,
    onProjectRefresh,
  } = handlers
```

- [ ] **Step 3: Add the chevron and switch the click handler on the name button**

Replace the name button block (currently lines 272–279):

```tsx
                    <td style={{ ...s.td, ...s.tdName }}>
                      <button
                        type="button"
                        style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', fontWeight: 700, fontSize: 14, color: '#101820', textDecoration: 'underline', textDecorationColor: '#E2E2E2', fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 6 }}
                        onClick={() => onToggleUserPanel(u)}
                      >
                        {u.first_name} {u.last_name}
                        <span style={{ fontSize: 9, color: '#B6B6B6', textDecoration: 'none' }}>
                          {expandedUserId === u.id ? '▼' : '▶'}
                        </span>
                      </button>
                    </td>
```

- [ ] **Step 4: Add the inline expansion row**

In the same `React.Fragment` (currently lines 270–368), immediately after the main `<tr>` closes and before the existing `{resetLinks[u.id] && (...)}` block, add a new conditional row:

```tsx
                  </tr>
                  {expandedUserId === u.id && (
                    <tr>
                      <td colSpan={7} style={{ padding: '0 24px 28px', borderBottom: '1px solid #F5F5F5' }}>
                        <ParticipantDetail
                          user={u}
                          survey={panelSurvey}
                          loadingPanel={loadingPanel}
                          learningUser={panelLearningUser}
                          tracks={panelTracks}
                          learningData={panelLearningData}
                          togglingItem={panelTogglingItem}
                          savingMaturity={panelSavingMaturity}
                          onToggleLearning={onToggleLearning}
                          onBulkAssign={onBulkAssign}
                          onSetMaturity={onSetMaturity}
                        />
                      </td>
                    </tr>
                  )}
                  {resetLinks[u.id] && (
```

(The existing `</tr>` that used to directly precede `{resetLinks[u.id] && (` is now followed by the new block above instead — the rest of the `resetLinks` block is unchanged.)

- [ ] **Step 5: Remove `UserPanel.tsx` and its dead styles**

Delete the file: `frontend/src/pages/admin/UserPanel.tsx`.

In `frontend/src/pages/admin/adminStyles.ts`, remove the six now-unused entries from the `/* user detail panel */` section (currently lines 196–218) — `panelOverlay`, `panel`, `panelHeader`, `panelClose`, `panelName`, `panelMeta` — leaving only the three still-used ones:

```tsx
  /* user detail panel */
  panelBody: { padding: '24px 28px', flex: 1 },
  panelSection: { marginBottom: 32 },
  panelSectionTitle: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8A8A8A', marginBottom: 14,
  },
```

- [ ] **Step 6: Update `Admin.tsx` — drop `panelUserData`, add toggle semantics, stop rendering the fixed panel**

Remove the `UserPanel` import (currently line 19):

```tsx
import UserPanel from './admin/UserPanel'
```

Remove the `panelUserData` state declaration (currently line 40):

```tsx
  const [panelUserData, setPanelUserData] = useState<AdminUser | null>(null)
```

In `openProject` (currently lines 140–148), remove the `setPanelUserData(null)` line:

```tsx
  function openProject(project: ProjectOut, companyName: string) {
    setSelectedProject({ ...project, company_name: companyName })
    setPanelUserId(null)
    setPanelSurvey(undefined)
    setResetLinks({})
    setActionError(null)
    loadProjectData(project.id)
  }
```

Replace `openUserPanel` (currently lines 155–168) with a toggling `toggleUserPanel`:

```tsx
  /* ── user detail panel ── */
  async function toggleUserPanel(panelUser: AdminUser) {
    if (panelUserId === panelUser.id) {
      setPanelUserId(null)
      return
    }
    setPanelUserId(panelUser.id)
    setPanelSurvey(undefined)
    setLoadingPanel(true)
    try {
      const { data } = await client.GET('/api/admin/surveys/{user_id}', {
        params: { path: { user_id: panelUser.id } },
      })
      setPanelSurvey(data ? data.survey : null)
    } catch { setPanelSurvey(null) }
    setLoadingPanel(false)
  }
```

In `handleSetMaturity` (currently lines 296–332), remove every `panelUserData` reference — the optimistic update and reconciliation only need `projectUsers` now, since `ProjectDetailView` passes `user={u}` (the `projectUsers` row) straight into `ParticipantDetail`:

```tsx
  /* ── maturity override (modelled on handleRoleToggle) ── */
  async function handleSetMaturity(userId: string, level: string | null) {
    const prevUsers = projectUsers
    setSavingMaturity(true)
    // Optimistically reflect the pin (effective follows on the reconcile below).
    const applyOverride = (u: AdminUser): AdminUser => ({
      ...u, maturity_override: level, effective_maturity: level ?? u.effective_maturity,
    })
    setProjectUsers(prev => prev.map(u => (u.id === userId ? applyOverride(u) : u)))
    try {
      const { error } = await client.PUT('/api/admin/users/{user_id}/maturity', {
        params: { path: { user_id: userId } },
        body: { level: level as 'explore' | 'practitioner' | 'integrator' | 'multiplier' | null },
      })
      if (error) {
        setProjectUsers(prevUsers)
        setActionError(errorMessage(error, 'Failed to update maturity level.'))
      } else if (selectedProject) {
        // Reconcile effective_maturity authoritatively — completion can raise it
        // above the pin, and clearing falls back to assessment + earned progression.
        const { data } = await client.GET('/api/admin/users', {
          params: { query: { project_id: selectedProject.id } },
        })
        if (data) setProjectUsers(data.users)
      }
    } catch {
      setProjectUsers(prevUsers)
      setActionError('Network error.')
    }
    setSavingMaturity(false)
  }
```

Update the `<ProjectDetailView>` call (currently lines 415–448) to add the `panel` prop and rename the handler:

```tsx
          <ProjectDetailView
            project={selectedProject}
            participants={{
              users: projectUsers,
              loading: loadingProjectUsers,
              error: projectUsersError,
              surveyLevels,
              togglingRole,
              generatingReset,
              resetLinks,
              confirmDelete,
              deleting,
            }}
            componentAccess={{
              data: projectComponents,
              loading: loadingComponents,
              error: componentError,
              toggling: togglingComponent,
            }}
            panel={{
              expandedUserId: panelUserId,
              survey: panelSurvey,
              loading: loadingPanel,
              learningUser: panelLearningUser,
              tracks,
              learningData,
              togglingItem,
              savingMaturity,
              onToggleLearning: toggleLearningItem,
              onBulkAssign: bulkAssignLearningItems,
              onSetMaturity: handleSetMaturity,
            }}
            handlers={{
              onBack: closeProject,
              onToggleComponent: toggleComponent,
              onRoleChange: handleRoleChange,
              onDelete: handleDelete,
              onSetConfirmDelete: setConfirmDelete,
              onGenerateResetLink: handleGenerateResetLink,
              onCopyResetLink: copyResetLink,
              onDismissResetLink: userId => setResetLinks(prev => { const n = { ...prev }; delete n[userId]; return n }),
              onToggleUserPanel: toggleUserPanel,
              onProjectRefresh: () => loadProjectData(selectedProject.id),
            }}
          />
```

Remove the fixed panel render block at the bottom of the component (currently lines 459–475):

```tsx
      {/* ── User detail panel ── */}
      {panelUserId && (
        <UserPanel
          user={panelUserData}
          survey={panelSurvey}
          loadingPanel={loadingPanel}
          learningUser={panelLearningUser}
          tracks={tracks}
          learningData={learningData}
          togglingItem={togglingItem}
          savingMaturity={savingMaturity}
          onToggleLearning={toggleLearningItem}
          onBulkAssign={bulkAssignLearningItems}
          onSetMaturity={handleSetMaturity}
          onClose={() => setPanelUserId(null)}
        />
      )}
```

— so the component's JSX now ends with the closing `</main>` tag followed directly by the closing `</div>` of the root `<div style={s.page}>`.

- [ ] **Step 7: Run frontend checks**

Run (inside `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all three pass, with zero references to `UserPanel`/`panelUserData`/`onOpenUserPanel` remaining anywhere in `frontend/src`. Confirm with:

```bash
grep -rn "UserPanel\|panelUserData\|onOpenUserPanel" frontend/src
```

Expected: no output.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/admin/ProjectDetailView.tsx frontend/src/pages/Admin.tsx frontend/src/pages/admin/adminStyles.ts
git rm frontend/src/pages/admin/UserPanel.tsx
git commit -m "Move participant detail from slide-out panel to inline row expansion"
```

---

### Task 3: Manual browser verification

**Files:** none (verification only).

- [ ] **Step 1: Start the dev servers**

Run (inside `backend/`): `uv run poe dev` (leave running).
Run (inside `frontend/`): `npm run dev` (leave running, → http://localhost:5173).

- [ ] **Step 2: Walk through the accordion behavior**

In the browser, sign in as an admin, go to `/admin` → open a project with at least two participants who have completed an assessment. Verify:
- Clicking a participant's name expands their details (Assessment results, Maturity level, Track assignment) directly under their row, full table width, with the chevron flipping to ▼. No overlay/backdrop appears and the rest of the page (other rows) stays visible below the expanded content.
- Clicking a *different* participant's name collapses the first row and expands the new one (only one open at a time).
- Clicking the *same* (already-expanded) participant's name again collapses it, chevron flips back to ▶.
- With a row expanded, click "reset link" on that same row — confirm the reset-link box appears too and both stay visible together (independent of the detail expansion, per the design's out-of-scope note).

- [ ] **Step 3: Confirm existing panel functionality still works inline**

With a row expanded:
- Change the maturity pin dropdown — confirm the badge updates immediately and stays correct if you then close and reopen the row.
- Expand a track's modules, then a module's lessons, and toggle a lesson's assignment — confirm it updates without closing the outer row.
- Click "+ add all tracks" / "− unassign all" — confirm bulk assignment still works.

- [ ] **Step 4: Report results**

Summarize pass/fail for each check above. If anything fails, treat it as a bug against Task 2's changes (not a new task) and fix before considering this plan complete.
