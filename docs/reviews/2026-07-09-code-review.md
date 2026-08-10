# AI Enablement Hub — Full Code & DB Review

**Date:** 2026-07-09
**Scope:** the live Azure rebuild (`AI ENABLEMENT HUB REBUILD/`) — backend (`backend/src`, ~6k LoC),
frontend (`frontend/src`, ~10k LoC excl. generated schema), database (models + Alembic + `db/` scripts),
and config/deploy/infra. The retired Supabase app (`../app/`) is out of scope.
**Method:** six parallel read-only reviews (backend architecture, backend security, backend
perf/correctness, frontend, database, config/deploy). No files were modified.

## Headline

The codebase is **unusually disciplined** — strict layering, exhaustive discriminated-union maps,
`SecretStr` throughout, pinned JWT algorithms (no alg-confusion), the authorization "iron rule" holds,
all SQL goes through the ORM (no injection surface), email templates HTML-escape input, and the two
load-bearing React `useCallback` identities are correct. **Nothing is Critical.** The findings are
concurrency, scale, and hygiene issues. The items most worth doing before the next scale-up / cutover
are the eight in the table below.

## Priority summary (do these first)

| # | Theme | Finding | Sev | Where |
|---|-------|---------|-----|-------|
| 1 | Async blocking | bcrypt hash/verify runs on the event loop → every login freezes all requests | High | `core/security.py` |
| 2 | Query scale | `GET /api/admin/users` is N+1 (one query per user) | High | `services/admin_user_service.py:88` |
| 3 | Concurrency | Single-use tokens & refresh rotation consumed non-atomically (TOCTOU) | Med | `services/token_service.py` |
| 4 | Script safety | Two `db/` scripts TRUNCATE / overwrite the **live** DB with only a README warning | High | `db/migrate_supabase_to_azure.py`, `db/sync_content_from_supabase.py` |
| 5 | Architecture | `AdminUserService` depends on another service (breaks the one hard rule) | High | `services/admin_user_service.py:34` |
| 6 | Frontend structure | Two `LearningPath` pages (~800 lines) with 3× duplicated DAG/zoom logic | Med | `pages/LearningPath.tsx` vs `LearningPathNew.tsx` |
| 7 | DB index | `lesson_progress.lesson_id` unindexed (seq-scan on every lesson delete) | Med | `db/models/assignment.py:86` |
| 8 | Info disclosure | Swagger `/docs` + `/openapi.json` publicly browsable in prod | Med | `main.py` |

---

## Theme 1 — Async event-loop blocking (High)

**1.1 — bcrypt runs synchronously on the event loop.** `core/security.py:32-40`
`hash_password` (`gensalt()` cost 12) and `verify_password` are ~200-300 ms of pure CPU and are
`await`ed directly in `UserService.authenticate` / `set_password` (`services/user_service.py:29,31,36`),
so each **login / set-password freezes the entire single-replica event loop** for the hash duration —
stalling health checks and every other concurrent request. This is the one blocking call that slipped
through: the codebase already wraps sync work in `run_in_threadpool` for ACS email
(`email_service.py:77`) and PyJWKClient (`entra_service.py:103`).
**Fix:** `await run_in_threadpool(bcrypt.hashpw / bcrypt.checkpw, ...)`.

---

## Theme 2 — Query performance & scale (High → Low)

**2.1 (High) — `GET /api/admin/users` is N+1.** `services/admin_user_service.py:88-93`
`_effective_maturity_map` calls `assigned_lesson_counts_by_module(user_id)` **once per user** in a loop.
Total page cost ≈ **N+7 queries** for N users (~207 round-trips at 200 users).
**Fix:** add `user_id` to the grouped count query, fetch all users' counts in one shot
(`WHERE UserLesson.user_id IN (...)` + `GROUP BY user_id, module_id`), assemble the map in Python.

