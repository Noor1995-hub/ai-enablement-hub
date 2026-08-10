# Plan — Frontend robustness & cleanup (review batches 8, 2.7/2.9 frontend, 9.1)

**Source review:** `CODE-REVIEW-2026-07-31.md` (this folder). Item numbers below are that document's.
**Written:** 2026-07-31. **Baseline:** `main`, frontend at 109 TS/TSX files.
**Scope:** `frontend/` only. Nothing under `backend/` is touched by any task here (a separate backend
plan covers the server-side half of 2.7).

## Goal

Close the frontend robustness gaps found in the 2026-07-31 review: give the app an error boundary so a
single bad lesson block can no longer white-page it, retire the stale `rawRequest` escape hatch so all
~25 admin/interview calls are compile-checked against the generated OpenAPI schema again, stop the
editors losing work silently, stop shipping the admin panel to every learner, and clear the dead
`pages/admin/` straddle so there is one admin tree instead of two.

## Architecture

The frontend is a Vite + React 18 SPA with two internally-consistent halves: a learner app
(`src/pages/*`, manual `useEffect` fetches through the generated `openapi-fetch` client) and an admin
panel (`src/pages/admin2/*`, `@tanstack/react-query` over the same client, `adm-*` CSS classes from
`src/styles/admin.css`). This plan does not change that split — it hardens the seams between them: one
typed API surface (no casts), one error boundary strategy (route level + per lesson block), one shared
unsaved-changes hook, and one admin tree loaded lazily as its own bundle chunk.

## Tech Stack

React 18.3.1 · react-router-dom 6.30.4 (installed; `^6.26.1` in `package.json`) · TypeScript 5.6
(strict, `noUncheckedIndexedAccess` off) · Vite 6 · `openapi-fetch` 0.13.5 over generated
`src/api/schema.d.ts` · `@tanstack/react-query` 5 (admin2 only) · framer-motion 12 (two importers).

## Global Constraints

1. **React 18.3.1 + react-router v6 are pinned.** Do not upgrade either as part of any task here. No
   React 19 APIs (`use`, `useActionState`, ref-as-prop), no react-router v7 imports.
2. **`useBlocker` is NOT available in this app as it stands.** `node_modules/react-router/dist/index.js:830`
   shows `useBlocker` calling `useDataRouterContext(...)`, which throws unless the tree is mounted by a
   *data* router (`createBrowserRouter` + `RouterProvider`). `src/App.tsx:97` uses `<BrowserRouter>`, so
   calling `useBlocker` today throws at render. Task 11 therefore ships a `beforeunload`-based guard
   that works under the current router; Task 11b (optional, needs sign-off) migrates to a data router
   to unlock in-app navigation blocking.
3. **The app renders at CSS `zoom: 1.25` on `:root`** (`src/index.css:63-68`). Any *new* code that mixes
   `getBoundingClientRect()` output with layout/`position:fixed` coordinates must divide the rect values
   by `getRectZoomFactor()` from `src/lib/uiZoom.ts` — see the existing correct call site,
   `src/pages/LearningPathNew.tsx:839-845`. No task in this plan should need new rect math; if one does,
   compensate.
4. **The load-bearing `useCallback` identities in `LessonPage` must stay stable.**
   `onQuizComplete` (`src/pages/LessonPage.tsx:110`) and `handleEditorLiveChange` (`:140`) are
   `useCallback(..., [])` on purpose, with comments explaining the failures an inline arrow causes: an
   inline `onQuizComplete` lets the previous lesson's still-mounted quiz refire and undo the per-lesson
   `quizDone` reset; an inline `onLiveChange` makes `LessonEditor`'s live-preview effect fire every
   render, each firing calling `setLesson` with a fresh object — an infinite loop. Never convert either
   to an inline arrow, and never add a dependency that changes on every render.
5. **`src/types/contentBlocks.ts`'s union drives the exhaustive `RENDERERS` / `EDITORS` maps**
   (`src/components/lesson/LessonView.tsx:24-39`, `src/components/lesson/LessonEditor.tsx:20-38`). Both
   are mapped types keyed on `ContentBlock['type']`, so adding a block type must remain a *compile
   error* until a renderer and an editor are registered. Do not loosen either map to
   `Record<string, ComponentType<...>>`, and keep the runtime `if (!Component) return null`
   unknown-type tolerance.
6. **`src/api/schema.d.ts` is generated and committed.** It is produced by `npm run gen:api`
   (`openapi-typescript http://localhost:8000/openapi.json`), which requires a **running backend**.
   Never hand-edit it. No task in this plan needs to regenerate it — every path used below was verified
   present in the committed file. If a typed call fails to compile because a field is missing, stop and
   report rather than editing the schema or casting around it.
7. **Destructive actions use in-app confirmation UI, never `window.confirm`** (in-repo rule; stated in
   `src/styles/admin.css:308` and `src/pages/admin2/kit/ConfirmButton.tsx:21-24`).
8. **`adm-*` CSS classes are only loaded inside the admin shell.** `src/styles/admin.css` is imported by
   `src/pages/admin2/AdminShell.tsx:5` and nowhere else — after Task 10 it lives in the lazily-loaded
   admin chunk. Therefore `admin2/kit` components must not be used from learner-facing code
   (`src/components/*`, `src/pages/LearningPathNew.tsx`, `src/pages/LessonPage.tsx`, …); they would
   render unstyled. This is why Task 7 fixes `ModulePanel` with its own in-file two-step pattern rather
   than with `kit/ConfirmButton`.
9. **There is no frontend test framework.** No vitest, no playwright, zero `*.test.*` files, and standing
   one up is out of scope. The gate for every task is therefore
   `npm run typecheck && npm run lint && npm run build` run inside `frontend/`, **plus** the task's
   manual browser check. Treat the manual check as mandatory, not optional.
10. **Work on a branch.** `main` is the live branch and deploys ship the working tree. Before Task 1:
    `git checkout -b fix/frontend-robustness`. Every task ends in its own commit on that branch.

## How to run the app for the manual checks

Two terminals, from the repo root:

```bash
# terminal 1 — backend on :8000
cd backend && uv run python -m src.startup

# terminal 2 — frontend on :5173 (proxies /api to :8000, see vite.config.ts)
cd frontend && npm run dev
```

Then open `http://localhost:5173`. Sign in as an admin account for the admin checks, and as a plain
`user` account for the learner checks (several tasks need both).

---

## Task 1: Memoize the MDX reparse so typing stops re-running the parser (8.6)

**Files:**
- Modify: `frontend/src/pages/LessonPage.tsx` (imports line 1; `blocks` line 43; `mdxBlocks` line 47)

**Interfaces:**
- Consumes: `parseMdxToBlocks(text: string): ContentBlock[]` (`src/lib/mdxParser.ts`).
- Produces: `blocks: ContentBlock[]` and `mdxBlocks: ContentBlock[]` with **stable identities** between
  renders that do not change `lesson.content_blocks` / `mdxText`. Later tasks (9, 11) rely on `blocks`
  being referentially stable.

- [ ] **Step 1: Memoize `blocks` first — otherwise memoizing `mdxBlocks` does nothing.**
      `blocks` is currently rebuilt every render (`(lesson?.content_blocks ?? []) as ContentBlock[]`), so it
      would invalidate any `useMemo` that depends on it. Replace line 43:

```tsx
  // content_blocks crosses the JSONB boundary as unknown[]; this is the one
  // cast to the hand-written union (design-frontend §2). Memoized so the
  // identity is stable — mdxBlocks below depends on it, and a fresh array
  // every render would defeat that memo.
  const blocks = useMemo(
    () => (lesson?.content_blocks ?? []) as ContentBlock[],
    [lesson?.content_blocks],
  )
  const hasQuiz = blocks.some(b => b.type === 'quiz')
```

- [ ] **Step 2: Memoize the parse.** Replace line 47 (`const mdxBlocks = mdxText.trim() ? parseMdxToBlocks(mdxText) : blocks`):

```tsx
  // The MDX parser is a full multi-pass regex scan over the whole document
  // (lib/mdxParser.ts). Without this memo it re-ran on every render — i.e. on
  // every keystroke in the MDX pane.
  const mdxBlocks = useMemo(
    () => (mdxText.trim() ? parseMdxToBlocks(mdxText) : blocks),
    [mdxText, blocks],
  )
```

- [ ] **Step 3: Add `useMemo` to the React import.** Line 1 becomes:

```tsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
```

- [ ] **Step 4: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 5: Verify (manual browser check)**
      Sign in as an **admin**. Open any lesson: `http://localhost:5173/learning` → open a track → click a
      module → "Start module". In the top bar click **MDX**. Paste this into the right-hand box:

```
# Test heading

A paragraph of text.

> A callout box.
```

      **Expected:** the left preview shows the heading, paragraph and callout; the label above the box reads
      "3 blocks parsed"; typing more text stays smooth with no lag, and the preview keeps up. Then click
      **Clear** — the preview goes back to the saved lesson content. Do **not** click "Save as blocks".

- [ ] **Step 6: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/LessonPage.tsx
git commit -m "$(cat <<'EOF'
perf(frontend): memoize MDX reparse and lesson blocks (review 8.6)

parseMdxToBlocks ran on every render — every keystroke in the MDX pane.
Memoizing mdxBlocks needs `blocks` memoized too, since it was rebuilt each
render and would have invalidated the memo immediately.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none — `blocks` feeds the same `LessonView` with identical contents, and
a *more* stable identity only reduces re-renders. *Admin:* if `lesson.content_blocks` were ever mutated
in place rather than replaced, the memo would show stale content — it is not (every writer uses
`setLesson(l => ({ ...l, content_blocks: … }))`, `LessonPage.tsx:141,145,163`). Watch the MDX preview
updating as you type during the manual check.

---

## Task 2: LessonPage — admin-gate `?edit=true`, and stop reporting server failures as "Lesson not found" (2.9, 8.7)

**Files:**
- Modify: `frontend/src/pages/LessonPage.tsx` (state block lines 20-33; load effect lines 54-81;
  render guards lines 169-186)

**Interfaces:**
- Consumes: `client.GET('/api/lessons/{lesson_id}')` → `{ data, error, response }` (`response.status` is
  what distinguishes 404 from 5xx).
- Produces: no exported surface change.

- [ ] **Step 1: Move the `isAdmin` derivation above the state block and gate the initial edit mode.**
      Today `editMode` initialises from the URL with no role check (`:22`), so `?edit=true` renders the
      editor pane to any signed-in learner. `useAuth()` already resolves before this page mounts —
      `App.tsx:39` returns a full-page spinner while `loading` is true — so a lazy initialiser is safe.
      Replace lines 20-33 with:

```tsx
  // Derived before the state block: the initial editMode depends on it. AppRoutes
  // gates on `loading` before rendering any page, so `user` is already resolved here.
  const isAdmin = user?.role === 'admin'

  const [lesson, setLesson]   = useState<LessonDetail | null>(null)
  const [loading, setLoading] = useState(true)
  // Distinguishes "the server said 404" from "the request failed" — the two need
  // different copy (see the render guards below).
  const [loadFailed, setLoadFailed] = useState(false)
  const [reloadKey, setReloadKey]   = useState(0)
  // Admin-only: the editor pane used to render for anyone who put ?edit=true in
  // the URL. Writes were always 403'd server-side, so this was cosmetic — but it
  // showed learners an editing surface that isn't theirs (review 2.9).
  const [editMode, setEditMode]   = useState(isAdmin && searchParams.get('edit') === 'true')
  const [mdxMode, setMdxMode]     = useState(false)
  const [mdxText, setMdxText]     = useState('')
  const [mdxSaving, setMdxSaving] = useState(false)
  const [mdxError, setMdxError]   = useState<string | null>(null)
  const [quizDone, setQuizDone]           = useState(false)
  const [answers, setAnswers]             = useState<Record<string, string>>({})
  const [completing, setCompleting]       = useState(false)
  const [markError, setMarkError]         = useState<string | null>(null)
  const [moduleLessons, setModuleLessons] = useState<ModuleLessonItem[]>([])
  const [completedIds, setCompletedIds]   = useState<Set<string>>(new Set())
  const [nextLessonId, setNextLessonId]   = useState<string | null>(null)
```

- [ ] **Step 2: Delete the now-duplicated `isAdmin` line.** Line 46 (`const isAdmin = user?.role === 'admin'`,
      just above the `mdxBlocks` memo from Task 1) is now a redeclaration — remove that single line.

- [ ] **Step 3: Record *why* the load produced no lesson.** In the load effect, replace the body of
      `load()` (currently lines 68-78) and add `reloadKey` to the dependency array:

```tsx
    async function load() {
      const { data, response } = await client.GET('/api/lessons/{lesson_id}', {
        params: { path: { lesson_id: lid } },
      })
      if (cancelled) return
      if (!data) {
        setLesson(null)
        // 404 = this lesson really doesn't exist (or isn't yours). Anything else
        // (500, 502, network failure → status 0) is a failure to load, and telling
        // the learner the lesson "doesn't exist" is both wrong and unactionable.
        setLoadFailed(response.status !== 404)
        setLoading(false)
        return
      }
      setLoadFailed(false)
      setLesson(data)
      setAnswers((data.my_answers as Record<string, string> | null) ?? {})
      setNextLessonId(data.next_lesson_id)
      setLoading(false)
    }

    load()
    return () => { cancelled = true }
  }, [lessonId, reloadKey])
```

- [ ] **Step 4: Split the two failure screens.** Replace the `if (!lesson)` block (lines 177-186) with:

```tsx
  if (!lesson) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 16, color: '#101820' }}>
          {loadFailed ? "We couldn't load this lesson." : 'Lesson not found.'}
        </p>
        {loadFailed && (
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: 0 }}>
            Something went wrong on our side. Please try again.
          </p>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          {loadFailed && (
            <button
              onClick={() => { setLoading(true); setReloadKey(k => k + 1) }}
              style={{ background: '#C42828', border: 'none', borderRadius: 999, padding: '9px 20px', cursor: 'pointer', fontSize: 14, color: '#fff', fontWeight: 700, fontFamily: 'var(--dlw-font-body)' }}
            >
              Try again
            </button>
          )}
          <button onClick={() => navigate('/learning')} style={{ background: 'none', border: '1px solid #E2E2E2', borderRadius: 999, padding: '9px 20px', cursor: 'pointer', fontSize: 14, color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)' }}>
            ← Back to learning path
          </button>
        </div>
      </div>
    )
  }
```

