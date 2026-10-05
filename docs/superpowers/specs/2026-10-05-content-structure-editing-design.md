# Content structure editing: design (B4)

Issue: #145. Bucket B4 of the admin-roles split; builds on the project-scoped admins of
`2026-10-01-project-scoped-admin-design.md` (B1, #93) and the capability panel (B2, #144).

## Why

Every structural content change should be possible in the website. Today tracks and modules can
only be **created**; renaming, reordering, moving, deleting a track, changing a track's level or a
module's prerequisites takes SQL or a script. Editing also happens inside the learner view
(`/learning` edit mode in `frontend/src/pages/LearningPathNew.tsx`, `components/ModulePanel.tsx`),
which Matthias finds "weird and cumbersome". And a lesson added to a module stays invisible to
learners who already have that module until someone replicates its assignments in SQL (authoring
guide §11).

Done when every operation below works in the website with authz and service tests, and no
authoring workflow in `docs/content/` needs SQL for structure.

## Decisions (2026-10-05, Matthias)

1. **A separate Content page in the admin panel**, not the learner view: a tree of
   tracks → modules → lessons with a detail panel for the selected item ("practical to work with"
   is the bar). The `/learning` edit mode stays as is for now; retiring it is a follow-up.
2. **Only power admins edit content.** Tracks, modules and lessons are shared by every project.
3. **Project admins assign their own project's learners to content** — they already can on the
   Assignments page. B4 adds, for them, the "new lessons → assign" action (below), limited to their
   project's learners, on a read-only view of the Content page.
4. **New and moved lessons are not auto-assigned.** A module shows "N lessons not yet assigned" and
   an explicit **Assign** button, pressed when the lesson is ready (a lesson exists from the moment
   "+ Lesson" is clicked, title only). Auto-assign on create and a draft/published status were
   rejected.
5. **Deleting a non-empty track or module is allowed**, after a warning that names the impact
   (modules, lessons, learners with progress). No undo.
6. **The Introduction track is a track like the others**: editable and deletable. With no
   Introduction track, `isIntroComplete` (`frontend/src/lib/learningPathLocks.ts`) is `true`, so
   nothing locks; the lane simply disappears. `is_introduction` stays non-editable.
7. **Prerequisite cycles are refused**: a save that would make a module depend on itself, directly
   or through a chain (A → B → A), fails with a message naming the module. Today nothing stops it,
   and a cycle locks those modules forever.

## The Content page (`/admin/content`)

New sidebar item **Content** (`frontend/src/pages/admin2/nav.ts`), visible to power admins and
project admins. Project admins see the page read-only: no add, edit, move, reorder or delete
controls; only the assign action of decision 3.

**Left: the tree.**

- Rows: track → module → lesson, collapsible. A track row shows `modules · lessons`; a module row
  its lesson count.
- **↑ / ↓ buttons** reorder an item within its parent (keyboard-friendly, no new dependency;
  drag-and-drop is out of scope).
- A filter box narrows the tree by name.
- **+ Track** (top), **+ Module** (inside a track), **+ Lesson** (inside a module).

**Right: the detail panel** for the selected item.

| Item | Fields and actions |
|---|---|
| Track | name, colour, type (`general`/`tool`), required level (any of the four; the field notes that it changes who can open the track), delete |
| Module | title, description, track (**Move to…** appends at the end of that track), prerequisites (checkboxes over all modules, grouped by track), the lessons list, the assignment-gap box, delete |
| Lesson | title, module (**Move to…** appends at the end of that module), **Edit content** (opens the existing lesson editor, `LessonPage` with `?edit=true`), delete |

**Assignment-gap box** (module panel): "*N* lessons not yet assigned — **Assign to the *X*
learners who have this module**". Hidden when the gap is empty. A power admin in the all-projects
scope assigns across all projects; with a project picked in the scope switcher, and always for a
project admin, it covers that project's learners only.

**Deletes**: an in-app two-step confirmation (never `window.confirm`) that spells out the impact,
e.g. "Deletes 3 modules, 21 lessons and the progress of 14 learners".

## Backend

All edits are **power admin** (`require_power_admin`); the project-scoped assign uses
`require_project_in_scope`. Every new route gets a `_MATRIX` row in
`backend/tests/integration/test_routers/test_authz.py`. Logic lives in `ContentService`
(`backend/src/services/content_service.py`), which gains the assignment and user repositories as
constructor arguments: repositories, not services, so "services never call services" holds.

| Action | Endpoint | Guard |
|---|---|---|
| The whole tree with counts | `GET /api/admin/content/tree` | `AdminScopeDep` (power or project admin) |
| Edit track | `PATCH /api/admin/tracks/{track_id}` (`name`, `color`, `track_type`, `required_level`) | power |
| Delete track | `DELETE /api/admin/tracks/{track_id}` | power |
| Reorder tracks | `PUT /api/admin/tracks/order` (full permutation of track ids) | power |
| Edit / move module | `PATCH /api/admin/modules/{module_id}` (`title`, `description`, `track_id`) | power |
| Reorder a track's modules | `PUT /api/admin/tracks/{track_id}/modules/order` (full permutation) | power |
| Set prerequisites | `PUT /api/admin/modules/{module_id}/prerequisites` (`prerequisite_ids`, replaces the set) | power |
| Move lesson | `PATCH /api/admin/lessons/{lesson_id}` gains optional `module_id` | power |
| Delete impact | `GET /api/admin/tracks/{track_id}/impact`, `GET /api/admin/modules/{module_id}/impact` | power |
| Assignment gap, all learners | `GET /api/admin/modules/{module_id}/assignment-gap` | power |
| Assign the gap, all learners | `POST /api/admin/modules/{module_id}/assign-new-lessons` | power |
| Assignment gap, one project | `GET /api/admin/projects/{project_id}/modules/{module_id}/assignment-gap` | `require_project_in_scope` |
| Assign the gap, one project | `POST /api/admin/projects/{project_id}/modules/{module_id}/assign-new-lessons` | `require_project_in_scope` |

Existing create/delete endpoints (`POST /api/admin/tracks`, `/modules`, `/lessons`,
`DELETE …/modules/{id}`, `…/lessons/{id}`, `PUT …/lessons/order`) are reused unchanged.

**Tree response:** tracks in order, each with `id, name, color, track_type, required_level,
is_introduction, sort_order` and its modules in order (`id, title, description, sort_order,
prerequisite_ids, lesson_count`), each with its lessons (`id, title, sort_order`). One call; the
page re-fetches it after each write.

**Impact response:** `{modules, lessons, learners_with_progress, learners_assigned}` (a module's
`modules` is 0). Counts only, no names.

**Gap response:** `{lesson_ids, learner_count, missing_pairs}`, where `learner_count` is the number
of learners who hold the module but miss at least one of its lessons. The assign call returns
`{assigned_pairs}`.

## Rules

- **The assignment gap.** For a module *M* and a set of learners *L* (everyone, or one project's
  learners): the learners in *L* with a `user_modules` row for *M*, crossed with *M*'s lessons,
  minus the existing `user_lessons` rows. Assigning inserts exactly those pairs with
  `assigned_via="manual"` (the Assignments page's stamp) in one transaction. Never removes a row.
  "One project's learners" follows the B1 rule: members of the project, excluding power admins
  and that project's own admins.
- **Move a module to another track.** Appends it at the end of the destination track and closes
  the gap in the source track's order. Assignments and progress are untouched; the module just
  shows in the other lane. Learners assigned the destination *track* do not get the module
  automatically.
- **Move a lesson to another module.** Appends it at the end of the destination module and closes
  the gap in the source. Learners who had it keep it and its progress. In the destination it
  counts toward the assignment gap, so one rule covers new and moved lessons.
- **Delete a track or module.** Cascades through the existing foreign keys (`ondelete=CASCADE`:
  modules → lessons → `user_*` rows and `lesson_progress`; prerequisite links in both directions).
  Remaining siblings are renumbered densely.
- **Prerequisites.** The new set may not contain the module itself, may not contain unknown ids
  (404), and may not create a cycle in the whole graph (`module_prerequisites` edges after the
  change); a cycle raises `InvalidRequestError` naming the module that would depend on itself.
  Cross-track prerequisites stay allowed (the tool tracks' first modules depend on General II).
- **Track type and required level are independent.** `create_track` still derives the initial
  level from the type; after that, editing one never changes the other.
- **Reorders** take a full permutation of the parent's children (as `reorder_lessons` does today;
  anything else → 400 `InvalidRequestError`, the same status as the lesson reorder's `LessonSetMismatchError`) and write `0..n-1` in one transaction.

## Migration (expand-first)

One Alembic revision off the current head:

1. Renumber `tracks.sort_order` globally and `modules.sort_order` per `track_id` to `0..n-1` with
   `ROW_NUMBER() OVER (ORDER BY sort_order, id)`. That is the order every query already uses
   (`content_repository.py`: `order_by(sort_order, id)`), so learners see nothing move.
2. Add deferrable, initially deferred unique constraints `tracks(sort_order)` and
   `modules(track_id, sort_order)`, like the existing `lessons(module_id, sort_order)`.

The running image keeps working on the new schema: `create_track` appends max+1, and
`create_module`'s shift-successors-then-insert only collides mid-transaction, which a deferred
constraint allows. The models declare the same constraints so the metadata-built test schema
matches.

## Frontend

- `frontend/src/pages/admin2/ContentPage.tsx` (tree + panel), routed at `/admin/content`.
- Pure helpers in `frontend/src/lib/contentTree.ts`: filter, ↑/↓ permutation, impact and gap
  labels. Unit-tested next to the file.
- Hooks in `frontend/src/pages/admin2/api.ts` on the typed client; `npm run gen:api` after the
  backend lands.
- Capability check from `adminAccess.ts`: edit controls only for power admins.

## Docs

- `docs/content/authoring-guide.md` §11: the "replicate the assignment set" paragraph becomes
  "press **Assign** on the module in Admin → Content"; structure changes point at the page.
- `docs/feature-index.md` entry; `CLAUDE.md` mention of the Content page where it describes
  editing.

## Testing

- **Service unit tests** (fake repositories): cycle detection (self, two-step, three-step, a
  cross-track chain that is not a cycle), gap computation (all learners, one project, staff
  excluded), move renumbering of source and destination, reorder permutation checks, independent
  type/level edits.
- **Integration tests** per endpoint against Postgres, including the cascade counts of a track
  delete and the project-scoped assign never touching another project's learner.
- **Authz matrix**: `power` for every edit row; `scoped` for the two project-scoped gap routes;
  `scoped_list` for the tree.
- **Migration**: CI's `migrations` job (upgrade → `alembic check` → round-trip), plus a test that
  two tracks tied on `sort_order` keep their `(sort_order, id)` order after renumbering.
- **Frontend**: `contentTree.ts` unit tests; page tests for the power-admin edit flow, the project
  admin's read-only view with the assign button, and the two-step delete.

## Out of scope

- Drag-and-drop reordering.
- A draft/published lesson status.
- Undo or soft delete.
- Retiring the `/learning` edit mode.
- Editor QA and protection against silent overwrites (B5, #146).
- Server-side enforcement of module prerequisites (still a frontend visibility rule).

## Risks

- **Deletes are permanent.** The impact warning is the only guard; the nightly backup is the
  recovery path (`docs/db-backup-restore.md`).
- **Changing a track's required level** changes who can open it server-side (the lesson access
  gate in `learning_service.py::_is_accessible`) immediately for every project.
- **The migration renumbers live rows.** It preserves visible order by construction, but it is a
  write to production data; the CI round-trip and the tie test are the evidence.
