# Frontend Rebuild Design — AI Enablement Hub (React 18 + TypeScript + Vite)

Perspective: Frontend Architect. Target: `c:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD\frontend\`. Old app stays untouched at `app/` for side-by-side parity checks. Current frontend is 49 source files, ~7,000 LOC, all JSX + inline style objects.

---

## 1. Scaffold + Project Structure

Scaffold with `npm create vite@latest frontend -- --template react-ts` (Vite 6, React 18 pinned — do NOT let it pull React 19; pin `react@^18.3.1 react-dom@^18.3.1` to match old app and framer-motion behavior).

Dependencies (keep the old app's minimal footprint):
- runtime: `react@18`, `react-dom@18`, `react-router-dom@^6` (stay on v6 — same guard semantics as old `App.jsx`), `framer-motion@^12`, `openapi-fetch`
- dev: `typescript`, `vite`, `@vitejs/plugin-react`, `openapi-typescript`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`

```
frontend/
├── index.html                     # port of app/index.html (Google Fonts links, #root)
├── package.json                   # scripts: dev / build / preview / gen:api / lint / typecheck
├── vite.config.ts                 # port 5173, proxy: { '/api': 'http://localhost:8000' }
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── eslint.config.js               # flat config: ts-eslint recommended + react-hooks + react-refresh
└── src/
    ├── main.tsx
    ├── App.tsx                    # routes + guards (Spinner, ComingSoon stay here)
    ├── index.css                  # copied verbatim from app/src/index.css (design tokens)
    ├── api/
    │   ├── schema.d.ts            # GENERATED from FastAPI /openapi.json (committed to repo)
    │   ├── client.ts              # openapi-fetch instance + auth/refresh middleware
    │   └── tokens.ts              # localStorage token store (single seam for Entra later)
    ├── types/
    │   ├── contentBlocks.ts       # hand-written discriminated union (JSONB boundary)
    │   └── domain.ts              # aliases re-exported from schema.d.ts (User, Track, …)
    ├── contexts/
    │   └── AuthContext.tsx
    ├── lib/
    │   ├── constants.ts           # DEFAULT_LOCKED/DEFAULT_HIDDEN, ComponentKey
    │   ├── surveyOptions.ts       # `as const`, derive code unions
    │   ├── contentBlocks.ts       # factories (typed against types/contentBlocks.ts)
    │   ├── mdxParser.ts           # (mdx: string) => ContentBlock[]
    │   └── blocksToMdx.ts         # (blocks: ContentBlock[]) => string
    ├── pages/
    │   ├── Login.tsx  SetPassword.tsx  InviteRedirect.tsx
    │   ├── JourneyHome.tsx  Assessment.tsx  LearningPath.tsx  LessonPage.tsx
    │   ├── Admin.tsx
    │   └── admin/  (ProjectsView, ProjectDetailView, SetupView, UserPanel,
    │                SurveyResults, adminStyles.ts, adminHelpers.tsx)
    └── components/
        ├── AppNav.tsx  ModulePanel.tsx  ModulePopup.tsx
        ├── AddTrackModal.tsx  AddModuleModal.tsx
        └── lesson/  (LessonView.tsx, LessonEditor.tsx, blocks/*, editors/*)
```

**tsconfig strictness**: `"strict": true`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax` (the Vite template defaults). Leave `noUncheckedIndexedAccess` OFF for the initial port — the quiz `options[correct]`, survey step arrays, and graph code index arrays constantly; enabling it during a parity port produces hundreds of non-bug friction points. Revisit after parity is reached.

**Vite dev proxy is load-bearing**: `/api → http://localhost:8000` means the browser only ever sees one origin in dev AND prod, so no CORS configuration is needed on FastAPI for the happy path, and token handling behaves identically in both environments. Old app runs on port 3000, new one on 5173 — side-by-side works out of the box.

`package.json` script: `"gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts"` — run whenever backend models change; commit the output so the frontend builds without a live backend.

---

## 2. API Client Strategy

**Recommendation: `openapi-typescript` (type generation only) + `openapi-fetch` (tiny typed runtime, ~6 kB), NOT a full generated client (@hey-api/openapi-ts), NOT a hand-written wrapper.**