- [ ] **Step 5: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 6: Verify (manual browser check — three parts)**
      **(a) Admin still edits.** As an **admin**, open a lesson, click **Edit content**. **Expected:** the
      split view appears (preview left, block editor right). Reload the page with `?edit=true` still in the
      address bar — **expected:** it opens straight into the editor as before.
      **(b) Learner no longer sees the editor.** Sign in as a plain **user**. Open a lesson, then manually
      append `?edit=true` to the URL and press Enter, e.g.
      `http://localhost:5173/learning/lesson/<the id in your address bar>?edit=true`. **Expected:** the
      normal reading view with the module sidebar — **no** editor pane, no "Edit content"/"MDX" buttons.
      **(c) Failure copy.** With the app open on a lesson, **stop the backend** (Ctrl-C in terminal 1),
      then reload the lesson page. **Expected:** "We couldn't load this lesson." + "Something went wrong on
      our side. Please try again." + a red **Try again** button. Restart the backend, click **Try again** —
      **expected:** the lesson loads. Finally, visit
      `http://localhost:5173/learning/lesson/00000000-0000-0000-0000-000000000000` — **expected:** the old
      "Lesson not found." wording with only the back link.

- [ ] **Step 7: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/LessonPage.tsx
git commit -m "$(cat <<'EOF'
fix(frontend): admin-gate ?edit=true and separate load failure from 404 (review 2.9, 8.7)

editMode initialised from the query param with no role check, so any learner
could render the editor pane (writes were always 403'd server-side). Also, any
empty response read as "Lesson not found" — a 500 now says so and offers a retry.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* the `?edit=true` gate is the visible change — verify part (b) actually
shows the reading view, and that a normal lesson open (no query param) is unchanged. *Admin:* if
`user?.role` were somehow not yet resolved on first render, the editor would fail to open from a
`?edit=true` deep link; part (a) of the manual check is exactly that case, so do not skip it.

---

## Task 3: Allowlist link protocols in `renderInline` (2.7, frontend half)

**Files:**
- Modify: `frontend/src/components/lesson/blocks/renderInline.tsx` (whole file, 14 lines)

**Interfaces:**
- Produces: `renderInline(text: string): ReactNode` — unchanged signature, so all 8 block components
  that call it are unaffected.

- [ ] **Step 1: Rewrite the file with a scheme allowlist.** The link branch currently interpolates the
      captured URL straight into `href` (`:10-11`). Content now reaches lessons through the
      AI content-improvement pipeline, which drafts from learner-submitted feedback text, so
      `[click me](javascript:…)` can arrive from outside the admin team:

```tsx
import type { ReactNode } from 'react'

// Only these schemes may become a real <a href>. `javascript:` and `data:` are
// the ones that matter: React 18 warns on a javascript: href but still renders
// it, and lesson content is no longer purely admin-authored — the
// content-improvement agent drafts blocks from learner-submitted feedback, so an
// admin approving a proposal is the last gate before a link goes live for
// everyone. Anything not on this list renders as plain text instead.
const SAFE_PROTOCOLS = ['http:', 'https:', 'mailto:']

/** Returns the href to use, or null when the target isn't a safe link. */
function safeHref(raw: string): string | null {
  const url = raw.trim()
  if (!url) return null
  // Site-relative and in-page targets carry no scheme at all, so they can never
  // be javascript:/data: — pass them through untouched.
  if (url.startsWith('/') || url.startsWith('#')) return url
  let parsed: URL
  try {
    // The base makes scheme-less input ("example.com/x") resolve as relative,
    // which is what it already did as a bare href.
    parsed = new URL(url, window.location.origin)
  } catch {
    return null
  }
  return SAFE_PROTOCOLS.includes(parsed.protocol) ? url : null
}

// Converts **bold**, *italic*, [text](url) markdown inline syntax into React elements.
export function renderInline(text: string): ReactNode {
  if (!text) return null
  const parts = text.split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^)\n]+\))/g)
  return parts.map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={i} style={{ fontWeight: 700 }}>{part.slice(2, -2)}</strong>
    if (/^\*[^*]+\*$/.test(part))     return <em key={i}>{part.slice(1, -1)}</em>
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) {
      const href = safeHref(link[2])
      // Blocked scheme: show the label as plain text rather than dropping it, so
      // the sentence still reads correctly and nothing silently disappears.
      if (!href) return <span key={i}>{link[1]}</span>
      return <a key={i} href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#C42828' }}>{link[1]}</a>
    }
    return part || null
  })
}
```

- [ ] **Step 2: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 3: Verify (manual browser check)**
      As an **admin**, open a lesson and click **Edit content**. Add a Paragraph block (click a `+` between
      blocks → **Paragraph**) and paste exactly this text:

```
Good: [delaware](https://delaware.pro) · Mail: [write us](mailto:hello@delaware.pro) · Relative: [learning](/learning) · Blocked: [do not click](javascript:alert(1))
```

      **Expected in the left-hand preview:** "delaware", "write us" and "learning" are red clickable links;
      **"do not click" is plain black text, not a link** (hovering shows no target, clicking does nothing).
      Click **delaware** — it opens delaware.pro in a new tab. Then click the **×** on that block to remove
      it and leave the lesson **without saving** (do not press Save).

- [ ] **Step 4: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/components/lesson/blocks/renderInline.tsx
git commit -m "$(cat <<'EOF'
fix(frontend): allowlist link protocols in renderInline (review 2.7)

[text](javascript:...) became a live href. Lesson content is no longer purely
admin-authored — the content-improvement agent drafts blocks from learner
feedback — so allow http/https/mailto/relative only and render the rest as text.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* `renderInline` backs 8 block renderers, so a mistake here affects every
lesson's inline formatting. The manual check covers all four link shapes; also glance at one existing
content-rich lesson to confirm bold/italic and normal links still render. *Admin:* none beyond the same
rendering path.

---

## Task 4: Abort the SSE chat stream on unmount and on "start new" (8.7)

**Files:**
- Modify: `frontend/src/lib/useChat.ts` (imports line 7; `fetchWithAuth` lines 29-42; `send` lines 71-138;
  `startNew` lines 155-159)

**Interfaces:**
- Consumes: nothing new.
- Produces: `useChat(kind)` returns the same object shape
  (`{ messages, send, loading, error, conversations, loadConversations, loadConversation, startNew }`) —
  `src/pages/Interview.tsx` and `src/pages/DevChat.tsx` need no changes.

- [ ] **Step 1: Import `useEffect` and `useRef`.** Line 7 becomes:

```tsx
import { useCallback, useEffect, useRef, useState } from 'react'
```

- [ ] **Step 2: Forward an abort signal through the auth-retry wrapper.** `fetchWithAuth` already spreads
      `init` into both attempts, so it only needs its doc comment updated (lines 26-28) to record that the
      caller owns cancellation:

```tsx
/** Bearer-auth fetch with the same 401→refresh→retry-once behaviour as the
 * openapi-fetch client's auth middleware (api/client.ts), reimplemented on raw
 * `fetch` because streaming responses can't go through openapi-fetch.
 * `init.signal` is forwarded to both attempts, so an abort cancels the retry too. */
```

- [ ] **Step 3: Own one controller per hook instance and abort it on unmount.** Insert directly after the
      `const [conversations, setConversations] = useState<ConversationSummary[]>([])` line (:69):

```tsx
  // One in-flight stream at a time. Aborting on unmount stops a long AI reply
  // from continuing to read the body (and to call setMessages) after the user
  // has navigated away; aborting in `send`/`startNew` supersedes a previous
  // stream rather than letting two write into the same message list.
  const abortRef = useRef<AbortController | null>(null)
  useEffect(() => () => abortRef.current?.abort(), [])
```

- [ ] **Step 4: Wire the controller into `send`.** Replace the opening of `send` (lines 72-83) with:

```tsx
    async (content: string) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setLoading(true)
      setError(null)
      setMessages((prev) => [...prev, { role: 'user', content }])
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

      try {
        const response = await fetchWithAuth(`/api/chat/${kind}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, conversation_id: conversationId }),
          signal: controller.signal,
        })
