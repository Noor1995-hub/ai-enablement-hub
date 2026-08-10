# Admin Panel Redesign — Design

**Date:** 2026-07-23 · **Status:** approved design, pending implementation plan
**Stakeholders:** Aaron (design owner), Matthias (backend sign-off given 2026-07-23)

## 1. Context & goals

The admin panel works but is an MVP: a single `/admin` route with two in-memory tabs,
a 478-line god component (`Admin.tsx`, "A1 noted, deferred"), inline-`CSSProperties`
styling, hand-rolled fetch state, and no pagination. Three admin pains drive this
redesign, in priority order:

1. **Assignment of tracks/modules/lessons is the #1 pain** — strictly per-user, buried
   in a narrow slide-over (`UserPanel.tsx`), repetitive for every new participant.
2. **No overview** — no way to see project health, stuck learners, or incoming feedback
   at a glance.
3. **Looks unfinished** — no design system; dense hand-built tables and literal-string
   loading states.

**Audience:** delaware people only (Aaron + Matthias now, extensible to colleagues).
**Out of scope:** content authoring (LearningPath edit mode, LessonEditor, `?edit=true`)
stays as-is on the learner pages; roles/auth model unchanged; AI feedback triage parked
(see §8).

**Design process:** the UX was iterated as clickable HTML mockups over five rounds
(2026-07-23, all approved). The mockups are the **visual contract** for implementation:
`scratch_review/admin_redesign_prototypes/` — `option-b.html` is the target design;
`index.html` documents the rounds; `option-a.html` is a rejected alternative kept for
reference. (scratch_review is git-untracked; promote the prototype folder into
`docs/design-prototypes/admin-redesign/` when this spec is committed so the contract
is versioned.)

## 2. Information architecture

**Function-first sidebar** (mockup "Option B"), chosen over a project-centric workspace
in a side-by-side comparison round:

| Section | Purpose |
|---|---|
| Dashboard | Cross-project (or scoped) tiles, needs-attention list, per-project funnels |
| People | Participants table + bulk actions + invite; row click → **user detail page** |
| Assignments | Full-width users × content matrix with project-defaults row and a track→module→lesson scope tree |
| Feedback | Triage queue (accept/dismiss) with structured location and filters |
| Projects | Per-project settings: component access, links to scoped sections |
| Email templates | Per-project invite/reset template editor (existing feature, first-class home) |
| Setup | Create companies and projects |

**Global scope switcher ("Viewing")** — the navigation anchor. Lives permanently in the
top bar next to the logo: `All projects` or one `Company · Project`. When scoped it is
red-tinted with an ✕ to clear; the scope follows the admin through every section.
Assignments and Email templates *require* a scope (unscoped they show a company picker);
Dashboard/People/Feedback filter by it.

**Company-first naming** everywhere: chips and cards lead with the company name (what
people recognize); the project name qualifies it (`Nova Foods Group · AI Foundations —
Wave 1`).

**URL routing (new):** the admin becomes routed pages — `/admin` (dashboard),
`/admin/people`, `/admin/people/:userId`, `/admin/assignments`, `/admin/feedback`,
`/admin/projects`, `/admin/templates`, `/admin/setup`. The scope is carried as a query
param (`?project=<id>`) so every admin URL is deep-linkable and the back button works.
Route guard semantics unchanged (session → role `admin`).

## 3. Screens (behavior contract; visuals per the mockups)