Rationale:
- FastAPI's OpenAPI schema is authoritative and free. Hand-writing ~35 endpoint types duplicates the Pydantic models and WILL drift — this rebuild's biggest risk is silent contract mismatch between the new backend and new frontend built in parallel. Generated types turn drift into compile errors.
- `@hey-api/openapi-ts` generates a full SDK (services, per-endpoint functions, many files) — over-engineered for ~35 endpoints and 6 users, and its generated code is harder to thread custom refresh logic through.
- `openapi-fetch` is one `createClient<paths>()` call; every `client.GET('/api/admin/users', { params })` is fully typed for path, query, body, and response from `schema.d.ts`, and it has a middleware API that's exactly the right seam for auth. Zero codegen of executable code.

One caveat to hand to the backend plan: `lessons.content_blocks` is JSONB. The backend should either define the Pydantic discriminated union (then the generated type is complete) or type it as `list[dict]` — in which case the frontend casts to the hand-written `ContentBlock[]` union at the client boundary (one cast, in a helper in `api/client.ts`). Plan for the cast; upgrade if backend types it.

### Token handling

**Recommendation: access token AND refresh token in `localStorage`.** Rationale for this app specifically:
- Internal tool, 6 users, 4 companies; the old app already stores the Supabase session in localStorage (supabase-js default), so this is no security regression.
- The old deployment's CSP (`script-src 'self'`, no third-party scripts) carries over — the XSS surface that makes localStorage risky is already minimized. Lesson content is admin-authored and rendered through React (no `dangerouslySetInnerHTML` in the block renderers).
- Cookies would require CSRF protection machinery on FastAPI and careful `SameSite`/`Secure` handling across the dev-proxy setup; that's real backend complexity for negligible gain here.
- Survives reload with zero network round-trip; trivially inspectable when debugging.
- The Entra seam: all storage access goes through `src/api/tokens.ts` (`getAccessToken / getRefreshToken / setTokens / clearTokens` + a `subscribe(cb)` for logout broadcast). When Entra ID lands, MSAL's token acquisition replaces this module and the middleware calls `acquireTokenSilent` instead — nothing else changes.

### Auth middleware (in `api/client.ts`)

- `onRequest`: attach `Authorization: Bearer <access>` except for `/api/auth/login`, `/api/auth/refresh`, `/api/auth/set-password`, `/api/invite/*`.
- `onResponse`: on 401 (and not already a refresh/login call), run a **single-flight refresh** — one shared in-module `refreshPromise` so N concurrent 401s trigger one `POST /api/auth/refresh`; retry the original request once with the new token. If refresh fails: `clearTokens()` and notify subscribers → AuthContext sets session to null → router redirects to `/login`.

### AuthContext reimplementation (no supabase.auth)

State shape stays intentionally identical to the old context so consuming pages port mechanically:

```ts
interface AuthState {
  session: boolean | undefined            // undefined = restoring, false = logged out, true = logged in
  user: UserProfile | null | undefined    // { id, first_name, last_name, role, company_id, project_id, password_set }
  role: 'admin' | 'user' | null
  passwordSet: boolean | undefined
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  markPasswordSet: () => void
  refreshProfile: () => Promise<void>
}
```

- **login**: `POST /api/auth/login {email, password}` → `{ access_token, refresh_token, user }` → `setTokens`, set user/passwordSet from response (one round-trip, no separate profile fetch).
- **session restore on reload**: on mount, if `getAccessToken()` exists → `GET /api/auth/me` → user profile. 401 is handled transparently by the refresh middleware; if that fails, tokens are cleared and state becomes logged-out. No token → logged-out immediately. This replaces `getSession()` + the `users` table SELECT keyed on `auth_id` (that column is gone; `/api/auth/me` resolves from the JWT `sub` = internal user UUID).
- **logout**: `POST /api/auth/logout` (backend revokes refresh token), `clearTokens()`, null state. AuthContext also subscribes to `tokens.ts` so a middleware-forced logout updates React state.
- **`isRecovery` is deleted.** It existed only because Supabase delivered recovery sessions via an auth event. In the new design the invite/reset credential is an opaque token **in the URL**, not a session — so `App.tsx`'s gate simplifies to `needsPassword = session && passwordSet === false` (kept as a defensive gate; see SetPassword below, where the primary flow never hits it because the redeem endpoint sets the password and logs in atomically).
- **password_set gate**: unchanged routing logic in `App.tsx` (`/` redirects to `/set-password` when `needsPassword`).

