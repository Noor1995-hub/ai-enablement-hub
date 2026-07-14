# Bulk CSV Invite — Design Spec

**Date:** 2026-07-14
**Status:** Approved design, pending implementation plan
**Area:** Admin panel → project view (participant onboarding)

## Summary

Add a bulk-invite capability to the admin project view: an admin uploads a CSV of
users (first name, last name, email), previews a validated result, confirms, and the
valid users are created and emailed an invite link. This is purely additive — the
existing single-invite form is unchanged.

All uploaded users are bound to the project the admin is currently viewing, so the CSV
carries **no** project column.

## Goals

- Onboard a cohort (typically up to ~50 users) into one project in a single action.
- Never mass-email off a bad file: validate and preview before anything is created or sent.
- Handle real-world files produced by Excel in EU locales (semicolon delimiter, UTF-8 BOM).
- Report per-row outcomes; one bad row never aborts the batch.
- Add no new stored personal data beyond the `User` rows an invite already creates.

## Non-goals

- No background job / queue (out of scope at this scale — see Scale).
- No re-invite of already-registered or already-invited users (they are skipped; the
  existing per-user reset/invite-link button handles individual re-nudges).
- No `role` or track/module/lesson assignment via CSV (fresh invites are `role='user'`
  with no assignments, exactly like the single invite today).
- The uploaded file is never stored.

## Decisions (locked with the user)

| Decision | Choice |
|---|---|
| Import flow | **Preview → confirm** (two-step, never fires on upload) |
| Wiring | **Option A**: one endpoint, `dry_run` flag; file re-sent for the commit |
| Scale | Typically ≤50 rows → **synchronous** send in the request |
| Duplicates | **Skip all existing** emails (password set *or* never activated); report them |
| CSV format | **Named headers** `first_name,last_name,email` (case-insensitive, any order, extra columns ignored); header row required; **Download template** provided |
| Delimiter/encoding | Auto-detect `,` vs `;`; strip UTF-8 BOM |
| Excel files | **CSV only** (editable in Excel, but must be saved as CSV); a native `.xlsx`/`.xls` upload is rejected with a friendly "Save As → CSV" message, not `.xlsx` parsing |
| File storage | **In-memory only, discarded**; no disk, no Blob |
| Audit logging | Summary counts + admin id + project id only; **no PII in logs** |
| Row cap / file cap | **200 rows / 1 MB** (headroom over the ~50 typical) |

## Architecture

The feature reuses the existing invite plumbing end to end. The only net-new pieces are
a CSV parser util, a batched existence check, one endpoint, and one frontend component.

### Backend

**Endpoint** — `POST /api/admin/invites/bulk`, in
`backend/src/routers/admin_users.py` beside `create_invite`. Admin-only via the
router-level `require_admin` dependency.

- Request (`multipart/form-data`): `file` (CSV), `project_id` (UUID), `dry_run` (bool).
- Response — `BulkInviteReport` (new schema in `backend/src/schemas/admin_users.py`):

  ```
  BulkInviteReport {
    dry_run: bool
    project_id: UUID
    summary: {
      total_rows: int
      valid: int
      duplicates: int
      invalid: int
      created: int          # 0 on dry_run
      email_failed: int     # 0 on dry_run
    }
    rows: [ BulkInviteRow ]
  }

  BulkInviteRow {
    row_number: int         # 1-based, source row in the file
    first_name: str
    last_name: str
    email: str
    status: "valid" | "duplicate" | "invalid"    # preview (dry_run=true)
          | "created" | "email_failed"           # commit (dry_run=false): each prior
                                                 # "valid" row becomes one of these
    detail: str | null      # reason for duplicate/invalid, e.g.
                            # "already registered", "malformed email",
                            # "missing last_name", "duplicate in file"
  }
  ```

**CSV parser** — new `backend/src/services/invite_csv.py`, pure (no DB, no I/O):

- `parse_invite_csv(raw: bytes) -> ParseResult` where `ParseResult` carries either a
  whole-file error (missing required column, undecodable, too many rows) or a list of
  `ParsedRow { row_number, first_name, last_name, email, error: str | None }`.
- Excel guard: if the bytes are a native workbook (`.xlsx` ZIP magic `PK\x03\x04` or
  `.xls` OLE magic), raise a whole-file error telling the admin to Save As → CSV — caught
  before decode so they never see a cryptic "not valid UTF-8" message.
- Decode: strip UTF-8 BOM, decode UTF-8.
- Delimiter: detect `,` vs `;` (sniff the header line).
- Headers: lowercase + trim; map to `first_name` / `last_name` / `email` in any order;
  ignore extra columns; a missing required column is a whole-file error.
- Per row: trim all fields; require non-blank first and last name; validate + lowercase
  the email; rows failing validation get an `error` reason and are surfaced as `invalid`.
- In-file dedup: the 2nd+ occurrence of an email is flagged `duplicate in file`.

**Service** — `backend/src/services/admin_user_service.py`:

- Add `existing_emails(emails: Iterable[str]) -> set[str]` — one batched repository
  query returning which of the given (normalized) emails already have a `User` row.
- Reuse the existing `invite(...)` / `UserRepository.create(...)` path for creation.
- Rule preserved: **services do not call services**; token minting and emailing stay in
  the router (as they do for `create_invite`).

**Router orchestration** (mirrors `create_invite`):