```

- [ ] **Step 5: Treat an abort as "not an error".** Replace the `catch`/`finally` pair (lines 130-135) with:

```tsx
      } catch {
        // An abort is a deliberate cancellation (unmount, or a superseding send),
        // not a failure: the component may already be gone, so don't touch state.
        if (controller.signal.aborted) return
        setError('Connection lost while streaming the reply.')
        setMessages(dropTrailingEmptyAssistant)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
```

- [ ] **Step 6: Abort from `startNew` too.** Replace `startNew` (lines 155-159) with:

```tsx
  const startNew = useCallback(() => {
    // Cancel any stream still writing into the list we're about to clear.
    abortRef.current?.abort()
    abortRef.current = null
    setConversationId(null)
    setMessages([])
    setError(null)
  }, [])
```

- [ ] **Step 7: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 8: Verify (manual browser check)**
      As an **admin**, open `http://localhost:5173/interview`. Start the interview and send a message
      ("I run monthly reporting for a client team and it takes me two days."). While the reply is still
      streaming in, click **← Back** in the top bar to leave the page. **Expected:** navigation is
      immediate, and the browser console shows **no** red "Cannot update a component that has been
      unmounted" / state-update warnings. Return to `/interview` — **expected:** the conversation is there
      with your message and whatever the assistant had produced, and you can send another message that
      streams normally.
      *(Interview AI must be enabled for your project — `/admin/projects` → your project → Interview row.
      If it is off, use `http://localhost:5173/dev-chat` instead and repeat the same steps.)*

- [ ] **Step 9: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/lib/useChat.ts
git commit -m "$(cat <<'EOF'
fix(frontend): abort the SSE chat stream on unmount and startNew (review 8.7)

Navigating away mid-reply left the reader loop consuming the body and calling
setMessages on an unmounted component. One AbortController per hook instance,
aborted on unmount, on a superseding send, and on startNew.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* the interviewer is the learner-facing user of this hook — the risk is
aborting too eagerly and truncating a good reply. `send` aborts only a *previous* stream, and the input
is disabled while `loading`, so a double-send is not the normal path; still, confirm during the manual
check that a full reply arrives intact when you *don't* navigate away. *Admin:* `/dev-chat` uses the same
hook.

---

## Task 5: Memoize the assignment matrix so a cell click stops re-deriving the whole table (8.5)

**Files:**
- Modify: `frontend/src/pages/admin2/Matrix.tsx` (imports line 1; `deriveCellState` lines 37-72;
  component body lines 98-171; the `users.map` row block lines 297-324)

**Interfaces:**
- Consumes: `AdminLearningUserEnriched`, `LearningModule`, `LearningLesson` (already imported).
- Produces: `Matrix`'s props are unchanged (`AssignmentsPage.tsx:140`-area call site needs no edit). New
  internal-only pieces: `type ChildIdIndex = { byTrack: Map<string, string[]>; byModule: Map<string, string[]> }`
  and a memoized `MatrixRow` component.

- [ ] **Step 1: Import the memo helpers.** Line 1 becomes:

```tsx
import { memo, useCallback, useMemo, useState } from 'react'
```

- [ ] **Step 2: Build the parent→children index once instead of filtering per cell.** Insert above
      `deriveCellState` (before line 28's doc comment):

```tsx
/** Parent → direct-child ids, built once per data load. `deriveCellState` used
 * to call `modules.filter(...)` / `lessons.filter(...)` inside every single cell,
 * so the work was O(users × columns × content) on every render — including the
 * re-render each optimistic cell toggle causes. */
interface ChildIdIndex {
  byTrack: Map<string, string[]>
  byModule: Map<string, string[]>
}

function buildChildIdIndex(modules: LearningModule[], lessons: LearningLesson[]): ChildIdIndex {
  const byTrack = new Map<string, string[]>()
  for (const module of modules) {
    const list = byTrack.get(module.track_id)
    if (list) list.push(module.id)
    else byTrack.set(module.track_id, [module.id])
  }
  const byModule = new Map<string, string[]>()
  for (const lesson of lessons) {
    const list = byModule.get(lesson.module_id)
    if (list) list.push(lesson.id)
    else byModule.set(lesson.module_id, [lesson.id])
  }
  return { byTrack, byModule }
}
```

- [ ] **Step 3: Take the index instead of the raw arrays in `deriveCellState`.** Replace its signature and
      the `childIds` block (lines 37-43 and 61-71) so the body becomes:

```tsx
function deriveCellState(
  kind: AssignmentKind,
  itemId: string,
  user: AdminLearningUserEnriched,
  childIds: ChildIdIndex,
): CellState {
  const assigned =
    kind === 'track'
      ? user.assigned_track_ids
      : kind === 'module'
        ? user.assigned_module_ids
        : user.assigned_lesson_ids
  const defaults =
    kind === 'track'
      ? user.default_track_ids
      : kind === 'module'
        ? user.default_module_ids
        : user.default_lesson_ids

  if (assigned.includes(itemId)) {
    return defaults.includes(itemId) ? 'def' : 'yes'
  }

  // Partial is a coverage signal over the item's direct children.
  const children =
    kind === 'track' ? childIds.byTrack.get(itemId) : kind === 'module' ? childIds.byModule.get(itemId) : undefined
  if (!children || children.length === 0) return ''
  const assignedChildren = new Set(kind === 'track' ? user.assigned_module_ids : user.assigned_lesson_ids)
  const covered = children.filter(id => assignedChildren.has(id)).length
  return covered > 0 && covered < children.length ? 'part' : ''
}
```

- [ ] **Step 4: Memoize the index, the columns, and the cell handler in the component body.** Replace the
      `kind` / `columns` derivations (lines 113-134) and `handleCellClick` (lines 141-144) with:

```tsx
  const kind: AssignmentKind =
    level.level === 'tracks' ? 'track' : level.level === 'modules' ? 'module' : 'lesson'

  const childIds = useMemo(() => buildChildIdIndex(modules, lessons), [modules, lessons])

  const trackName = 'trackId' in level ? (tracks.find(t => t.id === level.trackId)?.name ?? '—') : ''
  const moduleName =
    level.level === 'lessons' ? (modules.find(m => m.id === level.moduleId)?.title ?? '—') : ''

  const columns: Column[] = useMemo(() => {
    if (level.level === 'tracks') {
      return tracks.map(track => ({
        id: track.id,
        name: track.name,
        levelName: levelByCode(track.required_level)?.name,
        dotColor: resolveTrackColor(track),
      }))
    }
    if (level.level === 'modules') {
      return modules
        .filter(module => module.track_id === level.trackId)
        .map(module => ({ id: module.id, name: module.title }))
    }
    return lessons
      .filter(lesson => lesson.module_id === level.moduleId)
      .map(lesson => ({ id: lesson.id, name: lesson.title }))
  }, [level, tracks, modules, lessons])
```

      …and, further down, the handler (which `MatrixRow` receives as a prop, so it must be stable):

```tsx
  const handleCellClick = useCallback(
    (userId: string, itemId: string, state: CellState) => {
      const assigned = !(state === 'yes' || state === 'def')
      toggle.mutate({ userId, kind, id: itemId, assigned })
    },
    [toggle, kind],
  )
```

- [ ] **Step 5: Extract the participant row as a memoized component.** Add at the bottom of the file,
      above `function initials(...)`:

```tsx
interface MatrixRowProps {
  user: AdminLearningUserEnriched
  columns: Column[]
  kind: AssignmentKind
  childIds: ChildIdIndex
  onCellClick: (userId: string, itemId: string, state: CellState) => void
}

/** One participant row. `memo` is the point: `useToggleAssignment`'s optimistic
 * patch rebuilds only the toggled user's object (`api.ts` `cascadeToggleUser`
 * inside `users.map`), so every other row keeps its identity and skips
 * re-rendering — with `columns`/`childIds`/`onCellClick` all memo-stable above,
 * a click now re-derives one row instead of the whole grid. */
const MatrixRow = memo(function MatrixRow({ user, columns, kind, childIds, onCellClick }: MatrixRowProps) {
  return (
    <tr>
      <td className="adm-matrix-rowhead">
        <div className="adm-user-cell">
          <span className="adm-user-avatar">{initials(`${user.first_name} ${user.last_name}`)}</span>
          <span className="adm-user-name">
            {user.first_name} {user.last_name}
          </span>
        </div>
      </td>
      {columns.map(col => {
        const state = deriveCellState(kind, col.id, user, childIds)
        return (
          <td key={col.id}>
            <button
              type="button"
              className={`adm-cell${CELL_CLASS[state] ? ` ${CELL_CLASS[state]}` : ''}`}
              title={CELL_TITLE[state]}
              onClick={() => onCellClick(user.id, col.id, state)}
            >
              {(state === 'yes' || state === 'def') && <CheckIcon />}
              {state === 'part' && '◐'}
            </button>
          </td>
        )
      })}
    </tr>
  )
})
```

- [ ] **Step 6: Use it.** Replace the whole `{users.map(user => ( … ))}` block (lines 297-324) with:

```tsx
              {users.map(user => (
                <MatrixRow
                  key={user.id}
                  user={user}
                  columns={columns}
                  kind={kind}
                  childIds={childIds}
                  onCellClick={handleCellClick}
                />
              ))}
```

- [ ] **Step 7: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 8: Verify (manual browser check)**
      As an **admin**, go to `http://localhost:5173/admin/assignments`, pick a project in the **Viewing**
      switcher at the top. In the matrix: **(a)** click an empty cell for one participant — **expected:** a
      tick appears immediately in that cell only, and no other row changes. **(b)** click it again —
      **expected:** the tick disappears. **(c)** click a track cell that has modules and check the
      breadcrumb: click **All tracks → the track name** to drill into modules — **expected:** the half-moon
      "◐" partial markers appear on exactly the rows/columns they did before this change. **(d)** toggle a
      **Project defaults** cell in the top row — **expected:** it tints, and the "Applies to new
      participants — Apply to existing?" hint appears. Reload the page — **expected:** every tick you set
      is still there (the server agrees with what you saw).

- [ ] **Step 9: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/Matrix.tsx
git commit -m "$(cat <<'EOF'
perf(frontend): memoize assignment-matrix derivation and rows (review 8.5)

deriveCellState filtered the full modules/lessons arrays inside every cell, and
every optimistic toggle re-rendered the entire grid. Build a parent→children
index once, memoize columns and the click handler, and render rows through a
memo()'d component so a click re-derives one row.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none — this screen is admin-only. *Admin:* the risk is a stale row after a
mutation. `memo` compares props shallowly, so a row updates only when its `user` object identity
changes; `api.ts`'s optimistic patch and every `invalidateQueries` refetch both produce new user objects,
so this holds — but step 8's reload check is what proves it. Also watch that partial "◐" markers still
appear, since the child-lookup path changed.

---

## Task 6: Stop the prompt editor overwriting an in-progress draft (8.7)

**Files:**
- Modify: `frontend/src/pages/admin2/PromptsPage.tsx` (imports line 1; `PromptEditor` lines 145-204)

**Interfaces:**
- Consumes: `usePrompt(kind)`, `useUpdatePrompt()`, `useResetPrompt()` (unchanged).
- Produces: no exported change. Adds a local `dirtyRef` + `seededRef` pattern that Task 11 will reuse
  (it reads the same derived `dirty`).

- [ ] **Step 1: Import `useRef`.** Line 1 currently imports `useEffect`/`useState` from react — make it:

```tsx
import { useEffect, useRef, useState } from 'react'
```

- [ ] **Step 2: Replace the unconditional reseed effect.** The effect at lines 160-162 runs on every new
      `promptQuery.data` reference, so a background refetch (react-query refetches on window focus, and
      `staleTime` is 30s — `AdminShell.tsx:17`) can replace text the admin is typing. Replace the
      `const [content, setContent] = useState('')` line and that effect with:

```tsx
  const [content, setContent] = useState('')
  // True once the admin has typed. Guards the reseed effect below: a background
  // refetch must never replace an in-progress draft. Reset after a successful
  // save/reset, so the invalidation those trigger DOES reseed from the server.
  const dirtyRef = useRef(false)
  // The server text the current draft was seeded from — used to detect that
  // someone else saved this prompt while we were editing.
  const seededRef = useRef<string | null>(null)

  useEffect(() => {
    const server = promptQuery.data?.content
    if (server === undefined) return
    if (dirtyRef.current) return
    seededRef.current = server
    setContent(server)
  }, [promptQuery.data])

  function handleChange(next: string) {
    dirtyRef.current = true
    setContent(next)
  }

  function clearDirty() {
    dirtyRef.current = false
  }
```

- [ ] **Step 3: Surface the collision instead of hiding it.** After the existing
      `const busy = updatePrompt.isPending || resetPrompt.isPending` line (:189), add:

```tsx
  // The draft is based on text that is no longer what the server has: another
  // admin saved this prompt while this pane was open. Saving would overwrite
  // them, so say so rather than silently winning.
  const supersededUnderEdit =
    dirtyRef.current && seededRef.current !== null && data.content !== seededRef.current
```

- [ ] **Step 4: Use the guarded change handler and clear the flag on success.** In the `<textarea>` (:221)
      swap `onChange={e => setContent(e.target.value)}` for `onChange={e => handleChange(e.target.value)}`,
      and make the two mutation calls clear the flag — in `handleSave` (:193) and `handleReset` (:203):

```tsx
    updatePrompt.mutate({ kind, content }, { onSuccess: clearDirty })
```

```tsx
    resetPrompt.mutate(kind, { onSuccess: clearDirty })
```

- [ ] **Step 5: Render the warning.** Insert directly above the `<div className="adm-form-actions">` block
      (:233):

```tsx
      {supersededUnderEdit && (
        <p className="adm-form-msg adm-form-msg-err">
          Someone else changed this prompt while you were editing. Saving will replace their version.
        </p>
      )}
```

- [ ] **Step 6: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 7: Verify (manual browser check)**
      As an **admin**, open `http://localhost:5173/admin/prompts` and select a prompt in the left list.
      **(a)** Type a word at the end of the text, then click on another browser tab and back again (this
      triggers a background refetch). **Expected:** your typed word is **still there** — before this change
      it could vanish. **(b)** Now open the same page in a **second browser tab**, edit and save the same
      prompt there (append " ZZZ" and confirm the save). Return to the first tab and click away/back again.
      **Expected:** your draft is intact, and a red line appears: "Someone else changed this prompt while
      you were editing. Saving will replace their version." **(c)** Press **Escape**-free navigation: click
      another prompt in the left list and back. **Expected:** the pane shows the saved server text (the
      draft is intentionally dropped when you switch prompts — the component remounts). Finally, save one
      real edit and confirm the "Last edited …" timestamp updates.

- [ ] **Step 8: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/PromptsPage.tsx
git commit -m "$(cat <<'EOF'
fix(frontend): don't reseed the prompt editor over a dirty draft (review 8.7)

The reseed effect fired on every new query result, so a background refetch could
replace text mid-edit. Guard on a dirty ref, clear it after a successful
save/reset, and warn when the server text changed under the draft.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none (admin-only screen), though the prompts edited here drive every AI
surface, so a broken save path would be learner-visible later — step 7's final real save is the check.
*Admin:* the failure mode to watch is the *opposite* of the bug: if `clearDirty` were missed, a saved
prompt would stop refreshing from the server and the pane would look stuck on the old text. Verify the
"Last edited" timestamp moves after a save.

---

## Task 7: Replace the three `window.confirm` calls with in-app confirmation (8.7)

**Files:**
- Modify: `frontend/src/pages/admin2/PromptsPage.tsx` (`handleSave`/`handleReset` and the
  `adm-form-actions` buttons, lines ~191-251 after Task 6)
- Modify: `frontend/src/pages/admin2/InterviewCard.tsx` (imports; reset button lines 74-90)
- Modify: `frontend/src/components/ModulePanel.tsx` (state line 29-ish; `handleDelete` lines 62-69;
  lesson row delete button lines ~178-181)

**Interfaces:**
- Consumes: `ConfirmButton` from `frontend/src/pages/admin2/kit` —
  `{ label: string; confirmLabel: string; onConfirm: () => void; busy?: boolean; tone?: 'danger' | 'neutral' }`.
- Produces: no exported change.

> **Why `ModulePanel` does not use `ConfirmButton`:** `ConfirmButton` is styled entirely with `adm-*`
> classes from `src/styles/admin.css`, which is imported only by `AdminShell` (and after Task 10 lives in
> the admin-only chunk). `ModulePanel` renders on the learner-facing `/learning` route, so a kit button
> there would appear unstyled. It already contains the correct in-file two-step pattern for
> delete-module (`:226-259`); this task reuses it for delete-lesson.

- [ ] **Step 1: PromptsPage — drop both `window.confirm` calls.** Replace `handleSave` and `handleReset`
      with plain mutation calls (the confirmation now lives in the button):

```tsx
  function handleSave() {
    updatePrompt.mutate({ kind, content }, { onSuccess: clearDirty })
  }

  function handleReset() {
    resetPrompt.mutate(kind, { onSuccess: clearDirty })
  }
```

- [ ] **Step 2: PromptsPage — two-step Save and Reset.** Replace the two buttons inside
      `<div className="adm-form-actions">` with:

```tsx
        {canSave && !busy ? (
          <ConfirmButton
            label="Save"
            confirmLabel="Yes, save for everyone"
            tone="danger"
            busy={updatePrompt.isPending}
            onConfirm={handleSave}
          />
        ) : (
          <button type="button" className="adm-btn adm-btn-primary" disabled>
            {updatePrompt.isPending ? 'Saving…' : 'Save'}
          </button>
        )}
        {data.source === 'db' && (
          <ConfirmButton
            label="Reset to default"
            confirmLabel="Yes, restore the shipped default"
            busy={resetPrompt.isPending}
            onConfirm={handleReset}
          />
        )}
```

      Add the import: `ConfirmButton` joins the existing kit import line
      (`import { Card, Chip, ErrorState, Spinner, ... } from './kit'` — add `ConfirmButton` alphabetically).
      **Note the accepted visual delta:** an armable Save renders with the kit's ghost/danger styling
      rather than `adm-btn-primary`; the disabled state keeps the primary look. Confirm it reads correctly
      in step 6.

- [ ] **Step 3: InterviewCard — two-step reset.** Replace the reset `<button>` (lines 75-90) with:

```tsx
        <ConfirmButton
          label="Reset interview"
          confirmLabel="Yes, delete this interview"
          busy={reset.isPending}
          onConfirm={() => reset.mutate(userId)}
        />
```

      and add the import at the top of the file:

```tsx
import { ConfirmButton } from './kit'
```

- [ ] **Step 4: ModulePanel — track which lesson is armed.** Add next to the existing state (after
      `const [confirmingDelete, setConfirmingDelete] = useState(false)`, :29):

```tsx
  // Which lesson row is armed for deletion (in-app two-step, mirroring the
  // module danger zone below). Never window.confirm: this panel renders on the
  // learner-facing /learning route, where the admin kit's CSS isn't loaded.
  const [confirmingLessonId, setConfirmingLessonId] = useState<string | null>(null)
```

- [ ] **Step 5: ModulePanel — drop the native dialog from `handleDelete`.** Replace lines 62-69 with:

```tsx
  async function handleDelete(lessonId: string) {
    const { error } = await client.DELETE('/api/admin/lessons/{lesson_id}', {
      params: { path: { lesson_id: lessonId } },
    })
    setConfirmingLessonId(null)
    if (error) { setAddError(errorMessage(error, 'Failed to delete lesson.')); return }
    setLessons(ls => ls.filter(l => l.id !== lessonId))
  }
```

- [ ] **Step 6: ModulePanel — arm/confirm in the row.** Replace the row's delete button (the
      `<button type="button" onClick={() => handleDelete(lesson.id)}>×</button>` at ~:178-181) with:

```tsx
                {confirmingLessonId === lesson.id ? (
                  <>
                    <button type="button" onClick={() => handleDelete(lesson.id)}
                      style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #FCA5A5', background: '#FEF2F2', color: '#C42828', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                      Delete
                    </button>
                    <button type="button" onClick={() => setConfirmingLessonId(null)}
                      style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #E2E2E2', background: '#fff', color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)', fontSize: 12, cursor: 'pointer' }}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <button type="button" onClick={() => setConfirmingLessonId(lesson.id)} title="Delete lesson"
                    style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #FCA5A5', background: '#FEF2F2', color: '#C42828', fontSize: 13, cursor: 'pointer' }}>
                    ×
                  </button>
                )}
```

- [ ] **Step 7: Verify (build gate + no `window.confirm` left in the tree)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
grep -rn "window.confirm" src --include="*.tsx" --include="*.ts"
```

      The `grep` must print **nothing** except comment lines that mention the rule
      (`styles/admin.css`, `kit/ConfirmButton.tsx`, `ContentImprovementPage.tsx` doc comments).

- [ ] **Step 8: Verify (manual browser check — three screens)**
      **(a)** `http://localhost:5173/admin/prompts` → pick a prompt, change one word. **Expected:** a
      **Save** button that is now clickable; click it once — it becomes **"Yes, save for everyone"** +
      **Cancel** (no browser popup). Click **Cancel** — back to Save, nothing saved. Click Save → **Yes,
      save for everyone** — the prompt saves and "Last edited" updates. Repeat with **Reset to default**
      on a prompt whose chip reads "Edited".
      **(b)** `http://localhost:5173/admin/people` → click a participant who has done the interview →
      scroll to the interview card → click **Reset interview**. **Expected:** it turns into **"Yes, delete
      this interview"** + Cancel, no browser popup. Cancel first, then do it for real on a test account
      only.
      **(c)** `http://localhost:5173/learning` as an **admin** → click **Edit content** (bottom right) →
      open a track → click a module node → the lesson panel opens. Click the **×** next to a lesson.
      **Expected:** the × is replaced by **Delete** + **Cancel** styled like the rest of the panel (no
      browser popup, no unstyled buttons). Click **Cancel** — the × returns and the lesson is still listed.

- [ ] **Step 9: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/PromptsPage.tsx frontend/src/pages/admin2/InterviewCard.tsx frontend/src/components/ModulePanel.tsx
git commit -m "$(cat <<'EOF'
fix(frontend): in-app confirmation for the last three window.confirm calls (review 8.7)

PromptsPage save/reset and InterviewCard reset now use kit/ConfirmButton.
ModulePanel's lesson delete uses its own two-step pattern instead: it renders on
the learner /learning route, where styles/admin.css (the adm-* classes kit
components need) is not loaded.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none directly, but `ModulePanel` is mounted from the learner-facing
`/learning` page in admin edit mode — check the buttons are styled (step 8c) and that a non-admin never
sees the panel (edit mode is gated on `isAdmin`, `LearningPathNew.tsx:915`). *Admin:* the danger is an
accidental single-click delete if the arm/confirm wiring is wrong — cancel first in every part of step 8
before confirming anything for real, and use a throwaway lesson/interview.

---

## Task 8: Modal focus trap + restore, and keyboard-reachable table rows (8.7)

**Files:**
- Modify: `frontend/src/pages/admin2/kit/Modal.tsx` (whole file, 43 lines)
- Modify: `frontend/src/pages/admin2/kit/Table.tsx` (row element, lines 71-98)

**Interfaces:**
- Produces: `Modal` and `Table` props are unchanged — every existing caller (`PeoplePage`,
  `UserDetailPage`, `InviteModal`, `ProjectsPage`, `SetupPage`, …) keeps working untouched.

- [ ] **Step 1: Rewrite `Modal.tsx` with focus management and a Tab trap.**

```tsx
import { useEffect, useRef, type ReactNode } from 'react'

interface ModalProps {
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}

// Everything inside the dialog that can hold focus, in DOM order — used both for
// the initial focus target and for wrapping Tab at the ends.
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** Centered overlay dialog — click-outside and Escape both close. Focus moves
 * into the dialog on open, is trapped inside it while open (Tab wraps at both
 * ends), and returns to whatever opened it on close.
 * Prototype: docs/design-prototypes/admin-redesign/styles.css
 * `.modal-overlay` / `.modal`. */
export function Modal({ title, onClose, children, footer }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  // Mount-only: move focus in, and put it back where it came from on unmount.
  // onClose is deliberately not a dependency — re-running this would steal focus
  // back to the first field every time the caller re-renders with a new closure.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    const first = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE)
    ;(first ?? dialogRef.current)?.focus()
    return () => opener?.focus()
  }, [])

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab') return
      const nodes = dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE)
      if (!nodes || nodes.length === 0) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      // Wrap at both ends so Tab can't walk out into the page behind the overlay.
      if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      } else if (e.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
        e.preventDefault()
        last.focus()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div className="adm-modal-overlay" onClick={onClose}>
      <div
        className="adm-modal"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        // Fallback focus target when the dialog has no focusable child yet.
        tabIndex={-1}
        onClick={e => e.stopPropagation()}
      >
        <div className="adm-modal-head">
          <h2 className="adm-modal-title">{title}</h2>
          <button type="button" className="adm-modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="adm-modal-body">{children}</div>
        {footer && <div className="adm-modal-footer">{footer}</div>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Make clickable table rows keyboard-operable.** In `Table.tsx`, replace the `<tr …>` opening
      tag inside `rows.map` (lines 75-84) with:

```tsx
            <tr
              key={id}
              className={[
                onRowClick && 'adm-table-row-clickable',
                isSelected && 'adm-table-row-selected',
              ]
                .filter(Boolean)
                .join(' ')}
              // Clickable rows were mouse-only. tabIndex + Enter/Space makes them
              // reachable; the row keeps its native `row` role (an added
              // role="button" would break the table semantics screen readers use
              // to announce column headers).
              tabIndex={onRowClick ? 0 : undefined}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={
                onRowClick
                  ? e => {
                      if (e.target !== e.currentTarget) return // let checkboxes/buttons handle their own keys
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onRowClick(row)
                      }
                    }
                  : undefined
              }
            >