**New invite/reset flow (frontend contract for the backend plan):**
1. Admin clicks invite/reset in UI → `POST /api/admin/invite` / `POST /api/admin/reset-link` → returns `{ link: "<APP_URL>/invite/<token_id>" }` — admin copies it manually, same as today.
2. Invitee opens `/invite/:id` → `InviteRedirect.tsx` calls `GET /api/invite/{id}` → `{ token }` (self-issued, single-use, 7-day TTL — replaces stored Supabase action links) → `navigate('/set-password?token=…')`. 410 → "expired" UI, 404 → "invalid" UI (both exist today, port them).
3. `SetPassword.tsx` in token mode → `POST /api/auth/set-password {token, password}` → backend validates token, sets hash, sets `password_set=true`, consumes token, **returns login tokens + user** → frontend stores tokens, navigates `/`. This folds the old `supabase.auth.updateUser` + `POST /api/user/complete-password-setup` two-step into one atomic call.

---

## 3. Port Map (file by file)

Legend: **M** = mechanical (JS→TS + client swap only), **R** = rework. Line counts from the old app.

### lib/ (port first — zero dependencies)

| Old file | New | Effort | Notes |
|---|---|---|---|
| `lib/supabase.js` | — | **dropped** | replaced by `api/client.ts` + `api/tokens.ts` |
| `lib/migrateMdxToBlocks.js` (81) | — | **dropped** | dead + broken (context.md D1) — do not port |
| `lib/constants.js` | `lib/constants.ts` | M | `ComponentKey = 'assessment' \| 'learning' \| 'interview'`; `Record<ComponentKey, boolean>` |
| `lib/surveyOptions.js` (148) | `lib/surveyOptions.ts` | M | `as const` option arrays; derive code unions (`C1Code = typeof C1_OPTIONS[number]['code']`) — these unions feed the `SurveyResponse` type |
| `lib/contentBlocks.js` (63) | `lib/contentBlocks.ts` | M | factories return members of the union; `BLOCK_TYPES` `as const`; `BLOCK_FACTORIES: Record<ContentBlock['type'], () => ContentBlock>` |
| `lib/mdxParser.js` (92) | `lib/mdxParser.ts` | M | `(mdx: string) => ContentBlock[]` |
| `lib/blocksToMdx.js` | `lib/blocksToMdx.ts` | M | inverse signature |

**The key type of the codebase** — `types/contentBlocks.ts` (verified against `lib/contentBlocks.js`, which has **7** types including `question`, one more than context.md lists):

```ts
export type HeadingBlock    = { id: string; type: 'heading'; level: 1 | 2 | 3; text: string }
export type ParagraphBlock  = { id: string; type: 'paragraph'; text: string }
export type CalloutBlock    = { id: string; type: 'callout'; text: string }
export type Card            = { id: string; title: string; body: string }
export type CardGroupBlock  = { id: string; type: 'card_group'; cards: Card[] }
export type QuizQuestion    = { id: string; q: string; options: string[]; correct: number; explanation: string }
export type QuizBlock       = { id: string; type: 'quiz'; questions: QuizQuestion[] }
export type QuestionBlock   = { id: string; type: 'question'; prompt: string }
export type WhitespaceBlock = { id: string; type: 'whitespace'; size: 'sm' | 'md' | 'lg' }
export type ContentBlock =
  | HeadingBlock | ParagraphBlock | CalloutBlock | CardGroupBlock
  | QuizBlock | QuestionBlock | WhitespaceBlock
```

This union makes `LessonView`'s `RENDERERS` map, every `editors/*` component, `mdxParser`, and `blocksToMdx` exhaustively checked (`switch (block.type)` with `never` default).

### Core

| Old file | Effort | What changes |
|---|---|---|
| `main.jsx` → `main.tsx` | M | — |
| `App.jsx` (80) → `App.tsx` | R (small) | drop `isRecovery` from gate; routes identical otherwise (Spinner/ComingSoon port verbatim) |
| `contexts/AuthContext.jsx` (63) → `AuthContext.tsx` | **R (full rewrite)** | see §2 — same provider value shape, new internals |

