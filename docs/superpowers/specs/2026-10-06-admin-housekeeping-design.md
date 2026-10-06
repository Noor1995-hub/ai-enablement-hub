# Admin housekeeping: move users, rename/delete projects and companies, media library: design (B6)

Issues: #147 (B6 of the admin-roles split) and #111 (move a user to another project), which this
work closes. #160 part 2 duplicates #111. Builds on the project-scoped admins of
`2026-10-01-project-scoped-admin-design.md` and the delete-with-impact pattern of
`2026-10-05-content-structure-editing-design.md`.

## Why

Small power-admin housekeeping that today needs the database or the Azure portal:

- A user's project is fixed at invite (`PATCH /api/admin/users/{id}` only sets the role).
- Projects and companies can only be created, never renamed or deleted.
- Media can be uploaded (`POST /api/admin/media`) and shown, but not listed or deleted. Every
  replaced image, deleted image block or deleted lesson leaves its file in the private container,
  and nobody can see what's there or what's still used.

Done when every operation below works in the admin panel, with authz and service tests.

## Decisions (2026-10-06, Matthias)

1. **Moving a user keeps all their assignments.** Their progress, assessment and interview stay
   too (they belong to the user). Adding the new project's defaults automatically, or replacing
   assignments with them, were rejected: either silently changes a learner's path. The admin can
   still assign more, or press the new project's "apply defaults".
2. **A project or company can be deleted even when it has users**, behind a warning that spells
   out the impact, and **its users are deleted with it**, with their progress, assessments and
   interviews. Keeping them project-less was rejected.
3. **Power admins are never deleted by a project or company delete.** A power admin whose home
   project or company is deleted keeps the account and becomes project- and company-less (added
   during design so a delete can't lock the operators out).
4. **The media library lists files and deletes unused ones.** A "choose from library" picker in the
   lesson editor was rejected for now (a second feature in the editor).
5. **Everything in B6 is power admin only.**

## 1. Move a user to another project (#111)

- **UI:** on the user detail page (`frontend/src/pages/admin2/UserDetailPage.tsx`), **Move to
  project** opens a dialog with all projects as "Company · Project". It says what changes: the
  new project's locks, AI settings and email templates apply from now on; assignments, progress,
  assessment and interview stay.
- **API:** `PUT /api/admin/users/{user_id}/project`, body `{project_id}`, `require_power_admin`.
  - It sets `users.project_id` and `users.company_id` (the new project's company) in one transaction.
  - Unknown user or project → 404. Moving to the current project is a no-op 200.
  - A power admin target is allowed (their home project is just a membership).
  - If the user holds a `project_admins` grant **on the destination project**, that grant is removed
    in the same transaction: staff aren't learners of the project they run (B1's rule). The dialog
    warns when this applies.
- The user then appears under the new project on People, the dashboard and the export. Nothing
  else is touched.

## 2. Rename and delete projects and companies

On the Projects page (`frontend/src/pages/admin2/ProjectsPage.tsx`).

**Rename:** `PATCH /api/admin/projects/{project_id}` and `PATCH /api/admin/companies/{company_id}`,
body `{name}`, `require_power_admin`. Blank names are refused (422). Names keep the rules create applies
today: a company name is unique case-insensitively (`DuplicateCompanyNameError`, 409, as on
create); project names have no uniqueness rule (create has none either).

**Delete impact:** `GET /api/admin/projects/{project_id}/impact` and
`GET /api/admin/companies/{company_id}/impact` return counts only:
`{projects, users_deleted, power_admins_kept, project_admin_grants, users_with_progress}`
(`projects` is 0 for a project).

**Delete:** `DELETE /api/admin/projects/{project_id}` and `DELETE /api/admin/companies/{company_id}`,
`require_power_admin`, one transaction:

1. Users to delete: every user whose `project_id` is the project (for a company: is any of its
   projects), plus for a company every user whose `company_id` is the company. **Excluding power
   admins** (decision 3).
2. Power admins among them get `project_id = NULL` (and `company_id = NULL` for a company delete).
3. Delete those users. Their sessions, tokens, assignments, progress, survey, conversations,
   feedback and project-admin grants go via the existing `ON DELETE CASCADE` foreign keys. This
   needs the same path as today's user delete; check every FK into `users` while building.
4. Delete the project (or company). Its settings, email templates, defaults and `project_admins`
   rows cascade. For a company, its projects cascade (`projects.company_id ON DELETE CASCADE`),
   which works because step 3 removed every user pointing at them with `RESTRICT`.

**Logging:** one line per delete with ids and counts only, never names or emails.

**UI:** each project and company row gets **Rename** (inline) and **Delete…**. Delete fetches the
impact and shows, for example, "Deletes Rollout 2025, its 14 users (12 with progress), their
assessments and interviews, the project's settings and email templates, and 2 project-admin
grants. Power admins in it keep their accounts." Then a two-step in-app confirmation (`ConfirmButton`,
never `window.confirm`). Deleting the project currently in the scope switcher resets the scope to
"All projects".