```

- [ ] **Step 3: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 4: Verify (manual browser check — keyboard only, no mouse)**
      As an **admin**, go to `http://localhost:5173/admin/people`.
      **(a) Rows:** press **Tab** repeatedly until a participant row is highlighted, then press **Enter**.
      **Expected:** the participant's detail page opens (same as clicking the row). Go back.
      **(b) Modal focus:** click **Invite** to open the dialog. **Expected:** the cursor is already in the
      first field — you can type an email without clicking. Press **Tab** repeatedly through every field
      and button. **Expected:** focus cycles **within the dialog** and never lands on the page behind it;
      **Shift+Tab** from the first element jumps to the last. Press **Escape**. **Expected:** the dialog
      closes and the **Invite** button is focused again (press Enter and it reopens).
      **(c) Mouse unchanged:** click a row with the mouse — it still opens the detail page; click a row
      checkbox — it selects the row **without** navigating.

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/kit/Modal.tsx frontend/src/pages/admin2/kit/Table.tsx
git commit -m "$(cat <<'EOF'
a11y(frontend): modal focus trap/restore and keyboard-reachable table rows (review 8.7)

Modal now focuses its first field on open, wraps Tab at both ends, and returns
focus to the opener on close. Clickable Table rows get tabIndex + Enter/Space
without taking on role="button" (which would break table semantics).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none — both files are admin-only kit components. *Admin:* the sharp edge
is the `e.target !== e.currentTarget` guard in the row handler; without it, pressing Space on a row
checkbox would also navigate away. Step 4(c) is that check. Also confirm the bulk-select checkbox in the
header still works, since it sits inside the same `<tr>` machinery.

---

## Task 9: Add error boundaries — route level and per lesson block (8.1)

**Files:**
- Create: `frontend/src/components/ErrorBoundary.tsx`
- Modify: `frontend/src/App.tsx` (imports lines 1-25; `App` lines 94-103)
- Modify: `frontend/src/components/lesson/LessonView.tsx` (imports line 1; block map lines 57-75)

**Interfaces:**
- Produces:
  ```tsx
  interface ErrorBoundaryProps {
    children: ReactNode
    /** Changing this clears a caught error (e.g. the current pathname). */
    resetKey?: string
    /** Rendered instead of the default full-page message. */
    fallback?: (reset: () => void) => ReactNode
  }
  export default class ErrorBoundary extends Component<ErrorBoundaryProps, { error: Error | null }>
  ```
  Task 10 mounts its `<Suspense>` inside this boundary, so a failed chunk download surfaces as the
  boundary's message rather than a blank screen.

- [ ] **Step 1: Create the boundary.** A class component is required — there is no hook equivalent for
      `getDerivedStateFromError`.

```tsx
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  /** When this value changes, a caught error is cleared and children re-render.
   * The route-level boundary passes the current pathname, so navigating away
   * from a broken screen recovers without a manual reload. */
  resetKey?: string
  /** Custom fallback. `reset` clears the error and retries the children. */
  fallback?: (reset: () => void) => ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/** The app had no error boundary at all: any render-time throw blanked the whole
 * page with no message and no way back. Lesson content is the realistic source —
 * `content_blocks` crosses a JSONB boundary and now arrives from hand edits AND
 * the AI content-improvement pipeline, so a block of a known type with malformed
 * fields (a quiz whose `options` is null) throws inside its renderer. */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // No client error reporting service is wired up yet, so the console is the
    // record. Keep the component stack — it names the block/page that threw.
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  componentDidUpdate(prev: ErrorBoundaryProps): void {
    if (this.state.error !== null && prev.resetKey !== this.props.resetKey) {
      this.setState({ error: null })
    }
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  render(): ReactNode {
    if (this.state.error === null) return this.props.children
    if (this.props.fallback) return this.props.fallback(this.reset)

    return (
      <div style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 12, padding: 24,
        fontFamily: 'var(--dlw-font-body)', background: '#fff', textAlign: 'center',
      }}>
        <p style={{ fontWeight: 700, fontSize: 18, color: '#101820', margin: 0 }}>
          Something went wrong on this page.
        </p>
        <p style={{ fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: 0, maxWidth: '46ch' }}>
          Nothing you did is lost on our side. Try again, or go back to your journey.
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <button
            type="button"
            onClick={this.reset}
            style={{ padding: '10px 20px', borderRadius: 999, border: 'none', background: '#C42828', color: '#fff', fontWeight: 700, fontSize: 14, fontFamily: 'var(--dlw-font-body)', cursor: 'pointer' }}
          >
            Try again
          </button>
          <a
            href="/"
            style={{ padding: '10px 20px', borderRadius: 999, border: '1px solid #E2E2E2', background: '#fff', color: '#8A8A8A', fontWeight: 600, fontSize: 14, fontFamily: 'var(--dlw-font-body)', textDecoration: 'none' }}
          >
            Back to start
          </a>
        </div>
      </div>
    )
  }
}
```

- [ ] **Step 2: Wrap the routes.** In `App.tsx`, add the import
      `import ErrorBoundary from './components/ErrorBoundary'` next to the other component imports, and
      replace the `App` component (lines 94-103) with:

```tsx
/** The boundary lives inside BrowserRouter so it can key on the pathname:
 * navigating away from a screen that threw clears the error automatically. */
function RoutedErrorBoundary() {
  const { pathname } = useLocation()
  return (
    <ErrorBoundary resetKey={pathname}>
      <AppRoutes />
    </ErrorBoundary>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToTop />
        <RoutedErrorBoundary />
      </BrowserRouter>
    </AuthProvider>
  )
}
```

      (`useLocation` is already imported at `App.tsx:2`.)

- [ ] **Step 3: Isolate each lesson block.** In `LessonView.tsx`, one malformed block should not take the
      whole lesson down. Add the import and wrap the mapped component:

```tsx
import type { ComponentType } from 'react'
import ErrorBoundary from '../ErrorBoundary'
```

      and replace the `return (<Component … />)` inside `blocks.map` (lines 64-72) with:

```tsx
        return (
          // Per-block: a single malformed block (JSONB content, now also written
          // by the AI proposal pipeline) degrades to one inline notice instead of
          // taking the lesson — or the app — down with it.
          <ErrorBoundary
            key={block.id}
            resetKey={block.id}
            fallback={() => (
              <p style={{
                fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14,
                color: '#8A8A8A', fontStyle: 'italic',
                border: '1px dashed #E2E2E2', borderRadius: 8, padding: '12px 14px',
              }}>
                This part of the lesson couldn't be displayed.
              </p>
            )}
          >
            <Component
              block={block}
              onComplete={block.type === 'quiz' ? onQuizComplete : undefined}
              answer={block.type === 'question' ? answers?.[block.id] : undefined}
              onAnswerChange={block.type === 'question' ? onAnswerChange : undefined}
            />
          </ErrorBoundary>
        )
```

- [ ] **Step 4: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 5: Verify (manual browser check — needs a deliberately broken block)**
      As an **admin**, open a **throwaway** lesson (create one via `/learning` → Edit content → a module →
      "+ Add lesson" if you'd rather not touch real content). Click **MDX** in the top bar and paste this,
      which produces a quiz with no options:

```
<Quiz data='[{"q":"Broken on purpose","options":null,"correct":0}]' />
```

      **Expected in the left-hand preview:** a dashed box reading "This part of the lesson couldn't be
      displayed." — **the rest of the page (top bar, title, other blocks) still renders**, and the browser
      console shows one `[ErrorBoundary]` entry. Before this task the whole page went white.
      Then click **Clear** and leave without saving.
      **Second check (route level):** while still signed in, open `http://localhost:5173/learning` and
      confirm the page renders normally — the boundary must be invisible when nothing throws.

- [ ] **Step 6: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/components/ErrorBoundary.tsx frontend/src/App.tsx frontend/src/components/lesson/LessonView.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): add error boundaries at route level and per lesson block (review 8.1)

The app had no boundary anywhere, so any render throw produced a white page with
no message. A pathname-keyed boundary wraps all routes, and each lesson block is
isolated so one malformed block degrades to an inline notice.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* the per-block wrapper adds a component between `LessonView` and each block
renderer. Quiz completion is the thing to watch — `onQuizComplete` must still reach `QuizBlock`
unchanged (Global Constraint 4); after the manual check, open a lesson with a real quiz, answer every
question, and confirm **"Mark as complete"** appears. *Admin:* the editor's live preview uses the same
`LessonView`, so confirm editing a block still updates the preview.

---

## Task 10: Load the admin panel as its own chunk with `React.lazy` (8.4)

**Files:**
- Modify: `frontend/src/App.tsx` (imports lines 1-25; the `/admin` route block lines 57-72; `/dev-chat`
  lines 82-86)
- Modify: `frontend/src/pages/admin2/AdminShell.tsx` (imports lines 1-9; `<main>` block lines 64-68)

**Interfaces:**
- Consumes: `ErrorBoundary` from Task 9 (already wrapping all routes, so a chunk that fails to download
  surfaces as its message).
- Produces: no API change. Build output gains a separate admin chunk containing `admin2/*`,
  `@tanstack/react-query` and `styles/admin.css`.

- [ ] **Step 1: Convert the admin (and dev-chat) imports to lazy ones.** In `App.tsx`, replace the eleven
      static admin imports (lines 5-15) and the `DevChat` import (line 18) with:

```tsx
import { lazy, Suspense, useLayoutEffect } from 'react'
```

      …and, after the remaining static imports, add:

```tsx
// The admin panel is admin-only and pulls in @tanstack/react-query plus
// styles/admin.css (857 lines). Loading it lazily keeps all of that out of the
// bundle every LEARNER downloads to read a lesson. AdminShell renders its own
// <Suspense> around <Outlet/>, so switching admin sections swaps only the
// content area; this outer boundary covers the shell chunk itself.
const AdminShell = lazy(() => import('./pages/admin2/AdminShell'))
const AssignmentsPage = lazy(() => import('./pages/admin2/AssignmentsPage'))
const ContentImprovementPage = lazy(() => import('./pages/admin2/ContentImprovementPage'))
const DashboardPage = lazy(() => import('./pages/admin2/DashboardPage'))
const FeedbackPage = lazy(() => import('./pages/admin2/FeedbackPage'))
const PeoplePage = lazy(() => import('./pages/admin2/PeoplePage'))
const ProjectsPage = lazy(() => import('./pages/admin2/ProjectsPage'))
const PromptsPage = lazy(() => import('./pages/admin2/PromptsPage'))
const SetupPage = lazy(() => import('./pages/admin2/SetupPage'))
const TemplatesPage = lazy(() => import('./pages/admin2/TemplatesPage'))
const UserDetailPage = lazy(() => import('./pages/admin2/UserDetailPage'))
// Admin-only ChatPanel harness (see the route comment below).
const DevChat = lazy(() => import('./pages/DevChat'))
```

- [ ] **Step 2: Suspend the shell.** Replace the `/admin` layout route's `element` (lines 57-61) with:

```tsx
      <Route path="/admin" element={
        !session ? <Navigate to="/login" replace />
          : role !== 'admin' ? <Navigate to="/" replace />
          : <Suspense fallback={<Spinner fullPage />}><AdminShell /></Suspense>
      }>
```

      and the `/dev-chat` element (lines 82-86) with:

```tsx
      <Route path="/dev-chat" element={
        !session ? <Navigate to="/login" replace />
          : role !== 'admin' ? <Navigate to="/" replace />
          : <Suspense fallback={<Spinner fullPage />}><DevChat /></Suspense>
      } />
```

      The nested child routes need no `Suspense` of their own — they render into `AdminShell`'s `<Outlet/>`,
      which step 3 wraps.

- [ ] **Step 3: Suspend only the content area inside the shell.** In `AdminShell.tsx`, add `Suspense` to
      the react import (line 2) and the kit `Spinner`:

```tsx
import { Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
```

```tsx
import { Spinner } from './kit'
```

      then replace the `<main>` block (lines 64-68) with:

```tsx
        <main className="adm-main">
          <div className="adm-container">
            {/* Each section is its own lazy chunk; suspending here keeps the
                topbar and sidebar on screen while one loads. */}
            <Suspense fallback={<div className="adm-loading"><Spinner /></div>}>
              <Outlet />
            </Suspense>
          </div>
        </main>
```

- [ ] **Step 4: Verify (build gate + confirm the split actually happened)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
ls -la dist/assets/
```

      **Expected:** `dist/assets/` now contains **several** `.js` files (one entry chunk plus per-page
      chunks) instead of one large bundle, and a separate `.css` asset for the admin styles. Note the size
      of the largest `index-*.js` before and after this task — it should drop noticeably.

- [ ] **Step 5: Verify (manual browser check — both roles)**
      **(a) Admin:** open `http://localhost:5173/admin`. **Expected:** a brief spinner, then the dashboard;
      the topbar and left sidebar appear and **stay put** while you click through **People → Assignments →
      Feedback → Content AI → Projects → Email templates → System prompts → Setup** — each section shows a
      small spinner in the content area only, then renders. Pick a project in **Viewing** and confirm the
      `?project=` scope still follows you across sections. Open a participant (People → a row) and go back.
      **(b) Learner:** open a private window, sign in as a plain **user**, and open a lesson. In DevTools →
      **Network** → JS, **expected:** no admin chunk is downloaded (nothing containing the admin pages),
      and the page works normally. Navigate to `http://localhost:5173/admin` as this user — **expected:**
      you are redirected to the journey home, and still no admin chunk is fetched.

- [ ] **Step 6: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/App.tsx frontend/src/pages/admin2/AdminShell.tsx
git commit -m "$(cat <<'EOF'
perf(frontend): code-split the admin panel out of the learner bundle (review 8.4)

App.tsx eagerly imported all ten admin2 pages, so every learner downloaded the
admin panel, @tanstack/react-query and styles/admin.css to read a lesson. Lazy
imports + one Suspense for the shell and one inside it for the content area.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* this is the task most likely to help learners and least likely to affect
them — but a broken `Suspense` placement would show a spinner forever. Step 5(b) is the check. *Admin:*
the visible change is a short spinner on first entry to each admin section; a slow network could make
that noticeable. The failure mode to watch is a chunk-load error after a redeploy (the old chunk file is
gone) — Task 9's boundary now catches it and offers "Try again", which is why this task comes after it.

---

## Task 11: Shared unsaved-changes guard for the three editors (8.3)

**Files:**
- Create: `frontend/src/lib/useUnsavedGuard.ts`
- Modify: `frontend/src/components/lesson/LessonEditor.tsx` (imports line 1; after the state block ~line 188)
- Modify: `frontend/src/pages/admin2/PromptsPage.tsx` (inside `PromptEditor`, after `dirty` is derived)
- Modify: `frontend/src/pages/admin2/ContentImprovementPage.tsx` (inside `ProposalRow`, after the
  `workingBlocks` state/effects, lines ~250-273)

**Interfaces:**
- Produces: `export function useUnsavedGuard(dirty: boolean): void` — attaches a `beforeunload` handler
  while `dirty` is true and removes it otherwise.

> **Scope note (see Global Constraint 2):** this hook covers tab close, reload, and navigation away from
> the app — the cases `beforeunload` fires for. It does **not** intercept in-app route changes (clicking
> the admin sidebar, the lesson page's back link), because `useBlocker` throws under `<BrowserRouter>`.
> Task 11b covers that and needs sign-off.

- [ ] **Step 1: Create the hook.**

```ts
import { useEffect } from 'react'

/**
 * Warns before the browser discards unsaved work: while `dirty` is true, closing
 * the tab, reloading, or navigating to another site shows the browser's own
 * "Leave site?" prompt.
 *
 * Deliberately NOT react-router's `useBlocker`: that hook requires a data router
 * (`createBrowserRouter`), and this app mounts `<BrowserRouter>` (App.tsx), where
 * calling it throws. In-app route changes therefore remain unguarded until the
 * router migration lands — see the plan's Task 11b.
 */
export function useUnsavedGuard(dirty: boolean): void {
  useEffect(() => {
    if (!dirty) return
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      // Modern browsers only need preventDefault; returnValue keeps older ones
      // (and some embedded webviews) showing the prompt. The message itself is
      // not customisable — every browser shows its own wording.
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [dirty])
}
```

- [ ] **Step 2: Wire the lesson editor.** In `LessonEditor.tsx`, add the import
      `import { useUnsavedGuard } from '../../lib/useUnsavedGuard'` and, immediately after the
      `const pickerTypes = embedded ? EMBEDDED_TYPE_ORDER : TYPE_ORDER` line, add:

```tsx
  // `dirty` already tracks every block/title edit (it drives the toolbar label).
  // Embedded instances have no Save button of their own — their host owns saving
  // — but the work is just as losable, so guard both.
  useUnsavedGuard(dirty)
```

- [ ] **Step 3: Wire the prompt editor.** In `PromptsPage.tsx`'s `PromptEditor`, after the existing
      `const dirty = content !== data.content` line, add:

```tsx
  useUnsavedGuard(dirty)
```

      with `import { useUnsavedGuard } from '../../lib/useUnsavedGuard'` at the top. **Note:** `dirty` is
      derived *after* the component's early returns for loading/error, and hooks may not run
      conditionally — so instead place the call **above** those early returns using the ref-free
      equivalent:

```tsx
  // Placed above the loading/error early-returns: hooks can't run conditionally.
  // promptQuery.data is undefined while loading, so this reads false then.
  useUnsavedGuard(promptQuery.data !== undefined && content !== promptQuery.data.content)
```

- [ ] **Step 4: Wire the proposal review pane.** In `ContentImprovementPage.tsx`'s `ProposalRow`, after the
      two `useEffect`s that manage `workingBlocks`, add:

```tsx
  // Dirty = the admin has opened the editor and the draft in `workingBlocks` is
  // no longer what the server sent. Accept submits `workingBlocks`, so losing it
  // loses real editing work.
  useUnsavedGuard(
    editing && workingBlocks !== null && workingBlocks !== detail.data?.proposed_blocks,
  )
```

      with `import { useUnsavedGuard } from '../../lib/useUnsavedGuard'` at the top.

- [ ] **Step 5: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 6: Verify (manual browser check — three editors)**
      **(a) Lesson editor:** as an **admin**, open a lesson → **Edit content** → change the lesson title.
      The toolbar reads "Unsaved changes". Now press **F5** (reload). **Expected:** the browser asks
      whether you want to leave / reload — choose **Cancel/Stay**, your text is still there. Click
      **Save**, wait for "Saved", press **F5** again. **Expected:** no prompt this time.
      **(b) Prompt editor:** `/admin/prompts` → select a prompt → type a word → press **F5**.
      **Expected:** the browser asks before reloading. Save, then reload — **expected:** no prompt.
      **(c) Proposal review:** `/admin/content-improvement` → a **pending** proposal → **Review changes** →
      **Edit the draft** → change some text → press **F5**. **Expected:** the browser asks before
      reloading. Click **Back to comparison** then **Hide changes**, reload — **expected:** no prompt.
      **Known limitation to confirm, not a bug:** with unsaved changes, clicking a **sidebar link inside
      the app** still navigates away without a warning. That is Task 11b.

- [ ] **Step 7: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/lib/useUnsavedGuard.ts frontend/src/components/lesson/LessonEditor.tsx frontend/src/pages/admin2/PromptsPage.tsx frontend/src/pages/admin2/ContentImprovementPage.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): warn before discarding unsaved editor work (review 8.3)

Adds useUnsavedGuard (beforeunload while dirty) and wires it into the lesson
editor, the prompt editor and the proposal review pane. In-app route changes are
still unguarded: useBlocker needs a data router and this app uses BrowserRouter.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none — all three surfaces are admin-only. *Admin:* the failure mode is a
*sticky* prompt: if `dirty` never returns to false, the browser nags on every reload forever. Step 6's
"save then reload, expect no prompt" half of each check is exactly that test. Do not skip it.

---

## Task 11b (OPTIONAL — needs Matthias's go-ahead): migrate to a data router to block in-app navigation

Do **not** start this without sign-off; it rewrites how every route is declared.

**Files:**
- Modify: `frontend/src/App.tsx` (whole file)
- Modify: `frontend/src/lib/useUnsavedGuard.ts` (add a router-aware variant)

**Interfaces:**
- Produces: `useUnsavedGuard(dirty)` gains in-app blocking via `useBlocker`, plus an in-app confirmation
  UI (per Global Constraint 7, **not** `window.confirm`).

- [ ] **Step 1: Replace `<BrowserRouter>` + `<Routes>` with `createBrowserRouter(...)` + `<RouterProvider>`,**
      converting each `<Route>` to a route object and re-implementing `ScrollToTop` as a layout route
      component (a data router still supports `useLocation`, so the existing `useLayoutEffect` body moves
      unchanged into a root layout element that renders `<Outlet/>`).
- [ ] **Step 2: Add the blocking half of the hook,** `useBlocker(({ currentLocation, nextLocation }) => dirty && currentLocation.pathname !== nextLocation.pathname)`,
      and render the returned `blocker.state === 'blocked'` case as a kit `Modal` with "Discard changes?" /
      "Keep editing" wired to `blocker.proceed()` / `blocker.reset()`.
- [ ] **Step 3: Verify (build gate)** `cd frontend && npm run typecheck && npm run lint && npm run build`
- [ ] **Step 4: Verify (manual browser check)** Walk **every** route in the app — `/login`,
      `/set-password`, `/`, `/assessment`, `/learning`, a lesson, `/interview`, `/invite/<id>`,
      `/auth/callback`, `/admin` and all nine admin sections, plus a bad URL like `/nope` (must redirect) —
      confirming each still renders and each redirect still fires. Then repeat Task 11 step 6 and confirm
      that clicking a sidebar link mid-edit now shows the in-app "Discard changes?" dialog.
- [ ] **Step 5: Commit** with a message stating the router migration and that it unlocks `useBlocker`.

**Regression risk:** *Learner and admin:* highest in the whole plan — every route, redirect and auth gate
in the app is re-declared, including the password-reset and invite flows. This is why it is optional and
last-in-family.

---

## Task 12: Alias the two hand-kept response shapes onto the generated schema (8.7)

**Files:**
- Modify: `frontend/src/api/upload.ts` (lines 9-16)
- Modify: `frontend/src/api/bulkInvite.ts` (lines 10-35)

**Interfaces:**
- Produces: `UploadedMedia`, `BulkInviteReport`, `BulkInviteRow`, `BulkInviteSummary`,
  `BulkInviteStatus` — same names, now aliases of `components['schemas'][…]`.
  Verified present in `src/api/schema.d.ts`: `MediaUploadOut` (:2761), `BulkInviteReport` (:2026),
  `BulkInviteRow` (:2039), `BulkInviteSummary` (:2057).
  **One deliberate shape change:** generated `BulkInviteRow.detail` is `string | null | undefined`
  (optional) where the hand-written one was required. The single consumer is a truthiness check
  (`BulkInviteModal.tsx:186`, `{r.detail ? … : null}`), so nothing breaks.

- [ ] **Step 1: `upload.ts` — replace the hand-typed interface (lines 9-16) with an alias.** The XHR
      transport stays: only `XMLHttpRequest` reports upload progress, which matters for ~300 MB videos.

```ts
import { errorMessage, refreshAccessToken } from './client'
import type { components } from './schema'
import { getAccessToken } from './tokens'

// Aliased onto the generated schema rather than hand-typed: gen:api can't cover
// the multipart REQUEST, but the RESPONSE body is in schema.d.ts, so a backend
// rename now breaks the build instead of failing at runtime.
export type UploadedMedia = components['schemas']['MediaUploadOut']
```

- [ ] **Step 2: `bulkInvite.ts` — replace the four hand-typed shapes (lines 10-35) with aliases.**