**2.2 (Med) — `/learning/graph` issues 3 duplicate queries per request.**
`routers/learning.py:38`, `maturity_service.py:53`, `learning_service.py:47`
`effective_level(user)` and `graph(user.id, ...)` each independently run `list_tracks()`,
`list_modules()`, and `assigned_lesson_counts_by_module()` — so those three run **twice** per request
(~10 queries, 3 exact dupes). Note: can't `asyncio.gather` these (one shared per-request session);
de-duplication is the lever. `list_tracks/modules/prerequisites` are global and change only on admin
edits → good candidates for a short-TTL process cache.
**Fix:** compute the shared rows once and pass them into both computations.

**2.3 (Med) — DB: `lesson_progress.lesson_id` is unindexed.** `db/models/assignment.py:86-91`
It's the only child table whose content-side FK has no standalone index (its unique constraint only
covers `(user_id, …)`). Every `DELETE FROM lessons` cascade and every "who completed lesson X" query
does a **seq-scan of `lesson_progress`**. Its sibling `user_lessons` has `index=True` on `lesson_id` —
restore parity.
**Fix:** `index=True` on the column + migration `create_index("ix_lesson_progress_lesson_id", ...)`.

**2.4 (Med) — No pagination on admin list endpoints.**
`admin_user_service.list_users` / `learning_overview`, `user_repository.list_with_org_names:38`,
`list_for_learning:52`. Every row returned with no `LIMIT`/`OFFSET`; `_assignment_maps` full-table-scans
`user_tracks/modules/lessons`. Fine at internal scale, unbounded with tenant growth.
**Fix:** add `limit`/`offset` (or keyset) pagination; at minimum cap the assignment-map scans.

**2.5 (Med) — Survey completion writes across 4 separate transactions.**
`services/survey_service.py:71-116` — `surveys.update` → `set_user_tracks` → `set_user_modules` →
`set_user_lessons`, each committing internally. A failure mid-way leaves the user "scored" with partial
assignments. Root cause: every repo write commits internally, so services can't compose an atomic
multi-write. Mitigated today by idempotent on-conflict-do-nothing inserts (retry-safe), hence Med.
**Fix (structural):** give repos commit-less (flush-only) variants and let the service own one
`commit()` — a small unit-of-work seam that also fixes 3.x below.

**2.6 (Low) — Minor query cleanups.**
- `content_repository.py:171` `set_lesson_orders` issues M UPDATE round-trips in a loop (atomic, but M
  statements) → one bulk `UPDATE … CASE` / executemany.