## 3. Media library

New admin page **Media** (`/admin/media`, power admins only, sidebar item).

**Storage:** files live in the private container as `images/<hex>.<ext>` and `videos/<hex>.<ext>`
(`services/media_service.py`). The service's storage protocol gains a container-level listing and
a delete next to `get_blob_client`, and stays fakeable in tests as it is today.

**`GET /api/admin/media`** (power admin) returns
`{files: [{path, kind, size_bytes, uploaded_at, preview_url, used_in}], total_bytes}`:

- `preview_url` is a short-lived SAS link for images (the same stamping lessons use) and null for
  videos.
- `used_in` lists the lessons whose `content_blocks` reference the path (an image `blob_path`, or a
  video with `source: "blob"` and that `blob_path`), each `{lesson_id, lesson_title, module_title}`,
  plus a count of AI content proposals in status `pending` or `approved` whose
  `base_blocks`/`proposed_blocks`/`edited_blocks` reference it. **Any reference = in use.**
- Usage comes from one scan of all lessons and the live proposals per request. That's hundreds of
  rows, so no index is needed.

**`DELETE /api/admin/media/{kind}/{name}`** (power admin):

- `kind` is `images` or `videos`. `name` must match `<hex>.<ext>`, so no path traversal: anything
  else is 404.
- The server re-checks usage at delete time and returns **409 "in use"**, naming the lessons, if a
  reference appeared since the list was loaded.
- Unknown file → 404. One log line with the path.

**Page:**
- a table with thumbnail (or a video icon), file name, type, size, uploaded, and **Used in**
  (lesson links to the editor) or **Unused**;
- filters All / Unused and All / Images / Videos;
- a header line like "38 files · 412 MB · 9 unused (61 MB)";
- a two-step **Delete** on unused rows only.

## Testing

- **Backend service tests:**
  - a move keeps assignments and progress, updates `company_id`, and drops a grant on the
    destination only;
  - impact counts for a project and a company;
  - a delete removes members and their data, keeps power admins project-less, and cascades a
    company's projects;
  - media usage across lessons (image, blob video, embed video ignored) and live proposals
    (rejected and superseded ignored);
  - deleting a file in use is refused;
  - a bad media name gives 404.
- **Integration tests** per endpoint against Postgres, with media storage faked through the
  service's protocol.
- **Authz:** every new route has a `_MATRIX` row, all `power`.
- **Frontend:**
  - the move dialog;
  - the delete warnings with two-step confirmation;
  - the scope reset after deleting the scoped project;
  - the media table, its filters and the delete of an unused file.

## Docs

- `docs/feature-index.md` entry.
- `SECURITY.md` → "Admin access to learner data": a power admin can delete a project or company
  and with it its learners' data; recovery is only the nightly backup
  (`docs/db-backup-restore.md`).
- Closes #111. #160 keeps its part 1 (preview a project as its learners see it).

## Out of scope

- A media picker in the lesson editor (decision 4), renaming media, and uploading from the Media
  page.
- "Delete all unused" in one action.
- Bulk moving users (one at a time here). A project delete takes its users with it anyway.
- Project admins doing any of this (decision 5).

## Risks

- **Deletes are permanent and take learner data.** The impact warning is the only guard; the
  nightly backup is the recovery path.
- **Foreign keys into `users`.** Every table that references `users` must cascade or allow the
  delete, or the transaction fails. The plan's first backend task checks them against the models
  and the existing single-user delete path.
- **The media scan reads every lesson's blocks on each list request.** That's fine at today's scale
  (about 100 lessons). If it grows, a usage index is the follow-up.