```ts
import { errorMessage, refreshAccessToken } from './client'
import type { components } from './schema'
import { getAccessToken } from './tokens'

// Aliased onto the generated schema (same reasoning as api/upload.ts: the
// multipart request can't be typed by gen:api, the response can).
export type BulkInviteReport = components['schemas']['BulkInviteReport']
export type BulkInviteRow = components['schemas']['BulkInviteRow']
export type BulkInviteSummary = components['schemas']['BulkInviteSummary']
export type BulkInviteStatus = BulkInviteRow['status']
```

      Update the file's header comment: drop "so the response types are hand-kept in sync with the backend
      BulkInviteReport" and say they are now aliased onto `schema.d.ts`.

- [ ] **Step 3: Verify (build gate)**

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

      If `typecheck` flags an unused import or an optional-field access, fix it at the call site — do not
      re-add a hand-written type and do not edit `schema.d.ts`.

- [ ] **Step 4: Verify (manual browser check — both uploaders)**
      **(a) Media upload:** as an **admin**, open a lesson → **Edit content** → add an **Image** block →
      upload a small PNG. **Expected:** a progress indication, then the image renders in the left preview.
      Remove the block and leave without saving.
      **(b) Bulk CSV invite:** `/admin/people` → pick a project in **Viewing** → **Bulk invite (CSV)**.
      Upload a small CSV with a header row and two rows, e.g.

```
first_name,last_name,email
Test,Person,test.person@example.com
Test,Duplicate,<paste an email that already exists>
```

      **Expected:** the preview table lists both rows with their status chips, and the duplicate row shows
      its explanatory **detail** text next to it (that text is the field whose type changed). Then
      **cancel** — do not commit the invites.

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/api/upload.ts frontend/src/api/bulkInvite.ts
git commit -m "$(cat <<'EOF'
refactor(frontend): alias upload/bulk-invite response types onto the schema (review 8.7)

Both clients must stay on raw XHR/fetch (multipart + upload progress), but their
RESPONSE shapes exist in schema.d.ts — aliasing them means a backend rename is a
build error instead of a runtime surprise.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none. *Admin:* the two upload paths are the risk; both are exercised in
step 4. The `detail` optionality change is the only real behaviour surface — check the duplicate row's
explanation still appears.

---

## Tasks 13-18: retire the `rawRequest` escape hatch (8.2)

**Shared context for all six tasks.** `pages/admin2/api.ts:44-65` and `lib/interviewApi.ts:8-22` each
build `const raw = client as unknown as RawClient` — the only `as unknown as` casts in the codebase —
because these endpoints were once missing from the generated schema. They are **all present now**;
every path, verb and parameter name below was read out of the committed `src/api/schema.d.ts` while
writing this plan. Convert one endpoint family per task so a mistake is isolated and revertible, and
delete each hatch only when its last consumer is gone (Task 17 for `api.ts`, Task 18 for
`interviewApi.ts`).

Two mechanical rules for every conversion:
- Endpoints that answer **204 No Content** produce `data === undefined` — keep those functions checking
  `if (error) throw …`, never `if (!data)`.
- Endpoints declared `requestBody?: never` take **no** `body` key. Endpoints with a path parameter take
  `params: { path: { … } }`; query parameters go in `params: { query: { … } }` with `undefined` (not
  `null`) for "omit".

---

### Task 13: Type the dashboard and reminder calls (8.2a)

**Files:**
- Modify: `frontend/src/pages/admin2/api.ts` (`fetchDashboard` lines 152-158; `sendReminder` lines 500-504)

**Interfaces:**
- Verified in schema: `GET /api/admin/dashboard` → query `{ project_id?: string | null }`, 200
  `DashboardResponse` (`schema.d.ts:1573`, op at `:6137`). `POST /api/admin/users/{user_id}/reminder` →
  path `{ user_id }`, no request body, 200 `ReminderResponse` (`schema.d.ts:584`, op at `:4447`).
- Produces: `useDashboard(projectId)` / `useSendReminder()` signatures unchanged.

- [ ] **Step 1: `fetchDashboard`.**

```ts
async function fetchDashboard(projectId: string | null): Promise<DashboardResponse> {
  const { data, error } = await client.GET('/api/admin/dashboard', {
    params: { query: { project_id: projectId ?? undefined } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load the dashboard.'))
  return data
}
```

- [ ] **Step 2: `sendReminder`.**

```ts
async function sendReminder(userId: string): Promise<ReminderResponse> {
  const { data, error } = await client.POST('/api/admin/users/{user_id}/reminder', {
    params: { path: { user_id: userId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to send the reminder.'))
  return data
}
```

- [ ] **Step 3: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 4: Verify (manual browser check)**
      As an **admin**: **(a)** open `http://localhost:5173/admin`. **Expected:** the four tiles (Learners,
      Active this week, Need attention, New feedback) show numbers, and the funnel/attention sections
      render. Switch **Viewing** to a specific project and back to **All projects** — **expected:** the
      numbers change and no error state appears. **(b)** `/admin/people` → tick the checkbox on one **test**
      participant → in the bottom bar click **Send reminder**. **Expected:** a green line reading "Sent 1
      reminder."

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/api.ts
git commit -m "$(cat <<'EOF'
refactor(frontend): type the dashboard and reminder calls (review 8.2a)

Both paths are in the generated schema; drop them off the rawRequest hatch.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none. *Admin:* a wrong query-param name would silently return unscoped
dashboard numbers — the project-switch half of step 4(a) is what catches that. The reminder sends a real
email, so use a test participant.

---

### Task 14: Type the feedback family (8.2b)

**Files:**
- Modify: `frontend/src/pages/admin2/api.ts` (`fetchFeedback` lines 180-196; `patchFeedback` lines 516-520;
  `suggestTriage` lines 563-569)

**Interfaces:**
- Verified in schema: `GET /api/admin/feedback` → query
  `{ status?: 'new'|'accepted'|'dismissed'|null; track_id?: string|null; project_id?: string|null; limit?: number; offset?: number }`,
  200 `AdminFeedbackListResponse` (op at `:5755`). `PATCH /api/admin/feedback/{feedback_id}` → path
  `{ feedback_id }`, body `FeedbackStatusUpdateRequest`, **204** (op at `:5822`).
  `POST /api/admin/feedback/suggest-triage` → query `{ project_id?: string|null; limit?: number }`, no
  body, 200 `SuggestTriageResponse` (op at `:5790`).
- Produces: `useFeedback`, `usePatchFeedback`, `useSuggestTriage` signatures unchanged — the optimistic
  cache logic in `usePatchFeedback` (lines 530-556) is untouched.

- [ ] **Step 1: `fetchFeedback`.** Note `track_id` (schema) vs the params object's `track`.

```ts
async function fetchFeedback(params: FeedbackParams): Promise<AdminFeedbackListResponse> {
  const limit = params.limit ?? FEEDBACK_PAGE_SIZE
  const offset = ((params.page ?? 1) - 1) * limit
  const { data, error } = await client.GET('/api/admin/feedback', {
    params: {
      query: {
        status: params.status,
        track_id: params.track,
        project_id: params.project ?? undefined,
        limit,
        offset,
      },
    },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load feedback.'))
  return data
}
```

- [ ] **Step 2: `patchFeedback`** — 204, so check `error` only.

```ts
async function patchFeedback({ id, status }: PatchFeedbackInput): Promise<void> {
  const { error } = await client.PATCH('/api/admin/feedback/{feedback_id}', {
    params: { path: { feedback_id: id } },
    body: { status },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to update the feedback status.'))
}
```

      The local `const body: FeedbackStatusUpdateRequest = { status }` line is no longer needed — the
      generated type is enforced inline. Drop the now-unused `FeedbackStatusUpdateRequest` import if
      `typecheck` flags it.

- [ ] **Step 3: `suggestTriage`.**

```ts
async function suggestTriage({ project, limit }: SuggestTriageInput): Promise<SuggestTriageResponse> {
  const { data, error } = await client.POST('/api/admin/feedback/suggest-triage', {
    params: { query: { project_id: project ?? undefined, limit } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to generate triage suggestions.'))
  return data
}
```

- [ ] **Step 4: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 5: Verify (manual browser check)**
      As an **admin**, open `http://localhost:5173/admin/feedback`.
      **(a)** **Expected:** the list of learner feedback renders, and the **Feedback** count badge in the
      left sidebar matches the number of **New** items. Click the **New / Accepted / Dismissed** pills —
      **expected:** the list filters. Switch **Viewing** to one project — **expected:** the list narrows.
      **(b)** On one item click **Accept** (or **Dismiss**). **Expected:** the chip flips immediately, the
      sidebar badge decreases, and after a moment the list settles on the server's answer. Reload —
      **expected:** the new status stuck.
      **(c)** Click **Suggest triage** (the AI button). **Expected:** it runs and AI hints appear on `new`
      items. *(This spends model tokens — one run only.)*

- [ ] **Step 6: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/api.ts
git commit -m "$(cat <<'EOF'
refactor(frontend): type the feedback list/patch/suggest-triage calls (review 8.2b)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none directly — but this is the queue that decides which learner feedback
reaches the AI content pipeline, so a broken filter would hide items. *Admin:* the sidebar badge and the
page's "New" pill deliberately share one cache entry; if the query key or param names drift, the badge
stops matching the list. Step 5(a)'s badge-matches-list check covers it.

---

### Task 15: Type the project defaults and bulk-assignment calls (8.2c)

**Files:**
- Modify: `frontend/src/pages/admin2/api.ts` (`fetchDefaults` lines 209-212; `bulkAssignUsers` lines 420-423;
  `setDefaults` lines 444-448; `applyDefaults` lines 477-484)

**Interfaces:**
- Verified in schema: `GET /api/admin/projects/{project_id}/defaults` → 200 `DefaultsResponse` (op `:5660`);
  `PUT` same path → body `DefaultsUpdateRequest`, **204** (op `:5691`);
  `POST /api/admin/projects/{project_id}/defaults/apply` → no body, 200 `ApplyDefaultsResponse` (op `:5724`);
  `POST /api/admin/assignments/bulk` → body `BulkAssignmentRequest`, **204** (op `:4774`).
- Produces: `useDefaults`, `useSetDefaults`, `useApplyDefaults`, `useBulkAssignUsers` unchanged,
  including `useSetDefaults`'s optimistic patch (lines 457-475).

- [ ] **Step 1: `fetchDefaults`.**

```ts
async function fetchDefaults(projectId: string): Promise<DefaultsResponse> {
  const { data, error } = await client.GET('/api/admin/projects/{project_id}/defaults', {
    params: { path: { project_id: projectId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load default tracks.'))
  return data
}
```

- [ ] **Step 2: `setDefaults`** — 204.

```ts
async function setDefaults({ projectId, trackIds }: SetDefaultsInput): Promise<void> {
  const { error } = await client.PUT('/api/admin/projects/{project_id}/defaults', {
    params: { path: { project_id: projectId } },
    body: { track_ids: trackIds },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to save default tracks.'))
}
```

- [ ] **Step 3: `applyDefaults`** — no request body.

```ts
async function applyDefaults(projectId: string): Promise<ApplyDefaultsResponse> {
  const { data, error } = await client.POST('/api/admin/projects/{project_id}/defaults/apply', {
    params: { path: { project_id: projectId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to apply default tracks.'))
  return data
}
```

- [ ] **Step 4: `bulkAssignUsers`** — 204; `BulkAssignmentRequest` stays as the input type.

```ts
async function bulkAssignUsers(body: BulkAssignmentRequest): Promise<void> {
  const { error } = await client.POST('/api/admin/assignments/bulk', { body })
  if (error) throw new Error(errorMessage(error, 'Failed to update assignments.'))
}
```

- [ ] **Step 5: Drop now-unused imports** if `typecheck` flags `DefaultsUpdateRequest`.

- [ ] **Step 6: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 7: Verify (manual browser check)**
      As an **admin**, `http://localhost:5173/admin/assignments` with a project selected in **Viewing**.
      **(a)** **Expected:** the **Project defaults** row shows the current default tracks ticked. Click one
      to toggle it — **expected:** it tints immediately and the "Applies to new participants — Apply to
      existing?" hint appears. Reload — **expected:** your change stuck.
      **(b)** Click **Apply now** in that hint. **Expected:** it completes without an error, and the
      participant rows below gain ticks for the default track(s).
      **(c)** `/admin/people` → tick **two** test participants → **Assign content** → **Tracks** → pick one
      track → **Assign to 2 participants**. **Expected:** the dialog closes, the selection clears, and
      opening either participant's detail page shows that track assigned.

- [ ] **Step 8: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/api.ts
git commit -m "$(cat <<'EOF'
refactor(frontend): type the defaults and bulk-assignment calls (review 8.2c)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* **highest of the 8.2 family** — these endpoints decide what content
appears on a learner's `/learning` page. After step 7, sign in as one of the test participants and
confirm their learning path shows the tracks you just assigned and nothing has disappeared. *Admin:*
`apply` is additive-only server-side, but still run step 7 on a test project rather than a live client's.

---

### Task 16: Type the content-improvement family (8.2d)

**Files:**
- Modify: `frontend/src/pages/admin2/api.ts` (`fetchProposals` lines 867-875; `fetchProposal` lines 884-888;
  `fetchImprovementQueue` lines 905-909; `runImprovement` lines 921-927; `reviewProposal` lines 953-961;
  `generateLearnCard` lines 978-982)

**Interfaces:**
- Verified in schema: `GET /api/admin/content-improvement` → query
  `{ status?: 'pending'|'approved'|'rejected'|'superseded'|'failed'|null; limit?: number; offset?: number }`,
  200 `ProposalListResponse` (op `:5908`); `GET /api/admin/content-improvement/{proposal_id}` → 200
  `ProposalDetailOut` (op `:5941`); `GET …/queue` → no params, 200 `QueueResponse`;
  `POST …/run` → body `ImprovementRunRequest` = `{ lesson_ids: string[] }`, 200 `ImprovementRunResponse`
  (op `:5875`); `POST …/{proposal_id}/review` → body `ProposalReviewRequest` =
  `{ decision: 'approve'|'reject'; edited_blocks?: Record<string, unknown>[] | null }`, 200
  `ProposalReviewResponse` (op `:5972`); `POST …/{proposal_id}/critique` → no body, 200 `LearnCardOut`.
- Produces: all six hooks keep their current signatures, **including**
  `ReviewProposalInput.editedBlocks?: unknown[]` — see step 5 for why.

- [ ] **Step 1: `fetchProposals`.**

