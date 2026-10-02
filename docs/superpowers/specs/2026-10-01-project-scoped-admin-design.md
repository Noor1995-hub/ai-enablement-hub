# Project-scoped admins: design (B1)

Issue: #93. Follow-ups that depend on this spec: #144 (admin panel by capability), #92 (project export).
Independent work from the same split: #145, #146, #147.

## Why

People who don't have Claude or direct database access are starting to use the hub as admins.
Today every admin is global. `require_admin` (`backend/src/core/dependencies/auth.py`) only checks
`role == 'admin'`, and no admin endpoint checks which project its caller belongs to. `project_id`
is just an optional filter. A client-side coach given "admin" today can read and delete every
learner in every project, edit live content and change AI prompts' context.

The goal is three tiers:

| Tier | Who | Can do |
|---|---|---|
| user | learners | consume the site |
| **project admin** | client coaches, delaware leads | user management for the projects they administer |
| **power admin** | Matthias, Aaron | everything `admin` can do today |

## Decisions (2026-10-01, Matthias)

1. A project admin can administer **several projects**. Their scope is a new `project_admins`
   table, not the role column. A project admin may be a learner in another project or in none.
2. **`user+` is dropped.** Existing `user+` accounts become `user`.
3. A project admin, inside their projects only, can:
   - invite (single and bulk), always with role `user`;
   - delete users;
   - view a user's detail, assessment results, progress and interview;
   - assign content and set project default tracks;
   - set a maturity pin, send reset links and reminders;
   - change project settings: component hidden/locked, AI surface toggles, email templates;
   - see a dashboard limited to their projects.
4. Power admin only:
   - role changes, and granting or revoking project-admin rights;
   - all content (tracks, modules, lessons, media);
   - feedback triage, Content AI and calibration notes, prompts;
   - company and project create.
5. **Lock bypass:** power admins, and project admins *on their own project*, bypass `locked`
   components, module prerequisites, the lesson access gate and the "assessment first" interview
   gate. **`hidden` stays hidden for everyone**: if learners can't see a component, admins can't
   either. AI surface toggles are not locks and stay a hard gate for everyone (they control spend).
6. Dashboard numbers exclude power admins (as today) and the admins of the project being counted.

## Data model

- `users.role` keeps two values: `'admin'` (power admin) and `'user'`. Learners and project admins
  are both `'user'`.
- New table `project_admins`:

  | column | type | notes |
  |---|---|---|
  | `user_id` | uuid FK `users.id` ON DELETE CASCADE | PK part 1 |
  | `project_id` | uuid FK `projects.id` ON DELETE CASCADE | PK part 2, own index |
  | `granted_by` | uuid FK `users.id` ON DELETE SET NULL | nullable |
  | `granted_at` | timestamptz default now() | |

- A power admin can also have `project_admins` rows. They're harmless and ignored for scope,
  because power-admin scope is already everything.
- **Migration** (one revision on top of the current head, `e5f6a7b8c9d0`):
  1. create `project_admins`;
  2. `UPDATE users SET role = 'user' WHERE role = 'user+'`;
  3. replace the role CHECK with `role IN ('admin', 'user')`.

  The downgrade drops the table and widens the CHECK again. Former `user+` accounts are not
  restored; this is accepted, because the role only bypassed locks.

  The migration runs only in the Deploy migrate job, never locally (the one-database rule).

## Authorization: one scope, three guards

New module `backend/src/core/dependencies/admin_scope.py`:

- **`AdminScope`**: a frozen dataclass `(user, is_power: bool, project_ids: frozenset[UUID])`.
  Its method `covers(project_id: UUID | None) -> bool` returns true when `is_power` or
  `project_id in project_ids`.
- **`get_admin_scope`** reads the caller's `project_admins` rows on every request, the same way the
  role is read from the DB today (never from the JWT), so revoking takes effect on the next request.
  It raises 403 "Admin role required" when the caller is neither a power admin nor has any rows.
- **The three guards** that replace `require_admin`:
  - **`require_power_admin`** for global routes. Same behaviour as today's `require_admin`, renamed
    so every remaining call site is a deliberate choice.
  - **`require_project_in_scope`** for routes with `{project_id}` in the path. An out-of-scope
    project returns **404**, so project ids of other clients can't be probed.
  - **`require_user_in_scope`** for routes with `{user_id}` in the path. It loads the target, then
    returns 404 unless `scope.covers(target.project_id)`. For a project admin it also returns
    **403** when the target is a power admin, has any `project_admins` row, or is the caller.