### 3.1 Dashboard
- Four tiles: Learners · Active this week · Need attention (red when >0) · New feedback.
- **Needs attention** list: flagged learners with the *reason* ("Stalled in Copilot ›
  Cowork for 16 days", "Invited, never activated", "Activated N days ago, assessment
  not started") + per-row actions: Remind (email), View (→ user detail).
- Per-project **activation funnel** cards: Invited → Activated → Assessed → Learning
  started → Completed a track, with counts and step-conversion %. Single-hue ordinal
  ramp, values as text labels (accessibility: no color-only encoding anywhere).
- Maturity distribution appears as one labeled bar row per level (never a stacked bar —
  the four brand level colors fail adjacent-segment contrast/CVD validation).

### 3.2 People
- Table columns: [select] Participant (avatar, name, email) · Project (company chip,
  only when unscoped) · Status (Active / Invited / Needs attention) · Maturity (level
  badge) · Progress (bar) · Last active · Role chip · row menu.
- Search + status filter pills. Server-side pagination (see §4.6).
- **Multi-select bulk bar** (sticky bottom): *n selected* → Assign content · Send
  reminder · Change role. Bulk assign posts one request (see §4.2).
- **Invite modal** (requires scope): first/last/email; two submit paths kept from the
  current app — *Send email invite* and *Create invite link only*; a banner states
  which project defaults the participant will automatically receive. **Bulk invite
  (CSV)** stays as the existing separate flow (dry-run preview → commit).

### 3.3 User detail page (replaces the UserPanel slide-over)
Full-width page at `/admin/people/:userId`; header = avatar, name, email, company chip,
status, last active; shortcut to Assignments.
- **Assessment results** (the answers behind the maturity level): overall level badge +
  usage band + safety flag + completion date; every competency question with the
  learner's chosen answer (quoted) and its rung pill (Not yet / Partial / Has it /
  Advanced — existing admin rung palette); usage profile (frequency, tools, contexts)
  as chips; open questions with quoted answers. Not-assessed state shows why (invite
  not redeemed / activated but not started) + a Send-reminder action.
- **Account card:** role (user / user+ / admin), maturity pin (shows effective level;
  pin overrides assessed level for path gating, existing `PUT …/maturity`), send
  reset link (email status + copyable link fallback, existing endpoint), remove
  participant (two-step in-place confirm, never `window.confirm` — existing app
  convention).
- **Learning progress card:** per-assigned-track completion bars.

### 3.4 Assignments (the headline redesign)
- Layout: **content scope tree** (left, ~220px) + **matrix** (right).
- Tree: `All tracks` root → tracks (with maturity-level color dots) → a selected
  track's modules. Selecting a node sets the matrix columns: tracks | that track's
  modules | that module's lessons. A breadcrumb above the matrix mirrors the tree.
- Matrix rows = the scoped project's participants. Top row = **Project defaults**
  (what new participants inherit). Cell states: ✓ assigned (explicit, `assigned_via=
  'manual'`) · ✓ via default (tinted, `assigned_via='default'`) · ◐ partial (some but
  not all children assigned — narrow the scope for detail) · empty. Click toggles.
  With strategy A (§4.1) every cell renders its own materialized row state — the
  mockup's read-time inheritance is a mock simplification, not the implementation.
- Legend always visible. Unscoped → company picker cards.

### 3.5 Feedback
- Status pills row: New (count) · Accepted · Dismissed · All. Separate **Filter** row:
  track dropdown + (post-AI: classification) + item count.
- Card anatomy: person (avatar + name, company beneath when unscoped) · date ·
  labeled location chips **Track: / Module: / Lesson:** (track chip carries the level
  dot and filters the queue on click) · *open lesson* link · quoted message ·
  Dismiss / Accept actions. Accepted items land conceptually on the content backlog;
  accepted/dismissed cards render dimmed with a status chip.
- **At launch there is no type chip and no AI-triage box** — both belong to the parked
  AI feature (§8). The mock shows them as a preview of that later state.

### 3.6 Projects, Email templates, Setup
- **Projects:** one card per project (company-first title): component-access toggles
  (assessment / learning path / interview × visible / unlocked — existing endpoints)
  and buttons that jump to People / Assignments / Email templates pre-scoped.
- **Email templates:** existing feature relocated to its own scoped section; purpose
  pills (Invitation / Password reset), Markdown body, insertable `{{token}}` chips,
  required-link-token validation, Save / server-rendered Preview / Reset-to-default,
  "default" indicator when no custom template is saved. Reuses the existing
  `EmailTemplatesCard` internals and `admin_email_templates` endpoints unchanged.
- **Setup:** create company / create project forms + existing list. Lift of the
  current `SetupView`.