### Pages

| Old file | Effort | Supabase → API mapping |
|---|---|---|
| `Login.jsx` (242) | M | `auth.signInWithPassword` → `useAuth().login()`; rest is branding/styles |
| `SetPassword.jsx` (207) | **R** | two modes: token mode (`?token=` in URL) → `POST /api/auth/set-password`; authenticated fallback (password_set=false) → same endpoint with Bearer instead of token. Removes `auth.updateUser`, `auth.signOut`, `POST /api/user/complete-password-setup` |
| `InviteRedirect.jsx` (63) | R (small) | `GET /api/invite/{id}` → now returns `{token}`; `navigate('/set-password?token=…')` instead of `window.location.href = supabaseLink`; keep expired/invalid states |
| `JourneyHome.jsx` (402) | M + cleanup | 2 queries (`project_component_settings`, `survey_responses` status) → one `GET /api/me/journey` → `{ components: Record<ComponentKey,{hidden,locked}>, survey_status: 'none'\|'in_progress'\|'complete' }`. **Delete dead nav styles s.nav…s.dropdownDivider (~40 lines, D2).** Add `cancelled` flag in effect (A5) |
| `Assessment.jsx` (967) | M (large) | `SELECT survey_responses` → `GET /api/survey/me`; step-by-step `upsert` → `PUT /api/survey/me` (backend upserts on user_id); `POST /api/survey/complete` unchanged. Define `SurveyResponse` from generated schema (codes typed via surveyOptions unions, `c5_codes: C5Code[]` for the text[] column). Rendering/stepper/intro code ports 1:1; extracting `renderIntro` (A3) is optional, not required for parity |
| `LearningPath.jsx` (654) | M + aggregate | 7 queries (tracks, user_tracks, modules, user_modules, module_prerequisites, lessons count, lesson_progress) → **one** `GET /api/learning/path` → `{ tracks, assigned_track_ids, modules (with col_offset), assigned_module_ids, prerequisites: [{module_id, prerequisite_module_id}], lesson_counts: Record<moduleId, number>, completed_lesson_counts: Record<moduleId, number> }`. `buildGraph`, zoom, SVG, framer-motion port verbatim; type the graph node/edge shapes |
| `LessonPage.jsx` (438) | M + aggregate | 9 queries → `GET /api/lessons/{id}` aggregate → `{ lesson (with content_blocks), module, siblings: [{id,title,sort_order}], completed_lesson_ids, answers, next_lesson_id, next_module_first_lesson_id }` (backend computes prefetch targets — also fixes B4); mark complete → `POST /api/lessons/{id}/complete { answers }`; admin content save → `PUT /api/lessons/{id} { content_blocks }` |
| `Admin.jsx` (372) | M | already API-based; endpoints keep identical paths/shapes on FastAPI (companies, users, components, learning, survey, reset-link). Only supabase query (`tracks` SELECT) → `GET /api/tracks`. Replace both hand-rolled `authH` patterns with the api client (fixes A2 for free). Keep the God-component structure for parity (A1 noted, defer) |
| `admin/ProjectsView.jsx` | M | props-only, no I/O |
| `admin/ProjectDetailView.jsx` (328) | M | `POST /api/admin/invite` → same shape, `{link}` copied manually — unchanged UX |
| `admin/SetupView.jsx` (159) | M | `POST /api/admin/companies` (company + project variants) — unchanged |
| `admin/UserPanel.jsx` (117) | M | props-only |
| `admin/SurveyResults.jsx` (136) | M | type the admin survey object (all rung/band/code fields) from generated schema |
| `admin/adminStyles.js` (257) → `.ts` | M + cleanup | `satisfies Record<string, React.CSSProperties>`; **delete dead s.nav/s.avatar/s.dropdown etc. (D3), KEEP s.navBadge, s.navDivider, s.navTabs, s.navTab, s.navTabActive, s.navTabInactive** |
| `admin/adminHelpers.jsx` → `.tsx` | M | type LevelBadge/BandBadge/RungPill props from score unions |

### Components

