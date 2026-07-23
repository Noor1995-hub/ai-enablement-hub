# Admin panel redesign — backend changes to align on

**From:** Aaron (drafted with Claude) · **Date:** 2026-07-23
**Context:** We're redesigning the admin panel (MVP → production-ready). The UX is being
iterated as throwaway HTML mockups in `scratch_review/admin_redesign_prototypes/` — open
`index.html` there to click through the current state (round 3). The direction is a
function-first sidebar (Dashboard · People · Assignments · Feedback · Projects · Setup)
with one global company/project scope switcher.

Most of the redesign is frontend-only on top of existing endpoints. **Four things need
backend work**, one of them a real data-model addition. Nothing here is started — this
note is to align before any spec/plan is written.

---

## 1. Project-level default assignments  ⚠️ the big one

**Today:** assignment is strictly per-user (`user_tracks` / `user_modules` / `user_lessons`,
written via `PUT /api/admin/users/{id}/tracks|modules|lessons`). Every new participant
starts empty and is configured by hand — that's the #1 admin pain we're solving.

**Wanted:** each project defines a default content set; new participants inherit it
automatically at invite time. Per-user deviations stay possible on top (both extra
assignments and removals). The mock's assignment matrix visually distinguishes
"assigned via default" from "explicitly assigned".

**New schema (roughly):** `project_track_defaults (project_id, track_id)` — and the open
design question whether defaults also exist at module level or track-level defaults imply
"all modules/lessons of the track" (current mock assumes the latter; per-person tweaks
handle exceptions).

**The key decision — two implementation strategies:**

| | A. Materialize on invite | B. Resolve at read time |
|---|---|---|
| How | Copy defaults into `user_*` rows when the user is created (add an `assigned_via: 'default'\|'manual'` provenance column so the UI can show the difference) | Effective assignment = project defaults ∪ per-user overrides − per-user exclusions (three-state per user/content pair) |
| Changing a default later | Does **not** retro-apply — needs an explicit "apply to existing participants" admin action (probably wanted anyway, as an opt-in button) | Propagates automatically to everyone without an explicit override |
| Blast radius | Small: invite/bulk-invite service + one provenance column; every existing read path (graph counts, lesson lists, prerequisite unlock, learner sidebar) untouched | Large: every assignment read path changes, incl. `assigned_lesson_counts_by_module` and the LearningPath unlock rule |
| Risk | Low | High — the lesson-assignment semantics (2026-07-06 feature) are load-bearing for locks/progress |

**Recommendation: A.** The keep-rows/re-assign semantics we already have stay intact, and
"apply defaults to existing participants" becomes a deliberate admin action instead of a
silent global mutation.

**Endpoints:** `GET/PUT /api/admin/projects/{id}/defaults`, plus optionally
`POST /api/admin/projects/{id}/defaults/apply` (backfill to existing participants).

---

## 2. Multi-user bulk operations (transpose of today's bulk)

**Today:** bulk endpoints are one-user-many-items (`PUT /users/{id}/tracks {track_ids[]}`).

**Wanted by the new People table:** select N users → one action. Many-users-many-items:
`POST /api/admin/assignments/bulk {user_ids[], track_ids[]|module_ids[]|lesson_ids[], assigned}`
(404 if any id unknown, 422 on empty — same conventions as the existing bulk PUTs).
Also from the bulk bar: bulk **reminder email** (new — see §4) and bulk role change
(can loop the existing PATCH client-side at our scale; endpoint optional).

---

## 3. Feedback triage workflow (+ AI rating)

**Today:** `feedback` table is bare — `user_id, lesson_id (FK), message, created_at`
(`backend/src/db/models/feedback.py`). No admin surface beyond raw rows; no status, no type.

**Wanted:** an admin review queue where feedback is accepted (→ content backlog) or
dismissed, filterable by track/module/lesson (comes free via the lesson FK join), type
and status — plus an AI pre-rating per item (feasibility, rework effort, one-line note)
to help prioritize.

