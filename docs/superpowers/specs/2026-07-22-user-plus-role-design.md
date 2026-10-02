# `user+` role — design

> **Superseded 2026-10-01:** `user+` was removed by
> `2026-10-01-project-scoped-admin-design.md` (existing accounts became `user`).

**Date:** 2026-07-22
**Status:** approved, implementing

## Problem

Today there are two roles: `admin` and `user`. Admins bypass every learning-path
lock (prerequisites, the Introduction gate, maturity gating) but also hold full
admin powers (the `/admin` panel, content editing). There is no way to give a
learner the freedom to roam their learning path without also handing them the
admin panel and content-editing rights.

We want a third role, **`user+`**: an admin-style lock bypass on their own
assigned content, with **zero** admin powers.

## Behaviour

A `user+`:

- **Sees the same content a normal learner is assigned** — no more, no less.
  Visibility is unchanged; only the locks change. (This mirrors admins, who also
  only see their own assigned tracks.)
- **Bypasses all learning-path locks** on that assigned content: module
  prerequisites, the Introduction gate, and maturity-level gating — identical to
  how an admin behaves on `/learning`.
- **Has no admin powers.** The `/admin` route, the Admin nav link, the lesson
  editor, and learning-path edit mode all stay gated on `role === 'admin'`, so a
  `user+` is a normal user everywhere outside the lock bypass. Every `/admin/*`
  and lesson-edit endpoint returns 403 for a `user+`, exactly as for a `user`.
- **JourneyHome component tiles** (assessment / learning / interview) behave for
  a `user+` exactly as for a normal user — an admin still controls whether the
  Learning section is open for the project. (Admins don't bypass these either;
  they are a separate project-level gate, not a "learning-path requirement".)

## Implementation

### Data model & backend

- **Role becomes a 3-value enum:** `'admin' | 'user+' | 'user'`, stored as the
  literal string `'user+'` (the admin badge already renders the raw role value).
- **Migration** widens the `users.role` CHECK constraint (`ck_users_role`) from
  `role IN ('admin', 'user')` to `role IN ('admin', 'user+', 'user')`. Hand
  written, no autogenerate (CHECK text isn't diffed). Down-revision =
  `d8e9f0a1b2c3` (current head). Applied to the dev Azure DB after approval; prod
  auto-applies on next deploy via `startup.py`'s `alembic upgrade`.
- The `User` model's `CheckConstraint` is widened to match — this is what the
  integration test DB (built from `Base.metadata`) enforces.
- `RoleUpdateRequest.role` literal → `Literal['admin', 'user+', 'user']`.
- **`require_admin` is unchanged** (`role != 'admin'` → 403). No new backend
  permission surface; the authz iron rule is untouched.
- `UserProfileResponse.role` / `AdminUserOut.role` are already `str` — no change.

### Frontend

- `Role` type → `'admin' | 'user+' | 'user'` (`AuthContext.tsx`).
- In `LearningPathNew.tsx`, add `canBypassLocks = role === 'admin' || role === 'user+'`
  and swap the two lock checks (`isUnlocked`, `isTrackLocked`) from `isAdmin` to
  `canBypassLocks`. `isAdmin` stays strictly `role === 'admin'` for edit mode and
  the add-track/module buttons.
- `isAdmin` / `role === 'admin'` is unchanged everywhere else: `/admin` route
  guard (`App.tsx`), Admin nav link (`AppNav.tsx`), lesson edit button
  (`LessonPage.tsx`).
- `schema.d.ts` `RoleUpdateRequest.role` enum patched to `"admin" | "user+" | "user"`.

### Admin UI — role dropdown

Replace the admin↔user toggle button in `ProjectDetailView.tsx` with a `<select>`
styled as the badge, offering **User / User+ / Admin**. Selecting a value fires
the existing `PATCH /api/admin/users/{id}` with the new role. `handleRoleToggle`
becomes `handleRoleChange(userId, newRole)`, keeping the optimistic-update +
`togglingRole` disabled/spinner pattern. `user+` gets a distinct middle-shade
badge colour between the dark admin badge and the grey user badge.

## Out of scope / non-goals

- No change to what content is assigned or visible.
- No `user+` bypass of the JourneyHome component tiles.
- No backend access-control change (locks remain a frontend visibility concern,
  per the existing design).