```ts
async function fetchProposals(params: ProposalsParams): Promise<ProposalListResponse> {
  const limit = params.limit ?? PROPOSAL_PAGE_SIZE
  const offset = ((params.page ?? 1) - 1) * limit
  const { data, error } = await client.GET('/api/admin/content-improvement', {
    params: { query: { status: params.status, limit, offset } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load content proposals.'))
  return data
}
```

- [ ] **Step 2: `fetchProposal`.**

```ts
async function fetchProposal(proposalId: string): Promise<ProposalDetailOut> {
  const { data, error } = await client.GET('/api/admin/content-improvement/{proposal_id}', {
    params: { path: { proposal_id: proposalId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load the proposal.'))
  return data
}
```

- [ ] **Step 3: `fetchImprovementQueue`.**

```ts
async function fetchImprovementQueue(): Promise<ImprovementQueueResponse> {
  const { data, error } = await client.GET('/api/admin/content-improvement/queue')
  if (!data) throw new Error(errorMessage(error, 'Failed to load the draft queue.'))
  return data
}
```

- [ ] **Step 4: `runImprovement`.**

```ts
async function runImprovement(lessonIds: string[]): Promise<ImprovementRunResponse> {
  const { data, error } = await client.POST('/api/admin/content-improvement/run', {
    body: { lesson_ids: lessonIds },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to run the improvement pass.'))
  return data
}
```

- [ ] **Step 5: `reviewProposal` — the one place the schema is stricter than the app.**
      `ProposalDetailOut.base_blocks` / `proposed_blocks` are typed `unknown[]` (`schema.d.ts:3049,3051`),
      but `ProposalReviewRequest.edited_blocks` is `Record<string, unknown>[] | null` (`:3105`). Rather
      than churn `ReviewProposalInput`, `ContentImprovementPage`'s `workingBlocks` state and
      `ProposalDiff`'s props to chase that difference, narrow once at the boundary:

```ts
async function reviewProposal({ proposalId, decision, editedBlocks }: ReviewProposalInput): Promise<ProposalReviewResponse> {
  const { data, error } = await client.POST('/api/admin/content-improvement/{proposal_id}/review', {
    params: { path: { proposal_id: proposalId } },
    body: {
      decision,
      // The generated request type says `Record<string, unknown>[]` while every
      // block-carrying surface in the app (and ProposalDetailOut itself) says
      // `unknown[]`. Blocks ARE objects by contract — validate_content_blocks
      // rejects anything else server-side — so this is the single narrowing cast,
      // kept at the API boundary instead of pushed into three components.
      edited_blocks: (editedBlocks ?? null) as Record<string, unknown>[] | null,
    },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to review the proposal.'))
  return data
}
```

- [ ] **Step 6: `generateLearnCard`.**

```ts
async function generateLearnCard(proposalId: string): Promise<LearnCardOut> {
  const { data, error } = await client.POST('/api/admin/content-improvement/{proposal_id}/critique', {
    params: { path: { proposal_id: proposalId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to generate the learn card.'))
  return data
}
```

- [ ] **Step 7: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 8: Verify (manual browser check)**
      As an **admin**, `http://localhost:5173/admin/content-improvement`.
      **(a)** **Expected:** the proposal list renders, the **Content AI** sidebar badge matches the number
      of **Pending** proposals, and the status pills filter the list.
      **(b)** On a pending proposal click **Review changes**. **Expected:** the before/after comparison
      appears along with the source feedback quotes. Click **Edit the draft** — **expected:** the block
      editor appears seeded with the draft. Click **Back to comparison**, then **Hide changes**.
      **(c)** *(spends tokens — do once, on a throwaway lesson)* Click **Draft proposals**, pick one lesson
      from the queue, confirm. **Expected:** a new pending proposal appears for it.
      **(d)** *(writes live content — use a throwaway lesson)* Accept one proposal via its two-step confirm.
      **Expected:** its chip becomes "Approved", and opening the lesson shows the new text. Then click the
      learn-card action on that row. **Expected:** "Generating…" then a learn card with the agent's
      self-critique.

- [ ] **Step 9: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/api.ts
git commit -m "$(cat <<'EOF'
refactor(frontend): type the content-improvement calls (review 8.2d)

One documented narrowing cast remains at the boundary: the generated request type
says edited_blocks is Record<string, unknown>[] while ProposalDetailOut and every
block-carrying component say unknown[].

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* accepting a proposal **rewrites live lesson content**, so a broken
`edited_blocks` payload could publish the wrong blocks. Do step 8(d) on a throwaway lesson only, and
confirm the lesson reads correctly afterwards as a learner would see it. *Admin:* the run and critique
endpoints spend model tokens — one run each, as noted.

---

### Task 17: Type the calibration-notes calls and delete the `api.ts` hatch (8.2e)

**Files:**
- Modify: `frontend/src/pages/admin2/api.ts` (`fetchCalibrationNotes` lines 1015-1023;
  `reviewCalibrationNote` lines 1037-1042; `graduateCalibrationNote` lines 1056-1063; then **delete**
  lines 44-65, the whole "Interim raw-fetch escape hatch" block)

**Interfaces:**
- Verified in schema: `GET /api/admin/calibration-notes` → query
  `{ status?: 'suggested'|'approved'|'rejected'|'retired'|null; limit?: number; offset?: number }`, 200
  `CalibrationNoteListResponse` (op `:6038`); `POST …/{note_id}/review` → body
  `CalibrationNoteReviewRequest` = `{ decision: 'approve'|'reject' }`, 200
  `CalibrationNoteReviewResponse` (op `:6071`); `POST …/{note_id}/graduate` → no body, 200
  `CalibrationNoteGraduateResponse` (op `:6106`).
- Produces: after this task `pages/admin2/api.ts` contains **no casts at all** and imports only
  `client`, `errorMessage` and the domain type aliases.

- [ ] **Step 1: `fetchCalibrationNotes`.**

```ts
async function fetchCalibrationNotes(params: CalibrationNotesParams): Promise<CalibrationNoteListResponse> {
  const limit = params.limit ?? CALIBRATION_NOTE_PAGE_SIZE
  const offset = ((params.page ?? 1) - 1) * limit
  const { data, error } = await client.GET('/api/admin/calibration-notes', {
    params: { query: { status: params.status, limit, offset } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load calibration notes.'))
  return data
}
```

- [ ] **Step 2: `reviewCalibrationNote`.** The endpoint answers 200 with the resulting status; the caller
      does not use it, so keep returning `void` and check `error`:

```ts
async function reviewCalibrationNote({ noteId, decision }: ReviewCalibrationNoteInput): Promise<void> {
  const { error } = await client.POST('/api/admin/calibration-notes/{note_id}/review', {
    params: { path: { note_id: noteId } },
    body: { decision },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to review the note.'))
}
```

- [ ] **Step 3: `graduateCalibrationNote`.**

```ts
async function graduateCalibrationNote(noteId: string): Promise<CalibrationNoteGraduateResponse> {
  const { data, error } = await client.POST('/api/admin/calibration-notes/{note_id}/graduate', {
    params: { path: { note_id: noteId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to graduate the note.'))
  return data
}
```

- [ ] **Step 4: Delete the hatch.** Remove the entire block from the
      `// ── Interim raw-fetch escape hatch ───` comment through the closing brace of `rawRequest`
      (lines 44-65), i.e. `RawInit`, `RawResult`, `RawMethod`, `RawClient` and `rawRequest`.

- [ ] **Step 5: Prove no consumer is left.**

```bash
cd frontend && grep -n "rawRequest\|as unknown as" src/pages/admin2/api.ts
```

      **Expected:** no output.

- [ ] **Step 6: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 7: Verify (manual browser check)**
      As an **admin**, `http://localhost:5173/admin/content-improvement` → the **Learn cards** tab.
      **Expected:** suggested calibration notes render, and the tab's count badge matches the number of
      suggested notes. Approve one — **expected:** it moves out of "suggested" and the badge drops. On an
      approved note use the graduate action — **expected:** it returns the line to paste into
      `house_style.md` and the note is retired. Then, to prove nothing else on the admin panel regressed,
      click through **every** sidebar section once (Dashboard, People, Assignments, Feedback, Content AI,
      Projects, Email templates, System prompts, Setup) — **expected:** each renders with data, no red
      error box anywhere.

- [ ] **Step 8: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/pages/admin2/api.ts
git commit -m "$(cat <<'EOF'
refactor(frontend): type calibration-notes calls and delete the api.ts raw hatch (review 8.2e)

pages/admin2/api.ts now has no casts: every admin call goes through the
generated openapi-fetch client, so a path/verb/param typo is a build error.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* approved calibration notes steer how the AI drafts future lesson content,
so a broken approve path changes what learners eventually read — but nothing immediate. *Admin:* step 7's
walk of all nine sections is the real safety net for the whole 8.2 family; treat it as required.

---

### Task 18: Type the learner interview calls and delete the `interviewApi` hatch (8.2f)

**Files:**
- Modify: `frontend/src/lib/interviewApi.ts` (whole file, 44 lines)

**Interfaces:**
- Verified in schema: `GET /api/interview/me` → no params, 200 `InterviewStateResponse` (op `:5539`);
  `POST /api/interview/opener` → no body, 200 `InterviewOpenerResponse` =
  `{ conversation_id: string; greeting: string }` (op `:5559`); `POST /api/interview/playbook` → no body,
  200 `PlaybookResponse` = `{ playbook: PlaybookShared }` (op `:5580`).
- Produces: the three exported functions keep their exact current signatures —
  `getInterviewState(): Promise<InterviewState>`, `buildPlaybook(): Promise<PlaybookShared>`,
  `openInterview(): Promise<{ conversation_id: string; greeting: string }>` — so
  `src/pages/Interview.tsx` needs no changes.

- [ ] **Step 1: Rewrite the file without the hatch.**

```ts
// Learner-facing interview endpoints (AI Interviewer feature), typed through the
// generated client: all three paths are in src/api/schema.d.ts.
import { client, errorMessage } from '../api/client'
import type { InterviewState, PlaybookShared } from '../types/domain'

export async function getInterviewState(): Promise<InterviewState> {
  const { data, error } = await client.GET('/api/interview/me')
  if (!data) throw new Error(errorMessage(error, 'Failed to load your interview.'))
  return data
}

export async function buildPlaybook(): Promise<PlaybookShared> {
  const { data, error } = await client.POST('/api/interview/playbook')
  if (!data) throw new Error(errorMessage(error, 'Could not build your playbook.'))
  return data.playbook
}

export async function openInterview(): Promise<{ conversation_id: string; greeting: string }> {
  const { data, error } = await client.POST('/api/interview/opener')
  if (!data) throw new Error(errorMessage(error, 'Could not start the interview.'))
  return data
}
```

      If `typecheck` insists on a second argument for the two bodyless POSTs, pass `{}` rather than
      reintroducing a cast.

- [ ] **Step 2: Prove the hatch is gone from the whole tree.**

```bash
cd frontend && grep -rn "as unknown as" src --include="*.ts" --include="*.tsx"
```

      **Expected:** no output at all (this was the last of the two).

- [ ] **Step 3: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 4: Verify (manual browser check — learner path)**
      Sign in as a **test learner** whose project has the Interview enabled (check `/admin/projects` → the
      project → **Interview** row toggles). Open `http://localhost:5173/interview`.
      **(a) Fresh start:** if the account has never done it, **expected:** the welcome screen, then clicking
      start shows the interviewer's opening question within a few seconds.
      **(b) Resume:** send one message, reload the page. **Expected:** the conversation is still there.
      **(c) Playbook:** click **Build my playbook**. **Expected:** the "Building your playbook…" screen,
      then the finished playbook with use-cases and next moves. Reload — **expected:** the playbook renders
      from saved state.
      **(d)** Back on the journey home (`http://localhost:5173/`), **expected:** the Interview pill reflects
      the new status.
      *(To re-run: as admin, People → that user → interview card → Reset interview.)*

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add frontend/src/lib/interviewApi.ts
git commit -m "$(cat <<'EOF'
refactor(frontend): type the learner interview calls, dropping the last raw hatch (review 8.2f)

No `as unknown as` casts remain anywhere in frontend/src.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* this is a live learner-facing feature — the whole of step 4 is the check,
and it must be run on a test account rather than a real participant's (building a playbook writes state).
*Admin:* none, beyond the reset action used to re-run the check.

---

## Task 19: Delete the three dead files/exports (9.1, first half)

**Files:**
- Delete: `frontend/src/pages/admin/SetupView.tsx` (170 lines)
- Delete: `frontend/src/pages/admin2/Placeholder.tsx` (16 lines)
- Modify: `frontend/src/types/domain.ts` (remove `ResetLinkEntry`, lines 32-40)

**Interfaces:**
- Produces: nothing new. This task only removes surface.

- [ ] **Step 1: Prove each one really is unused before deleting it.**

```bash
cd frontend
grep -rn "SetupView" src --include="*.ts" --include="*.tsx"
grep -rn "Placeholder" src/pages --include="*.tsx"
grep -rn "ResetLinkEntry" src --include="*.ts" --include="*.tsx"
```

      **Expected:** `SetupView` appears only in its own file and in two *comments*
      (`admin2/SetupPage.tsx`, `admin/adminStyles.ts`); `Placeholder` in `admin2/Placeholder.tsx` plus the
      unrelated local `Placeholder` helpers inside `blocks/ImageBlock.tsx` and `blocks/VideoBlock.tsx`
      (**do not touch those**); `ResetLinkEntry` only in `types/domain.ts`. If any real import shows up,
      stop and report instead of deleting.

- [ ] **Step 2: Delete the two files.**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git rm frontend/src/pages/admin/SetupView.tsx frontend/src/pages/admin2/Placeholder.tsx
```

- [ ] **Step 3: Remove `ResetLinkEntry`** from `types/domain.ts` — the comment block plus the interface
      (lines 32-40). Keep the `EmailStatus` alias above it (line 30): it is used elsewhere.

- [ ] **Step 4: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 5: Verify (manual browser check)**
      As an **admin**, open `http://localhost:5173/admin/setup`. **Expected:** the real Setup page (add
      company / add project forms and the existing-companies list) renders and works — create a throwaway
      company to confirm, then a project under it. Then click every other sidebar section once —
      **expected:** no "Coming soon" stub appears anywhere and nothing errors.

- [ ] **Step 6: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add -A frontend/src
git commit -m "$(cat <<'EOF'
chore(frontend): delete dead SetupView, Placeholder and ResetLinkEntry (review 9.1)

admin2/SetupPage re-implemented SetupView on the kit; all nine admin routes now
render real pages, so the Coming-soon stub is unreachable; ResetLinkEntry had no
consumers.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none. *Admin:* only if step 1's greps were misread — the build gate would
catch a real import as a compile error, which is why the greps come first and the build runs before the
commit.