**Schema additions on `feedback`:**
- `status text NOT NULL DEFAULT 'new'` CHECK in `('new','accepted','dismissed')` + `reviewed_at`/`reviewed_by`
- AI triage fields: `ai_feasibility`, `ai_effort`, `ai_note`, `ai_rated_at` (nullable — rating can lag submission). A separate `feedback_triage` table is the alternative if we'd rather keep the core row immutable.
- **No `type` column** (decided 2026-07-23): the learner form stays message-only — an extra
  field would suppress submissions, and at our volume the reviewer reads every quote anyway.
  If a classification later proves useful, the AI triage call can emit one as another
  `ai_*` field — no learner-facing change needed.

**Endpoints:** `GET /api/admin/feedback?status=&track_id=&project_id=` (joined with
lesson→module→track names) + `PATCH /api/admin/feedback/{id} {status}`.

**AI rating runtime:** an Anthropic API key is available (org-managed, direct Anthropic).
Remaining choices: it presumably lives as a Container App secret next to `jwt-secret`/
`acs-connection-string` (confirm), and the trigger — on-submit hook, scheduled job, or
admin-triggered batch script (cheapest start: a `backend/scripts/` batch like the
content_qa tooling, writing the `ai_*` columns; promote to a job later).

---

## 4. Dashboard / attention signals — no migration needed 🎉

The overview (funnel, stuck/inactive learners, maturity distribution) is derivable from
existing data:
- **last active** = max(`auth_sessions.last_used_at`) per user
- **activated** = `password_set` OR `external_id` set
- **assessed** = `surveys.status = 'complete'`
- **learning started / stalled** = `lesson_progress.completed_at` (latest = where they stalled)
- **maturity distribution** = survey results (already served per-user)

Work = one or two admin aggregate endpoints (e.g. `GET /api/admin/dashboard?project_id=`)
with real SQL aggregates — **not** N+1 loops. Definitions to agree: "stalled" threshold
(mock uses ~14 days without progress), "completed a track" (= all assigned lessons of
that track completed).

**Reminder email** ("Remind" button on stuck learners): new endpoint + ACS template,
same pattern as invite/reset emails.

---

## 5. Hygiene riding along (already in CODE-REVIEW.md, 2026-07-09)

- `GET /api/admin/users` N+1 (`services/admin_user_service.py`) — fix when the new People table lands
- Pagination on admin list endpoints (`/admin/users`, `/admin/learning`, and the new feedback list from day one)

---

## Explicitly NOT changing

- Roles (`admin` / `user+` / `user`), auth, and the iron rule (no endpoint outside `/admin/*` takes a user id)
- Assignment stays a **visibility filter, not access control** (documented design)
- Learner-side lock/prerequisite semantics
- Content endpoints & lesson editor (content authoring is out of scope for this redesign)

## Suggested phasing (each independently shippable)

1. **Assignments:** defaults table + inherit-on-invite + provenance + bulk-transpose endpoint (+ N+1/pagination fix) — unblocks the #1 pain
2. **Dashboard:** aggregate endpoint(s) + reminder email
3. **Feedback:** status/type columns + admin queue endpoints; AI triage batch as a fast follow

## Decisions (Aaron, 2026-07-23) — for your review/veto

1. **Defaults strategy: A (materialize on invite)** with an `assigned_via` provenance column; "apply to existing participants" as an explicit admin action.
2. **Defaults at track level only** — a default track implies all its modules and lessons; per-person tweaks handle exceptions.
3. **AI triage: PARKED** until after the new setup is live in production. The feedback queue itself (status column, accept/dismiss, admin list endpoints) still ships — the `ai_*` columns and the rating job come later. (An org-managed Anthropic API key is available when we pick this up; storage as a Container App secret to confirm then.)
4. **Funnel definitions per the mockup:** stalled = no lesson completed for ~14 days; completed a track = all *assigned* lessons of that track completed.

Also decided: **Email templates** get a first-class section in the new admin shell — no
backend change, the existing `routers/admin_email_templates.py` endpoints and editor
behavior are reused as-is.