- **Lists and filters** (users, dashboard, learning overview, surveys, companies): the router passes
  `scope` to the service.
  - With an explicit `project_id` outside scope: 404.
  - With no `project_id`: if the project admin has exactly one project, that project is used.
    With several, the request is rejected (400 "project_id is required"). The admin panel always
    sends the selected project (#144), so no list query has to learn "a set of projects".
  - Power admins: unchanged behaviour.
- **Bodies that carry ids:**
  - **Invites:** `body.project_id` must be covered. For a project admin the created role is always
    `user`.
  - **`POST /assignments/bulk` and `GET /surveys?user_ids=`:** every user id must be in scope. One
    miss rejects the whole request with 404, no partial apply.

### Endpoint table

**Open to project admins, scoped:**

| Router | Endpoints | Guard |
|---|---|---|
| `admin_users.py` | `GET /users`, `GET /learning` | scope filter |
| | `GET /users/{id}`, `POST /users/{id}/reset-link`, `/reminder`, `PUT /users/{id}/maturity`, `DELETE /users/{id}`, every `PUT /users/{id}/tracks|modules|lessons…`, `GET /surveys/{id}` | `require_user_in_scope` |
| | `POST /invites`, `POST /invites/bulk` | body project covered, role forced `user` |
| | `POST /assignments/bulk`, `GET /surveys?user_ids=` | every id in scope |
| `admin_defaults.py` | all three | `require_project_in_scope` |
| `admin_org.py` | components GET/PUT, AI settings GET/PUT | `require_project_in_scope` |
| | `GET /companies` | filtered to companies with an in-scope project, listing only those projects |
| `admin_email_templates.py` | all four | `require_project_in_scope` |
| `admin_dashboard.py` | `GET /dashboard` | scope filter |
| `interview.py` (admin_router) | `GET`, `DELETE /admin/interviews/{user_id}` | `require_user_in_scope` |
| new | `GET /projects/{id}/admins` | `require_project_in_scope` |

**Power admin only:**

| Router | Endpoints |
|---|---|
| `admin_users.py` | `PATCH /users/{id}` (role) |
| `admin_org.py` | `POST /companies`, `POST /projects` |
| `admin_content.py`, `admin_media.py` | all admin writes |
| `admin_feedback.py`, `admin_content_improvement.py`, `admin_calibration_notes.py`, `admin_prompts.py` | all |
| new | `PUT /projects/{id}/admins/{user_id}`, `DELETE /projects/{id}/admins/{user_id}` |

### Guards that apply to everyone

- An admin can't delete their own account or change their own role (409).
- The last power admin can't be demoted or deleted (409).
- Granting project-admin rights to a power admin is a no-op success, not an error.
- Revoking a row that doesn't exist returns 404.

## Lock bypass (learner side)

- **New helper `bypasses_locks(user, admin_project_ids) -> bool`**, which replaces the
  `LOCK_BYPASS_ROLES` tuple in `core/constants.py`. It's true for a power admin, or when
  `user.project_id` is not None and is in the user's `project_admins` project ids.
- **Where it's used:**
  - `routers/learning.py` (the two `bypass_locks=` call sites) and so
    `learning_service._is_accessible`;
  - `core/dependencies/interview.py::require_completed_assessment`, which replaces
    `_ASSESSMENT_EXEMPT_ROLES`;
  - `core/dependencies/components.py::_ensure_unlocked`. **`hidden` still raises for everyone;
    `locked` raises only when the user doesn't bypass locks.** This is a behaviour change: today
    nobody bypasses component locks.
  - `GET /api/me/journey` (`routers/me.py`). For a user who bypasses locks, a `locked` component is
    returned unlocked; `hidden` is unchanged.
- `require_ai_surface` and `require_interview_surface` are **unchanged**.
- **`GET /api/me`** adds `is_power_admin: bool`, `admin_project_ids: list[UUID]` and
  `bypasses_locks: bool`. Until #144 ships, the frontend keeps working: `role` is still returned
  and still `'admin'` for power admins.

## Dashboard

`dashboard_service.py` already drops `role == 'admin'`. For each project it also drops users who
have a `project_admins` row for that same project.

## Frontend in B1 (minimum, so nothing breaks)

The admin panel rework is #144. B1 only:

- removes `'user+'` from the `Role` type and the role-change buttons;
- switches `learningPathLocks.ts` and `interviewAccess.ts` from role checks to the new `/api/me`
  fields;
- regenerates the API types (`npm run gen:api`).

A project admin still can't open `/admin` until #144 ships. That's an accepted gap: B1 can deploy
safely on its own because no one has a `project_admins` row yet.

## Testing

- **Authorization matrix** `tests/integration/test_routers/test_authz.py`:
  - each row gets an `access` value of `power_only` or `project_scoped`;
  - every row is called as anonymous (401), learner (403), project admin of project A against a
    project-A target, the same project admin against a project-B target, and power admin;
  - expected results: in-scope rows succeed for the project admin, out-of-scope rows return 404,
    `power_only` rows return 403.
  - Add the rows missing today: `GET /users/{id}`, `/invites/bulk`, `/admin/interviews/{id}`,
    `/admin/prompts*`, `/projects/{id}/ai*`, plus the new endpoints.
  - **A guard test makes the matrix complete:** it walks the OpenAPI schema and fails if any
    `/api/admin/*` route is missing from `_MATRIX`.
- **Unit:** `AdminScope.covers`, `bypasses_locks`, the self/last-power-admin guards, invite
  role-forcing and bulk all-or-nothing.
- **Lock bypass integration:**
  - a project admin on their own project opens a `locked` learning component and a
    prerequisite-locked lesson, and gets past the assessment gate;
  - the same user still gets 403 on a `hidden` component and on a disabled AI surface;
  - a project admin of project B whose own project is A does not bypass anything.
- **Migration:** the test DB is built with `create_all`, not by running the migrations. So the
  migration itself is covered by CI's migrations job (`alembic upgrade head`, `alembic check`, and a
  `downgrade -1` round-trip on a local Postgres). A unit test asserts that the model's role CHECK no
  longer allows `user+`.
- All checks from `CLAUDE.md`, coverage ≥ 90%.

## Out of scope

- The admin panel by capability, and the UI to grant project admins: #144.
- The project data export: #92.
- Moving a user to another project: #111 (power admin only when it ships).
- An audit log of admin actions: parked.

## Risks

- **AI spend:** project admins can switch on AI surfaces for their projects, while the spend cap on
  the prod key is still unverified (#44).
- **Aaron's interviewer work** touches `interview.py` and `core/dependencies/interview.py`: fetch
  before branching and merge `main` often.
- **Phase D tasks:** D5 touches the AI-surface settings read. Expect a small merge in `admin_org.py`
  or `core/dependencies/`, not a design conflict.