## 4. Backend changes (decisions locked 2026-07-23, Matthias OK)

### 4.1 Project-level default assignments — the one new data concept
- New table `project_track_defaults (project_id, track_id)` (PK on the pair).
- **Track-level only:** a default track implies *all* of its modules and lessons;
  per-person tweaks handle exceptions.
- **Strategy A — materialize on invite:** when a user is created in a project (single
  invite, bulk CSV, either email or link path), the defaults are copied into
  `user_tracks`/`user_modules`/`user_lessons` rows. Add provenance
  `assigned_via text NOT NULL DEFAULT 'manual'` CHECK `('manual','default')` to the
  three assignment tables so the matrix can render "via default" distinctly.
  Changing a default later does **not** retro-apply; an explicit
  `POST /api/admin/projects/{id}/defaults/apply` backfills existing participants
  (additive only — never removes).
- Endpoints: `GET/PUT /api/admin/projects/{id}/defaults` (+ the apply action above).
- Existing read paths (graph counts, prerequisite unlock, lesson lists) are untouched
  by design — that is why A was chosen over read-time resolution.
- **Builds on the cascading-assignment feature** (branch
  `worktree-cascading-track-module-assignment`, spec
  `2026-07-23-cascading-track-module-assignment-design.md`, developed in parallel the
  same day): assigning a track/module cascades to all descendants with full-resync
  semantics, superseding the old keep-rows behavior. That cascade is exactly the
  mechanism defaults materialization and the matrix's track/module cell toggles need;
  cascade writes triggered by defaults carry `assigned_via='default'`.

### 4.2 Multi-user bulk assignment (transpose of existing bulk)
`POST /api/admin/assignments/bulk {user_ids[], track_ids[]|module_ids[]|lesson_ids[],
assigned}` — 404 if any id unknown, 422 on empty lists (existing bulk conventions).
Writes carry `assigned_via='manual'`. The bulk bar's other actions (send reminder,
change role) fan out client-side over the existing per-user endpoints — fine at our
scale, no new endpoints needed.

### 4.3 Feedback triage
- `feedback` gains `status text NOT NULL DEFAULT 'new'` CHECK
  `('new','accepted','dismissed')`, `reviewed_at`, `reviewed_by`.
  **No `type` column** (decided): the learner form stays message-only; a classification
  can later be AI-emitted without learner-facing change.
- `GET /api/admin/feedback?status=&track_id=&project_id=` (paginated, joined with
  lesson → module → track names) + `PATCH /api/admin/feedback/{id} {status}`.
- AI triage columns/job: **parked** (§8).

### 4.4 Dashboard aggregates — no migration
All signals derive from existing data: last active = max(`auth_sessions.last_used_at`);
activated = `password_set` OR `external_id`; assessed = `surveys.status='complete'`;
learning/stalled = `lesson_progress.completed_at`. New endpoint
`GET /api/admin/dashboard?project_id=` returning tiles + funnel(s) + attention list in
one call, computed with SQL aggregates (not per-user loops).
**Definitions (locked):** *stalled* = last lesson completion > 14 days ago for a learner
with unfinished assigned lessons; *active this week* = last activity ≤ 7 days;
*completed a track* = all assigned lessons of that track completed.

### 4.5 Reminder email
`POST /api/admin/users/{id}/reminder` — ACS email via the existing email-service seam
(feature-flagged like invite/reset; "sent/failed/disabled" status shape reused).
One new template in `services/email_templates.py`.

### 4.6 Hygiene riding along
Fix the documented `GET /api/admin/users` N+1 (`admin_user_service.py`); add pagination
to `/admin/users`, `/admin/learning`, and the new feedback list from day one.

### Unchanged (explicitly)
Roles (`admin`/`user+`/`user`), auth, the authorization iron rule (no endpoint outside
`/admin/*` accepts a user identifier), assignment-as-visibility-filter (not access
control), learner-side lock semantics, content endpoints.

## 5. Frontend foundation ("middle + reskin", confirmed)