| Old file | Effort | Mapping |
|---|---|---|
| `AppNav.jsx` (93) | M | `auth.signOut()` → `useAuth().logout()` |
| `ModulePanel.jsx` (192) | M + API | lessons list → `GET /api/modules/{id}/lessons`; create → `POST /api/modules/{id}/lessons`; delete → `DELETE /api/lessons/{id}`; reorder → **one** `PUT /api/modules/{id}/lessons/order { lesson_ids: string[] }` (replaces N parallel updates — fixes B5) |
| `ModulePopup.jsx` (108) | M + API | 2 queries → `GET /api/modules/{id}/lessons?progress=me` → `{ lessons: [{id}], completed_ids }` |
| `AddTrackModal.jsx` (124) | M + API | insert → `POST /api/tracks { name, track_type, color }`; backend assigns sort_order (fixes A4 for tracks) |
| `AddModuleModal.jsx` (165) | M + API | 4 queries → `GET /api/tracks`, `GET /api/tracks/{id}/modules`, then **one** `POST /api/modules { track_id, title, col_offset, after_module_id?, prerequisite_ids: string[] }` — backend computes sort_order and inserts prerequisites atomically (addresses A4/DB6) |
| `lesson/LessonView.jsx` | M | `RENDERERS: { [K in ContentBlock['type']]: FC<{block: Extract<ContentBlock,{type:K}>}> }` |
| `lesson/LessonEditor.jsx` (235) | M | typed block array ops; MDX import via `mdxParser.ts` |
| `lesson/blocks/*` (7 renderers + renderInline) | M | each typed to its union member; QuizBlock keeps quiz-gating callback typed `(allCorrect: boolean) => void` |
| `lesson/editors/*` (7 editors) | M | each typed to its variant, `onChange: (b: XBlock) => void` |

**Do not port**: `lib/migrateMdxToBlocks.js`, the dead nav style objects in JourneyHome and adminStyles, and `lib/supabase.js`.

---

## 4. State / Data-Fetching

**Keep plain `useState` + `useEffect` load functions, typed. Do NOT introduce TanStack Query.**

Justification for this app: 6 users; no shared cache needs (each page owns disjoint data); no background refetch/stale-while-revalidate requirements; no pagination/infinite scroll; no optimistic-update complexity worth abstracting (the two "optimistic" spots — admin toggles and lesson complete — are 5-line hand-rolled patterns that already work). TanStack Query would add a dependency, a provider, queryKey design, and cache-invalidation reasoning to every one of ~20 files during a port whose success metric is behavioral parity. The aggregate endpoints (§3) already remove the request waterfalls that would have been the one real argument for it.

Two small disciplines instead:
1. Every fetch effect gets the `let cancelled = false` cleanup pattern (already used in `LessonPage.prefetch`; fixes A5 systematically).
2. A 10-line `useLoad<T>(fn, deps)` helper in `lib/` if repetition grates — optional, decide during the port, don't pre-build.

If the app later grows real caching needs, TanStack Query can be introduced page-by-page; nothing in this design blocks it.

---

## 5. Styling

**Port as-is: inline style objects typed with `satisfies Record<string, React.CSSProperties>`, plus the verbatim-copied `index.css` token file. Do NOT migrate to CSS modules now.**

Reasoning: visual parity is a hard requirement and inline objects are the single highest-fidelity way to guarantee it — the ported style object is diffable line-by-line against the old file. CSS-module migration changes the cascade (class specificity, hover handling — the old app does hovers via a mix of CSS utility classes in `index.css` and JS state), which is exactly where subtle regressions breed, across all ~49 files at once. The rebuild already carries JS→TS + API-swap risk; don't stack a styling rewrite on top.

TypeScript makes the pattern strictly better than today: `satisfies Record<string, React.CSSProperties>` catches typo'd properties and invalid values while preserving literal types, and dead style keys become findable. Use `satisfies` (not `: Record<…>` annotation) so per-key autocomplete survives.

Carry-over notes: copy `index.css` exactly (tokens, reset, hover utility classes, font imports in `index.html`); keep the D5 observation (tokens defined but underused) as-is — cleaning it is out of scope for parity. The eventual CSP for the Azure deployment will still need `style-src 'unsafe-inline'` (S4) — acceptable, unchanged from today.

---

## 6. Build Order + Parity Verification

Port in dependency order; each phase leaves the app compiling and runnable.