- `learning_service.py:122,153` `lesson_ids_for_user` pulls **all** of a user's assigned lessons to test
  one module's membership → scope the query with `WHERE lesson_id IN (module's lessons)`.

---

## Theme 3 — Concurrency & atomicity (Medium)

All share one root cause: read-then-write with no atomic guard.

**3.1 — Single-use action/login tokens consumed non-atomically (TOCTOU).**
`services/token_service.py:127`, `repositories/auth_token_repository.py:36`
`consume_action_token` = `peek` (SELECT, check `consumed_at IS NULL`) then a separate `consume`
(UPDATE + commit). Two concurrent redemptions of the same invite/reset/`entra_login` code can both pass
the check before either commits. Blast radius low (a token normally has one holder; frontend has a
StrictMode `useRef` guard) but the "single-use" contract isn't actually enforced under races.
**Fix:** atomic `UPDATE auth_tokens SET consumed_at=now() WHERE id=:id AND consumed_at IS NULL RETURNING id`,
treat `rowcount==0` as already-consumed.

**3.2 — Refresh rotation race + no reuse detection.**
`services/token_service.py:74`, `repositories/auth_session_repository.py:34`
`refresh_pair` reads → checks `revoked_at IS NULL` → `revoke()` + mints new — non-atomically. Worse,
there's **no refresh-token reuse detection**: replaying an already-rotated token just fails silently
instead of revoking the token family (the RFC 9700 / OAuth BCP behavior). An attacker who steals and
rotates a refresh token keeps a live session; the victim simply re-logs-in, nothing flagged.
**Fix:** atomic conditional revoke on rotation; if a *revoked* (not merely expired) refresh token is
presented, revoke all of that user's sessions.

---

## Theme 4 — Backend architecture & cohesiveness (High → Low)

**4.1 (High) — Service depends on another service.** `services/admin_user_service.py:34` (wired
`core/dependencies/domain.py:116`). `AdminUserService.__init__` takes `TokenService` and calls it for
invite/reset — violating the standard's one non-negotiable rule ("services never call services"). The
irony: the same file's `_effective_maturity_map` carries a comment saying it *duplicates* maturity logic
specifically to avoid calling `MaturityService`. So the rule is enforced for maturity but broken for
tokens. **Fix (lowest churn):** return the user from `invite`/`reset_link` and issue the raw token in
the router (which already orchestrates email there).

**4.2 (Med) — Email-dispatch logic lives in the router.** `routers/admin_users.py:63-115`
`_email_the_link` + the `send_email` branch + `EmailStatus` derivation ("sent"/"failed"/"disabled"/
"skipped") is use-case logic in the HTTP edge, present there only because the service can't call
`EmailService` (same constraint as 4.1). Acceptable as a seam, but flag it — it's the second place the
no-service→service rule pushed logic upward. Resolve alongside 4.1 or document as the sanctioned
orchestration point.

**4.3 (Med) — Duplicated effective-maturity assembly.** `maturity_service.py:46-63` ≈
`admin_user_service.py:70-94`. Both build the identical `track_level`/`module_level` maps and call
`advance_level`; only the leaf is shared. **Fix:** promote the map construction into the shared pure
helper (`advance_level(base, tracks, modules, counts)`).

**4.4 (Low) — Auth routers aren't try/except-free.** `routers/auth.py:76-146`,
`routers/auth_entra.py:126-176`. The `AuthError` family has no handler in `main.py` (only
`NotFoundError`/`ConflictError`/`DomainError`/`ScoringError` are mapped), so these routers must catch to
avoid 500s — a deviation from the convention. Partly justified (login needs `WWW-Authenticate`; the
entra callback must 302 not JSON), but the plain-JSON cases (401 refresh, 404/410 redeem) could be
centralized. **Fix:** register an `AuthError` handler for the JSON cases; keep inline only where a
header/redirect is required — or document the deviation.

**4.5 (Low) — Two response-conversion styles.** `me.py`/`survey.py`/`admin_content.py` return raw ORM
models relying on `response_model=`, while `admin_org.py`/`admin_users.py` use explicit
`Response.model_validate(...)`. Both safe (no secret leaks). Pick one convention.

**4.6 (Low) — `_require_non_blank` validator copy-defined 3×.** `schemas/admin_org.py:22`,
`admin_content.py:22`, `admin_users.py:31` → hoist to `schemas/_validators.py`.

---

## Theme 5 — Dead code (Low)

Safe deletions, verified unreferenced:

- **Backend:** `db/base.py:22` `Base.to_dict` (no callers, template carry-over);
  `core/constants.py:34` `next_level` in `__all__` but only used internally (drop from `__all__`).
- **Frontend:** `QuizBlock.tsx:37` dispatches a `quiz-complete` CustomEvent nobody listens for (vestige;
  completion goes via `onComplete()` on the next line); `types/domain.ts` has 5 unused aliases
  (`TokenPair`, `JourneyResponse`, `SurveyResponse`, `LearningGraph`, `AdminLearningLesson`);
  three hand-rolled `Spinner` copies (`SetPassword.tsx:80`, `InviteRedirect.tsx:10`, `AuthCallback.tsx:44`)
  duplicate the shared `components/Spinner.tsx` — consolidate.

---

## Theme 6 — Frontend structure, correctness & re-render (Medium → Low)

**6.1 (Med) — Two `LearningPath` pages, heavily duplicated.** `pages/LearningPath.tsx` (680 lines,
routed `/learning/old`) and `LearningPathNew.tsx` (949 lines, routed `/learning`). Both are reachable,
but they duplicate the ASAP-rank DAG algorithm, the graph-load/filter effect, `isModuleUnlocked`, and
the zoom-compensated popover math (a **third** copy is in `ModulePopup.tsx:29`). `LearningPathNew` now
has the full edit mode that was the stated reason to keep `/learning/old` — so the old page +
`ModulePopup.tsx` may be fully superseded. **Action:** confirm with product whether `/learning/old` is
still needed; if not, deleting both removes ~800 lines and 3 copies of the zoom math.

**6.2 (Med) — Admin `loadProjectData` has no cancellation.** `Admin.tsx:102-138` — called imperatively
from `openProject`, no AbortController/request-id. Rapidly switching projects can apply an earlier
project's users/surveys over the current one. Low impact (admin tool) but a real race.
**Fix:** track a request id and ignore stale completions.

**6.3 (Low) — `LearningPath.tsx` is the one page using inline style objects** reconstructed every render
(`:329-677`), instead of the house `const s = {…} satisfies Record<string, CSSProperties>` pattern used
everywhere else. (Moot if 6.1 deletes it.)

**6.4 (Low) — Per-render work.** `LessonPage.tsx:46` re-runs the full MDX regex parse on every keystroke
in MDX mode (wrap in `useMemo`); `LearningPathNew.tsx:208-219` recreates `isDone`/`isUnlocked`/
`firstCurrent` each render inside deps-suppressed `useMemo`/effect — correct today but fragile; make them
`useCallback` so the dep arrays can be honest.

---

## Theme 7 — Web hardening & info disclosure (Medium → Low)

**7.1 (Med) — Swagger `/docs`, `/redoc`, `/openapi.json` are anonymously browsable in prod.** `main.py`
The full API surface (incl. every `/api/admin/*` route + request shapes) is disclosed to unauthenticated
visitors; the security-headers middleware even whitelists `/docs` for the jsdelivr CDN. Endpoints are
auth-guarded, so this is info-disclosure, not access. CLAUDE.md treats `/docs` as intentionally live —
**confirm intent**; if not needed in prod, pass `docs_url=None, redoc_url=None, openapi_url=None` when
`app.env == "prod"`.

**7.2 (Low — RE-ASSESSED 2026-07-09, largely a non-issue) — IP rate limits and proxy headers.**
`routers/auth.py:135`, `routers/auth_entra.py:64,124,169`. The original finding claimed all clients
collapse into the ingress IP. **That's wrong:** `startup.py` runs uvicorn with `proxy_headers=True` +
`forwarded_allow_ips="*"`, so `request.client.host` is already resolved from `X-Forwarded-For` — the
limiter keys on the real client IP. The only residual is that `forwarded_allow_ips="*"` trusts XFF from
anyone, so a client *could* spoof the header to poison/evade its own limit — a hardening nuance, not the
DoS described. **Fix (optional):** set `forwarded_allow_ips` to the actual trusted ACA/WAF proxy hop
count once known. Not worth doing before that infrastructure is finalized.

**7.3 (Low) — Assorted hardening.**
- `core/configs/auth.py:17` — `AUTH__JWT_SECRET` has no min-length/entropy validation (short secret →
  HS256 offline-forgeable); add a ≥32-byte validator. Also rotate the dev secret that leaked to a
  transcript (dev-only blast radius, per CLAUDE.md).
- No rate limit on `POST /api/auth/refresh` (256-bit tokens, so low) and `login`/`set-password` limits
  enable targeted per-victim lockout (short window, in-process).
- `main.py:117` CSP could add `base-uri 'self'` + `object-src 'none'`; rate-limiter store never evicts
  keys (unbounded under a flood — documented single-replica design).
- PII (user email + Entra oid) logged at info/warning in `entra_service.py:136,140,152` and recipient
  address in `email_service.py:79` — minimize (hash or drop email, keep oid).
- `renderInline.tsx:11` builds `<a href>` from `[text](url)` markdown with no protocol allowlist —
  `[x](javascript:…)` would render a `javascript:` link. Admin-authored content so low; add an
  `http(s)|mailto` allowlist.

---

## Theme 8 — Client-side security posture (High note → Low)

**8.1 (High note, low real risk) — Tokens in `localStorage`.** `api/tokens.ts:11-22` — access + 14-day
refresh token are readable by any origin script (XSS → full exfiltration). **Strong mitigations exist:**
no `dangerouslySetInnerHTML` anywhere, all content is admin-authored, CSP ships in prod. So real-world
risk is low, but it's the headline threat-model note — acknowledge explicitly, or move the refresh token
to an httpOnly cookie in a future pass.

**8.2 (Low, documented) — `?edit=true` renders the editor to non-admins.** `LessonPage.tsx:21,213` —
`editMode` inits from the URL param without an `isAdmin` gate (saves 403 server-side via the admin-only
PATCH). Already accepted in CLAUDE.md; cheap to gate the render on `isAdmin`.

---

## Theme 9 — Destructive DB scripts (High)

Now that cutover is complete and Azure is the sole authoritative DB, these are the sharpest edges in the
repo — their only guard is prose in `db/README.md`.

**9.1 (High) — `migrate_supabase_to_azure.py:162` TRUNCATEs the live DB.** A bare
`uv run migrate_supabase_to_azure.py` goes straight to `TRUNCATE {13 app tables + auth_tokens +
auth_sessions} CASCADE` and reloads a frozen, stale snapshot — erasing all post-cutover content edits,
every set password, and all learner progress. `--check-only` is opt-*in*.
**Fix:** invert the default (no-arg = dry run); require an explicit
`--i-understand-this-truncates-prod` flag and/or refuse to run if any `users.password_set = true` exists
(proves real usage started).

**9.2 (Med) — `sync_content_from_supabase.py --apply` would silently unwind the maturity split
(`b4e5f6a7c8d9`).** It matches by id and would rename "General I" → "General", reset `sort_order`, move
the 3 split modules' `track_id` back, and **delete** any `module_prerequisites` edge the stale snapshot
lacks. Dry-run is the default (good), but `--apply` has no further guard.
**Fix:** same destructive-confirm gate; ideally refuse to run if a `General II` track exists.

---

## Theme 10 — Data integrity & schema (Medium → Low)

**10.1 (Med) — `module_prerequisites` allows cyclic & cross-track edges.** `db/models/learning.py:89`
The only DB constraint is `not_self`. A cyclic/cross-track row (via admin API or the sync script) would
**lock all dependents forever with no edge drawn to explain why** — CLAUDE.md lists this as an accepted
quirk, but it's a real integrity gap the DB can't express. Cycles can't be caught by a CHECK.
**Fix:** add application-level cycle detection on the prerequisite-insert path (service layer), since the
DB can't guard it.

**10.2 (Low) — assorted.**
- ~~`learning_service.py:54` `LEVEL_RANK[required_level]` uses subscript (not `.get`) → `KeyError`.~~
  **RE-ASSESSED 2026-07-09, non-issue:** migration `b4e5f6a7c8d9` makes `tracks.required_level` `NOT NULL`
  with `CHECK IN ('explore','practitioner','integrator')`, so the value is always a valid `LEVEL_RANK`
  key — the KeyError is unreachable from DB data. No change needed.
- `learning_service.py:160` "next lesson" uses strict `sort_order > current`; `sort_order` isn't unique
  (`max+1` creation has a TOCTOU gap, reorder uses 0-based indices), so tied siblings get skipped and
  disagree with `module_lessons`' `(sort_order, id)` ordering. Compare by the `(sort_order, id)` tuple
  consistently, or add a unique `(module_id, sort_order)` constraint.
- No index on `auth_tokens.expires_at` / `auth_sessions.expires_at` (cleanup seq-scans; tables tiny).
- `curricula.created_at` nullable while all other `created_at` are NOT NULL (cosmetic, data-only table).
- `updated_at` uses ORM `onupdate` (not a DB trigger) → raw-SQL/script edits won't bump it.

**Verified correct (no action):** cascade tree is complete (module/track/lesson deletes leave no
orphans); `users.company_id = RESTRICT` correctly blocks company deletion; all migrations are reversible
and the NOT-NULL-on-populated-table step in `b4e5f6a7c8d9` is safe; `provision_roles.py`'s
`ALTER DEFAULT PRIVILEGES … TO ai_hub_app` (run as owner) means future migration tables are auto-grantable
— the memory-noted "new tables lack grants" pain is solved; backfills are idempotent; no hardcoded
secrets in any `db/*.py`.

---

## Theme 11 — Config & dependency hygiene (Medium → Low)

**11.1 (Med) — `DatabaseSettings` silently defaults to local SQLite.** `core/configs/database.py:20,26`
(`protocol = SQLITE`, `name = "app.db"`). If the `DATABASE__*` env block were ever missing (typo'd secret
name), the app boots against an ephemeral `app.db` instead of failing loudly. Prod is protected only by
`containerapp.yaml` setting the protocol explicitly. It's a template leftover — the app never runs on
SQLite. **Fix:** make `protocol` required (or default `postgresql`) so misconfig fails fast.

**11.2 (Med) — `azure-communication-email>=1.1.0` is the only unbounded dep.** `pyproject.toml:23` —
every other dep uses `~=`. `uv.lock` + `--frozen` makes prod deterministic, but a re-lock could pull a
breaking major. **Fix:** pin `~=1.1`.

**11.3 (Low) — dep/tooling nits.** `httpx` declared in both main and dev deps (`pyproject.toml:21,31`) —
drop the dev copy; `aiosqlite` dev dep is a leftover of the abandoned SQLite path — drop if unused.
Base images are tag-pinned not digest-pinned (`Dockerfile:7,17,29`) → cloud rebuilds aren't reproducible;
consider `@sha256:` pins. ESLint uses `recommended` not `recommendedTypeChecked`, so `no-floating-promises`
/ `no-misused-promises` aren't enforced on an async-heavy codebase; revisit `noUncheckedIndexedAccess`
(off, documented) once parity is reached. `deploy.ps1:28` picks the newest ACR run via `--top 1` (can race
if two builds queue together). `startup.py:3` comment says "distroless" but the runtime is `slim-bookworm`
(doc nit).

**Verified good (no action):** no real secret in any committable file (`.env`/`db/.env` are gitignored
*and* dockerignored; `containerapp.yaml` uses `__PLACEHOLDER__` tokens; `deploy-initial.ps1` reads secrets
at runtime and cleans up in `finally`); `.dockerignore` correctly lists every dir bare **and** with `/**`
(the az-CLI trailing-slash bug); correct 3-stage non-root Docker build with lockfile-first caching; all
settings `frozen=True` with `SecretStr`; `AUTH__JWT_SECRET` has no default (fails loudly); both-or-neither
enforced structurally for `entra`/`email`; CORS has no wildcard fallback and `allow_credentials` is off
(correct for a bearer API); migration-on-startup is race-safe under the min=max=1 replica design.

---

## Confirmed-clean areas (checked, no action)

- **Auth:** JWT algorithms pinned (`HS256` access, `RS256` id_token, no `verify=False`); Entra id_token
  fully validated (aud/iss/exp/nonce, `oid` identity, 60s leeway); token `typ` separation; PKCE S256 +
  `secrets.compare_digest` state; state cookie HttpOnly/SameSite=Lax/Secure-in-prod; no open redirect
  (all targets from config); the authorization iron rule holds (no non-admin endpoint takes a user id;
  every `/admin/*` route carries `require_admin`); bcrypt with timing-equalized dummy hash + no user
  enumeration; deactivation/role changes take effect next request (user row reloaded each request).
- **Injection:** zero raw SQL — all ORM/Core constructs, no `text()`/f-string SQL.
- **Backend architecture:** downward-only layering respected everywhere except finding 4.1; every module
  has `from __future__ import annotations` + `__all__`; DI providers correctly runtime-import annotation
  types (the FastAPI silent-422 gotcha is avoided everywhere).
- **Frontend:** single-flight refresh is sound; the load-bearing `onQuizComplete`/`onLiveChange`
  `useCallback` identities are correct; `cancelled` cleanup flags in every fetch effect; AuthCallback's
  StrictMode `useRef` guard is correct; `as` casts are confined to justified boundaries, no `any`.
- **Perf non-issues:** ACS client + PyJWKClient correctly in `run_in_threadpool`; JWKS `@lru_cache`d;
  Entra exchange uses async `httpx`; `scoring.py` is pure; `create_module` shift+insert is atomic; user
  delete relies on a single-DELETE FK cascade.