---

## Task 20: Fold `pages/admin/` into `admin2/kit/` and delete the folder (9.1, second half)

**Files:**
- Create: `frontend/src/pages/admin2/kit/legacyStyles.ts` (moved from `frontend/src/pages/admin/adminStyles.ts`)
- Create: `frontend/src/pages/admin2/kit/legacyHelpers.tsx` (moved from `frontend/src/pages/admin/adminHelpers.tsx`)
- Create: `frontend/src/pages/admin2/BulkInviteModal.tsx` (moved from `frontend/src/pages/admin/BulkInviteModal.tsx`)
- Create: `frontend/src/pages/admin2/EmailTemplatesCard.tsx` (moved from `frontend/src/pages/admin/EmailTemplatesCard.tsx`)
- Create: `frontend/src/pages/admin2/SurveyResults.tsx` (moved from `frontend/src/pages/admin/SurveyResults.tsx`)
- Delete: the now-empty `frontend/src/pages/admin/` directory
- Modify (import paths only): `frontend/src/pages/admin2/CalibrationNotesQueue.tsx:2`,
  `ContentImprovementPage.tsx:2`, `FeedbackPage.tsx:2`, `InterviewCard.tsx:3`, `PeoplePage.tsx:4,5`,
  `ProjectsPage.tsx:5`, `PromptsPage.tsx:2`, `TemplatesPage.tsx:2`, `UserDetailPage.tsx:4,5`
- Modify: `frontend/src/pages/admin2/kit/index.ts` (re-export the moved helpers)

**Interfaces:**
- Produces: `formatDate`, `LevelBadge`, `BandBadge`, `RungPill` become kit exports
  (`import { formatDate, LevelBadge } from './kit'` from an `admin2/` page,
  `from '../kit'` is not needed since the pages sit one level above `kit/`). `COMPONENT_KEYS` /
  `COMPONENT_LABELS` and the `s` style dictionary move to `kit/legacyStyles.ts`. The three moved
  components keep their default exports and prop shapes unchanged.
- Consumes: `Field` (exported by the old `adminHelpers`) had exactly one consumer — `SetupView`, deleted
  in Task 19 — so drop it during the move.

> **Why "legacy" names:** these files carry the pre-kit inline-style system. Naming them
> `legacyStyles`/`legacyHelpers` inside `kit/` makes the remaining debt visible and greppable without
> blocking this deletion on the styling-convergence work (Task 21, optional).

- [ ] **Step 1: Move the two shared modules with git so history follows.**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git mv frontend/src/pages/admin/adminStyles.ts frontend/src/pages/admin2/kit/legacyStyles.ts
git mv frontend/src/pages/admin/adminHelpers.tsx frontend/src/pages/admin2/kit/legacyHelpers.tsx
```

- [ ] **Step 2: Fix the relative imports inside the moved files.** `legacyStyles.ts` currently reaches up
      two levels (`../../lib/constants`, `../../lib/levels`) and now sits one level deeper, so its first
      lines become:

```ts
import type { CSSProperties } from 'react'
import type { ComponentKey } from '../../../lib/constants'
import { levelByCode, type AssignableLevel } from '../../../lib/levels'
```

      In `legacyHelpers.tsx`, update the two imports to the new filename and drop the `Field` component
      (its only caller was the deleted `SetupView`):

```tsx
import { s, LEVEL_STYLE, BAND_STYLE, RUNG_LABELS, RUNG_COLORS, RUNG_TEXT } from './legacyStyles'
import type { ScoreLevel, UsageBand } from './legacyStyles'
```

      Also update its header comment: these are the pre-kit badge helpers, kept until the styling
      convergence lands. Keep the existing `eslint-disable-next-line react-refresh/only-export-components`
      on `formatDate` — the file still mixes components and helpers.

- [ ] **Step 3: Move the three components.**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git mv frontend/src/pages/admin/BulkInviteModal.tsx frontend/src/pages/admin2/BulkInviteModal.tsx
git mv frontend/src/pages/admin/EmailTemplatesCard.tsx frontend/src/pages/admin2/EmailTemplatesCard.tsx
git mv frontend/src/pages/admin/SurveyResults.tsx frontend/src/pages/admin2/SurveyResults.tsx
```

      Then fix each one's imports. They now live one level *shallower* relative to `src/`, so
      `../../api/...`-style paths stay correct, but the style/helper imports change:

```tsx
// BulkInviteModal.tsx and EmailTemplatesCard.tsx
import { s } from './kit/legacyStyles'
```

```tsx
// SurveyResults.tsx
import { s } from './kit/legacyStyles'
import { LevelBadge, BandBadge, RungPill, formatDate } from './kit/legacyHelpers'
```

      Check every other relative import in the three files after the move and fix any that were
      `../../` and now need `../` (the build gate will name them precisely if you miss one).

- [ ] **Step 4: Re-export the helpers from the kit barrel.** Append to `kit/index.ts`:

```ts
// Pre-kit helpers, still used by several screens — see kit/legacyStyles.ts.
export { formatDate, LevelBadge, BandBadge, RungPill } from './legacyHelpers'
export { COMPONENT_KEYS, COMPONENT_LABELS, s as legacyStyles } from './legacyStyles'
```

- [ ] **Step 5: Repoint the ten consuming import lines.**

| File | Was | Becomes |
|---|---|---|
| `admin2/CalibrationNotesQueue.tsx:2` | `import { formatDate } from '../admin/adminHelpers'` | `import { formatDate } from './kit'` |
| `admin2/ContentImprovementPage.tsx:2` | same | `import { formatDate } from './kit'` |
| `admin2/FeedbackPage.tsx:2` | same | `import { formatDate } from './kit'` |
| `admin2/PromptsPage.tsx:2` | same | `import { formatDate } from './kit'` |
| `admin2/PeoplePage.tsx:4` | `import { LevelBadge, formatDate } from '../admin/adminHelpers'` | `import { LevelBadge, formatDate } from './kit'` |
| `admin2/PeoplePage.tsx:5` | `import BulkInviteModal from '../admin/BulkInviteModal'` | `import BulkInviteModal from './BulkInviteModal'` |
| `admin2/UserDetailPage.tsx:4` | `import { LevelBadge, formatDate } from '../admin/adminHelpers'` | `import { LevelBadge, formatDate } from './kit'` |
| `admin2/UserDetailPage.tsx:5` | `import SurveyResults from '../admin/SurveyResults'` | `import SurveyResults from './SurveyResults'` |
| `admin2/TemplatesPage.tsx:2` | `import EmailTemplatesCard from '../admin/EmailTemplatesCard'` | `import EmailTemplatesCard from './EmailTemplatesCard'` |
| `admin2/ProjectsPage.tsx:5` | `import { COMPONENT_KEYS, COMPONENT_LABELS } from '../admin/adminStyles'` | `import { COMPONENT_KEYS, COMPONENT_LABELS } from './kit'` |
| `admin2/InterviewCard.tsx:3` | `import { s } from '../admin/adminStyles'` | `import { legacyStyles as s } from './kit'` |

      Where a file already imports from `'./kit'`, merge the names into that existing import rather than
      adding a second line.

- [ ] **Step 6: Confirm `pages/admin/` is gone and nothing references it.**

```bash
cd frontend
ls src/pages/admin 2>&1        # expect: No such file or directory
grep -rn "admin/adminHelpers\|admin/adminStyles\|admin/BulkInviteModal\|admin/EmailTemplatesCard\|admin/SurveyResults\|pages/admin/" src --include="*.ts" --include="*.tsx"
```

      The `grep` should print **nothing** (comments in the moved files that still say "pages/admin/…"
      should be updated as you go).

- [ ] **Step 7: Verify (build gate)** — `cd frontend && npm run typecheck && npm run lint && npm run build`

- [ ] **Step 8: Verify (manual browser check — the four screens that use the moved code)**
      As an **admin**:
      **(a)** `/admin/people` — **expected:** the table renders with **maturity badges** (coloured level
      chips) and **Last active** dates. Click **Bulk invite (CSV)** with a project scoped — **expected:**
      the CSV modal opens and looks unchanged; cancel it.
      **(b)** `/admin/people` → a participant with a completed assessment — **expected:** the survey
      results section renders with its level/band badges and rung pills, and the interview card's headings
      ("Shared playbook", "Input quality", …) are styled as before (that is the `legacyStyles` import).
      **(c)** `/admin/templates` — **expected:** the email-template editor renders, you can switch between
      invite/reset, and **Preview** produces rendered output. Do not save.
      **(d)** `/admin/feedback`, `/admin/content-improvement`, `/admin/prompts` — **expected:** dates
      display as e.g. "31 Jul 2026" everywhere (that is `formatDate`), not as raw ISO strings.

- [ ] **Step 9: Commit**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub/AI ENABLEMENT HUB REBUILD"
git add -A frontend/src
git commit -m "$(cat <<'EOF'
refactor(frontend): fold pages/admin into admin2/kit and delete the folder (review 9.1)

Ten admin2 files imported helpers, styles and three whole components from the
superseded pages/admin tree, so neither tree could be deleted. Moved with git mv
(history preserved) into admin2/ and admin2/kit/legacy{Styles,Helpers}, named so
the remaining pre-kit styling debt stays visible. One admin tree now.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

**Regression risk:** *Learner:* none — everything moved is admin-only. *Admin:* this is a wide,
import-path-only change across ten files; the compiler catches broken paths, but it cannot catch a
component that renders *unstyled* because a style import resolved to the wrong module. Step 8 exists for
exactly that: look at the badges, dates and template editor, not just for absence of errors.

---

## Task 21 (OPTIONAL — split out on purpose): port the four legacy-styled admin surfaces to `adm-*` classes

Task 20 makes `pages/admin/` disappear, but it does **not** remove the pre-kit inline-style system —
`kit/legacyStyles.ts`'s `s` dictionary still backs `BulkInviteModal`, `EmailTemplatesCard`,
`SurveyResults` and three style keys in `InterviewCard`. Converting them is a design task, not a
mechanical one, so it is deliberately separate and optional.

Measured scope (counted while writing this plan): `InterviewCard` uses only **3** keys
(`surveyQLabel`, `surveyQText`, `panelSectionTitle`); `SurveyResults` **4**; `BulkInviteModal` **11**;
`EmailTemplatesCard` **15**.

**Files:**
- Modify: `frontend/src/styles/admin.css` (add the handful of classes the four surfaces need)
- Modify: `frontend/src/pages/admin2/InterviewCard.tsx`, `SurveyResults.tsx`, `BulkInviteModal.tsx`,
  `EmailTemplatesCard.tsx`
- Delete (last step only): `frontend/src/pages/admin2/kit/legacyStyles.ts`'s `s` export and
  `kit/legacyHelpers.tsx`'s use of it

- [ ] **Step 1: Port `InterviewCard` first (3 keys).** Add `adm-field-label` and `adm-quoted-text`
      classes to `admin.css` mirroring `surveyQLabel` / `surveyQText`, reuse the existing
      `adm-section-title` for `panelSectionTitle`, and replace the six `style={s.…}` sites.
- [ ] **Step 2: Port `SurveyResults` (4 keys), then `BulkInviteModal` (11), then `EmailTemplatesCard` (15)** —
      one file per commit, each with its own build gate and manual check.
- [ ] **Step 3: Move the badge helpers' styling into classes** so `legacyHelpers.tsx` no longer imports `s`,
      then delete the `s` dictionary, keeping `COMPONENT_KEYS`/`COMPONENT_LABELS` (rename the file to
      `kit/componentKeys.ts`).
- [ ] **Step 4: Verify (build gate)** `cd frontend && npm run typecheck && npm run lint && npm run build`
- [ ] **Step 5: Verify (manual browser check)** For each ported file, open its screen and compare against a
      screenshot taken before the change: `/admin/people` → a participant (survey results + interview
      card), `/admin/people` → Bulk invite (CSV), `/admin/templates`. **Expected:** visually identical.
- [ ] **Step 6: Commit** one commit per ported file.

**Regression risk:** *Learner:* none. *Admin:* purely visual, and visual regressions are exactly what no
automated check here can catch — take before/after screenshots.

---

## Deferred follow-ups (explicitly NOT tasks in this plan)

- **Styling convergence (review 8's cohesion finding).** Four styling systems coexist: `--dlw-*` tokens
  in `index.css`, the `adm-*` class system in `styles/admin.css`, the pre-kit inline `s` dictionaries,
  and ~300 ad-hoc `style={{…}}` objects with hardcoded hexes that duplicate existing tokens. Task 21
  chips at the third; converging the fourth is its own project and is not scoped here.
- **The five suppressed `exhaustive-deps`** (`LearningPathNew.tsx:391,466`, `Interview.tsx:395`,
  `EmailTemplatesCard.tsx:91`, `QuizBlock.tsx:32`). Fixing the LearningPathNew pair properly means
  converting `isDone`/`isUnlocked`/`firstCurrent`/`predSatisfied` (`:253-308`) to `useCallback` so the
  dependency arrays can be honest — that is the app's most load-bearing learner screen (maturity gating,
  prerequisite locks, the self-propelling ladder), it has no tests, and each suppression carries a written
  rationale. Do it as its own plan with its own manual matrix of lock states, not as a step here.
- **`/dev-chat` is still routed** (`App.tsx`, admin-gated, self-labelled "Delete once Batch B mounts
  ChatPanel for real"). **Flagged, not removed:** Batch B has not landed, and this route is currently the
  only harness for the chat panel. Task 10 does move it into its own lazy chunk, so it no longer costs
  learners anything. Revisit when Batch B ships.
- **`AuthContext`'s unmemoized value object** (`contexts/AuthContext.tsx:121-132`). Real but negligible:
  the provider re-renders only when `user` changes and every callback is already `useCallback`'d. Left
  alone deliberately — wrapping it in `useMemo` is a one-line change with a non-zero chance of subtly
  altering auth-gate timing, for no measurable gain.
- **`/api/admin/learning` returns every user in scope, unpaginated** (`api.ts` `fetchLearning`, which the
  matrix depends on). Task 5 makes the client cheap, but the payload itself grows with the participant
  count; adding paging is a backend + frontend contract change.
- **Table rows would ideally contain a real `<Link>`** rather than a `tabIndex`-ed `<tr>` (Task 8 step 2's
  note). That changes the `Table` row-click contract and `PeoplePage`'s first column, so it is left for
  whenever the People table is next revisited.