**Phase 0 — Scaffold**: Vite react-ts template, tsconfig/eslint, `index.css` + `index.html` copied, empty route shell rendering Spinner. Generate `schema.d.ts` from the FastAPI stub as soon as the backend's auth endpoints exist (backend and frontend Phase 1 must co-develop the auth contract).

**Phase 1 — Foundation (no UI)**: `types/contentBlocks.ts` → `lib/*` (constants, surveyOptions, contentBlocks, mdxParser, blocksToMdx) → `api/tokens.ts` → `api/client.ts`. mdxParser/blocksToMdx get a quick round-trip sanity check against a real `content_blocks` JSON pulled from Supabase.

**Phase 2 — Auth spine**: `AuthContext.tsx` → `App.tsx` (routes/guards) → `Login` → `AppNav` → `SetPassword` → `InviteRedirect`. Gate: log in as migrated admin + invite a test user end-to-end (create invite in admin later; for now hit the API directly).

**Phase 3 — Learner core** (needs migrated data in Azure PG): `JourneyHome` → `Assessment` → `ModulePopup` → `LearningPath` → lesson `blocks/*` + `LessonView` → `LessonPage` (view + progress only).

**Phase 4 — Admin**: `adminStyles.ts` + `adminHelpers.tsx` → `Admin.tsx` shell → `ProjectsView`/`SetupView` → `ProjectDetailView` (invite flow closes the Phase-2 loop) → `UserPanel` + `SurveyResults` → `AddTrackModal`/`AddModuleModal`/`ModulePanel` → lesson `editors/*` + `LessonEditor` (admin edit mode in LessonPage last — it's the least-used, highest-complexity surface).

**Parity verification protocol**: run old app (`app/`, port 3000, live Supabase) and new stack (FastAPI :8000 + Vite :5173) side by side, same user in both, per-page checklist:
- **Login**: wrong-password error text, redirect-if-logged-in, spinner state.
- **SetPassword/Invite**: expired token → 410 UI; consumed token reuse → invalid UI; post-set lands on `/` with nav showing name.
- **JourneyHome**: locked/hidden component states for a project with non-default settings; assessment CTA changes across none/in_progress/complete survey states; progress stepper.
- **Assessment**: resume mid-step after reload (step + answers restored); c5 multi-select; free-text steps; completion → score visible in admin.
- **LearningPath**: graph layout identical for the real dataset (node positions, col_offset ties, track colors, zoom, edges from prerequisites); lesson-count badges.
- **LessonPage**: every block type renders identically (screenshot-diff one content-heavy lesson); quiz must-be-all-correct gate before "Mark as complete"; complete → next-lesson navigation incl. cross-module hop; answers pre-filled on revisit.
- **Admin**: user table badges (level per B1-fixed ordering), role toggle, delete, component toggles persist, track/module assignment reflects on learner's LearningPath, invite + reset link copy, add track/module/lesson, lesson reorder survives reload, MDX import round-trip.
- Cross-cutting: reload on every route (session restore), token expiry mid-session (shorten access TTL in dev to force the refresh path), logout everywhere.

Sequencing dependency on other workstreams: Phase 2 needs backend auth endpoints + at least the admin user row migrated; Phase 3 needs full data migration into Azure PG; the aggregate endpoints (`/api/me/journey`, `/api/learning/path`, `/api/lessons/{id}`, module lesson routes) are new contract this design hands to the backend plan — everything under `/api/admin/*`, `/api/survey/*`, `/api/invite/{id}` keeps the old paths/shapes.

### Critical Files for Implementation
- `C:\Users\danneelm\projects\AI enablement hub\app\src\contexts\AuthContext.jsx` — the contract the new AuthContext must preserve (state shape) while replacing internals
- `C:\Users\danneelm\projects\AI enablement hub\app\src\App.jsx` — route guards / password gate semantics to reproduce
- `C:\Users\danneelm\projects\AI enablement hub\app\src\lib\contentBlocks.js` — source of truth for the ContentBlock discriminated union (7 types incl. `question`)
- `C:\Users\danneelm\projects\AI enablement hub\app\src\pages\LessonPage.jsx` — densest Supabase-query cluster to collapse into the lesson aggregate endpoint
- `C:\Users\danneelm\projects\AI enablement hub\app\src\pages\LearningPath.jsx` — 7-query chain defining the `/api/learning/path` aggregate contract