- **New admin shell:** nested routes under `/admin/*` (react-router already in the app),
  sidebar navigation, topbar scope switcher; scope in the URL query.
- **Data layer:** TanStack Query (react-query) for all admin data — caching, request
  dedup, shared loading/error handling, optimistic updates for matrix toggles and
  triage actions (reconcile on error). Admin-only for now; learner pages keep their
  current pattern.
- **Component kit** (small, admin-scoped, styled per the prototype `styles.css` tokens —
  which derive from the app's existing `--dlw-*` brand tokens): Table, Chip/Badge,
  Tile, Card, Toolbar/FilterRow, ProgressBar, BulkBar, Modal, EmptyState, ErrorState,
  two-step ConfirmButton, ScopeSwitcher, ContentTree, Matrix.
- **Reused legacy internals** (inside the new shell, token-level restyle only):
  `SurveyResults` (user detail), `BulkInviteModal`, `EmailTemplatesCard` internals,
  Setup forms — plus `ParticipantDetail` internals if the parallel inline-detail work
  (see §9) lands first. `Admin.tsx`, `ProjectsView`, `ProjectDetailView`, and the
  UserPanel/ParticipantDetail *container* are **retired** — their functions all have
  new homes (verified against the full feature inventory).
- Loading/error/empty states always via the shared components — no literal strings.

## 6. Rollout — one-go cutover (confirmed)

Build the complete new panel on a feature branch; ship as **one release** replacing
`/admin`. Learners never see the admin panel, so the blast radius is Aaron + Matthias;
rollback = revert the release commit. The old panel code is deleted in the cutover
commit (recoverable from git history). Content edit modes on learner pages are
untouched by the cutover. Standard deploy discipline applies (build from a clean
worktree of the pushed commit, never the live working dir).

## 7. Testing

- **Backend:** authz-matrix entries for every new `/admin` endpoint × 3 roles;
  materialization tests (invite single/bulk/link/email × defaults; apply-action
  additivity; provenance values); dashboard aggregate correctness against seeded
  fixtures; feedback status transitions; pagination contracts. Existing suites must
  stay green (locks/progress semantics untouched is a test assertion, not a hope).
- **Frontend:** typecheck/lint/build; `npm run gen:api` after each contract change.
- **Browser verification** (pre-cutover checklist): the five mockup tasks executed
  against the real app — morning check, project health, bulk assign, change defaults,
  triage feedback — plus user detail (assessed + not-assessed), invite with defaults
  banner, deep-link + back-button on every route, and a below-1280px width pass.

## 8. Parked / out of scope

- **AI feedback triage** (feasibility/effort/note columns + rating job + type
  classification): parked until after go-live. An org-managed Anthropic API key is
  available; storage (Container App secret) and trigger (script → job) to be decided
  when picked up. The queue ships without the `ai_*` columns.
- **Feedback roll-up grouping** (per-lesson aggregation): revisit when volume grows.
- **Content authoring UX**, the delaware IT hosting move, Entra go-live: separate
  tracks, unaffected.

## 9. Reference & related parallel work

- Mockups (visual contract): `docs/design-prototypes/admin-redesign/` (promoted from
  the untracked `scratch_review/admin_redesign_prototypes/` iteration space).
- Backend alignment note (decision history): `backend-changes-for-matthias.md`, formerly in
  the prototype folder — removed 2026-08-10 as superseded by this spec (recoverable from git
  history).
- Current-state audit that motivated the foundation work: `docs/reviews/2026-07-09-code-review.md`.
- **Parallel work discovered at spec time** (branch
  `worktree-cascading-track-module-assignment`, Matthias, same day):
  - *Cascading track/module assignment* (spec + plan + implementation): aligned —
    adopted as the write mechanism in §4.1. This redesign builds on it, not around it.
  - *Participant inline detail* (spec + plan, "approved, implementing"): a tactical
    replacement of the UserPanel slide-over inside the current panel. Compatible as a
    stopgap; superseded by this redesign's user detail page (§3.3) at cutover. The
    implementation-plan phase must sequence against this branch (merge it first, then
    build on top).