1. Parse the file → parser yields the `invalid` rows.
2. `existing_emails(...)` over the parsed emails → the `duplicate` set (any existing
   email, regardless of `password_set`).
3. Remaining rows are `valid`.
4. `dry_run=true`: assemble `BulkInviteReport`, **persist nothing**.
5. `dry_run=false`: create valid users + tokens (single DB transaction, then commit),
   then send emails. A failed send does **not** roll back the created user — it is
   reported as `email_failed`, matching single-invite semantics.

**Rate limiting** — the single invite is limited per email (`invite:{email}`), which
would false-fail cohorts and re-previews here. The bulk endpoint uses a **per-admin**
limit (`bulk_invite:{admin_id}`) instead — a runaway-loop backstop, not per-recipient
throttling.

**Guardrails**

- Admin-only (existing dependency).
- File size cap **1 MB**; row cap **200**. Exceeding either → whole-file error, nothing
  created.
- File processed in memory and discarded; never written to disk or Blob.
- Audit log line on commit: admin id, project id, and the summary counts — no names/emails.

### Frontend

- New component `frontend/src/pages/admin/BulkInviteModal.tsx`, opened from a
  "Bulk invite (CSV)" control in
  `frontend/src/pages/admin/ProjectDetailView.tsx`, reusing `adminStyles.ts`. The
  existing single-invite form is untouched.
- **Download template**: client-side `Blob` download of
  `first_name,last_name,email\n` — no backend route.
- **Upload**: a hand-typed `api/bulkInvite.ts` helper (plain `fetch` + `FormData`, Bearer
  token, single-flight-refresh retry) — mirroring the established multipart precedent
  `api/upload.ts` rather than `openapi-fetch`, whose typing for multipart bodies is awkward.
- **Preview**: render the summary banner + per-row table from the `dry_run=true`
  response; highlight `duplicate` / `invalid` rows. Whole-file errors (missing column,
  too big, too many rows) render as a banner instead of a table.
- **Confirm**: "Confirm & send N invites" (disabled when `valid == 0`) re-sends the same
  `File` with `dry_run=false`; render the results summary; call `onProjectRefresh()` to
  reload the participants table.
- `npm run gen:api` is not required (the endpoint still appears in OpenAPI via its
  `response_model`); the frontend response types are hand-kept in sync with `BulkInviteReport`.

## Data flow

```
Admin picks file
      │  (multipart, dry_run=true)
      ▼
POST /api/admin/invites/bulk ── parse_invite_csv ──► rows (+ invalid)
      │                          existing_emails ───► duplicates
      │                          remainder ─────────► valid
      ▼
BulkInviteReport (nothing persisted)  ──► preview table
      │
Admin clicks Confirm
      │  (same file, dry_run=false)
      ▼
POST /api/admin/invites/bulk ── (re-parse, re-check) ──► for each valid:
      │                             create User + AuthToken (txn, commit)
      │                             send invite email (failure → email_failed)
      ▼
BulkInviteReport (created / email_failed / skipped) ──► results summary + refresh
```

## Error handling

- **Whole-file errors** (undecodable, missing required column, > 200 rows, > 1 MB):
  return a single error; create nothing; frontend shows a banner.
- **Per-row errors** (bad email, blank name, in-file dup): row marked `invalid`, skipped,
  reason in `detail`; the rest proceed.
- **Existing users**: marked `duplicate` (`already registered`), skipped.
- **Email send failure** (commit only): user is still created; row marked `email_failed`;
  admin can re-send via the existing per-user link button.
- **TOCTOU** (a user created between preview and commit): commit re-runs the existence
  check, so a late duplicate is skipped at commit and reported.

## Testing

**Parser unit tests** (`parse_invite_csv`): comma and semicolon delimiters; UTF-8 BOM;
CRLF line endings; headers reordered; extra columns ignored; missing required column;
blank first/last name; malformed email; quoted names containing commas; in-file
duplicates; over-row-cap.

**Endpoint tests**: `dry_run=true` returns a correct preview and creates nothing;
`dry_run=false` creates + emails valid rows; a seeded existing user is skipped as
`duplicate`; invalid rows reported; stubbed sender returning `False` yields
`email_failed` with the user still created; oversized file and over-cap row count
rejected as whole-file errors; non-admin → 403.

**Frontend**: manual verification in the running app (template download, preview render
for a mixed-quality file, confirm, participants refresh); component test optional.

## Files touched

- `backend/src/services/invite_csv.py` — **new** parser util.
- `backend/src/schemas/admin_users.py` — add `BulkInviteReport`, `BulkInviteRow`.
- `backend/src/services/admin_user_service.py` — add `existing_emails(...)`.
- `backend/src/routers/admin_users.py` — add `POST /api/admin/invites/bulk`.
- `backend/tests/...` — parser + endpoint tests.
- `frontend/src/pages/admin/BulkInviteModal.tsx` — **new** UI.
- `frontend/src/pages/admin/ProjectDetailView.tsx` — entry point control.
- `frontend/src/api/schema.d.ts` — regenerated.

## Constraints to honor during implementation

- Backend must follow the project's `python-be-architecture.md`
  (router → service → repository; services never call services; token minting in the
  router). Verify the endpoint/service split against that doc when writing the plan.
- Reuse the existing invite/token/email code paths rather than duplicating them.
```
