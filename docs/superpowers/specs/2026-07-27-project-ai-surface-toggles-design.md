# Project AI-surface toggles — admin Projects card

**Date:** 2026-07-27
**Branch:** `feature/ai-chat-foundation` (has `origin/main`'s admin2 panel merged in)
**Status:** design approved, ready for implementation plan

## Goal

Give the per-project AI-surface enable/disable controls a production home on each
card in [`admin2/ProjectsPage.tsx`](../../../frontend/src/pages/admin2/ProjectsPage.tsx),
replacing the throwaway control in the Batch A verification harness
[`DevChat.tsx`](../../../frontend/src/pages/DevChat.tsx). This is the "Batch B real
admin AI-toggle UI" that Task 18 of the AI-chat-foundation plan deferred while the
admin panel was being rewritten on a concurrent branch.

## Context (what already exists)

- **Backend contract is done and deployed.** `GET /api/admin/projects/{id}/ai` returns
  `{ settings: { chatbot|assessment|lesson|interview: { enabled: bool } } }`;
  `PUT /api/admin/projects/{id}/ai/{kind}` with `{ enabled }` flips one surface (204).
  All four surfaces default to `false`. Both routes are already in the generated
  `frontend/src/api/schema.d.ts`, so the frontend uses the **typed `client`** — no
  `rawRequest` escape hatch. The `project_ai_settings` table (migration `12bf5f54a1e4`)
  is applied to prod but inert until the chat app ships. **No backend change in this work.**
- **The pattern to mirror** is component access: the card's `ProjectComponentToggles`
  child ([`ProjectsPage.tsx:107`](../../../frontend/src/pages/admin2/ProjectsPage.tsx))
  plus the `useComponents` / `useToggleComponent` optimistic hook pair
  ([`api.ts:218`, `api.ts:641`](../../../frontend/src/pages/admin2/api.ts)).
- **DevChat** has two independent parts: a temporary AI-toggle card (its own `projectId`
  input + per-kind buttons) and a `<ChatPanel kind="chatbot" />` pane that does **not**
  depend on the toggle card's state.

## Design

### 1. UI — AI folds into the existing component list (no new section)

The card keeps one list. The three component rows are unchanged **except** the
**Assessment** row gains a **third toggle labelled "AI enabled"**. Two new rows —
**Chatbot** and **Lesson helper** — are appended to the same list, each with a single
"enabled" toggle. **Interview's AI surface is not exposed** (redundant with the Interview
component); Interview keeps only its two component toggles.

```
DELAWARE · AI DI HACKATHON              [People] [Assignments] [Email templates]

  Assessment      (on) visible   (on)  unlocked   (off) AI enabled    Fully available
  Learning path   (on) visible   (off) unlocked                       Shown as locked tile
  Interview       (on) visible   (off) unlocked                       Shown as locked tile
  Chatbot         (off) enabled                                       Off — hidden from learners
  Lesson helper   (off) enabled                                       Off — hidden from learners
```

**Backend surface → UI control:**

| Surface (`kind`) | Control |
|---|---|
| `assessment` | third "AI enabled" switch on the Assessment component row |
| `chatbot` | new "Chatbot" row, single "enabled" switch |
| `lesson` | new "Lesson helper" row, single "enabled" switch |
| `interview` | **not exposed** — never written from this UI, stays default `false` |

- The two AI-only rows are ordinary `adm-comp-row`s: `adm-comp-name` + one
  `adm-switch-label` (button `adm-switch` + text "enabled") + a trailing
  `adm-subtext adm-push-right`. Subtext: **"Enabled for learners"** when on,
  **"Off — hidden from learners"** when off.
- The Assessment row's third switch is just another `adm-switch-label`
  ("AI enabled") after the existing two; the row's existing component-derived subtext
  ("Fully available" / …) is unchanged.
- **No new CSS.** All classes already exist (`adm-comp-list/row/name`, `adm-switch(-label)`,
  `adm-subtext`, `adm-push-right`). The list's `:last-child` border rule now falls on the
  Lesson helper row — correct.

### 2. Frontend types — `domain.ts`

Add one alias mirroring `ComponentState` ([`domain.ts:23`](../../../frontend/src/types/domain.ts)):

```ts
export type AiSurfaceState = components['schemas']['AiSurfaceState']
```

### 3. Frontend hooks — `api.ts`

Add a query + mutation pair, structural copies of `useComponents` / `useToggleComponent`,
using the typed `client`. Query key family: `['admin', 'ai', projectId]`.

```ts
// query
async function fetchAiSettings(projectId: string): Promise<Record<string, AiSurfaceState>> {
  const { data, error } = await client.GET('/api/admin/projects/{project_id}/ai', {
    params: { path: { project_id: projectId } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load AI assistant settings.'))
  return data.settings
}

export function useAiSettings(projectId: string | null) {
  return useQuery({
    queryKey: ['admin', 'ai', projectId] as const,
    queryFn: () => fetchAiSettings(projectId as string),
    enabled: projectId !== null,
  })
}

// mutation
export type AiSurfaceKind = 'chatbot' | 'assessment' | 'lesson' | 'interview'
export interface ToggleAiSettingInput { projectId: string; kind: AiSurfaceKind; enabled: boolean }

async function toggleAiSetting({ projectId, kind, enabled }: ToggleAiSettingInput): Promise<void> {
  const { error } = await client.PUT('/api/admin/projects/{project_id}/ai/{kind}', {
    params: { path: { project_id: projectId, kind } },
    body: { enabled },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to update the AI assistant setting.'))
}

export function useToggleAiSetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: toggleAiSetting,
    onMutate: async ({ projectId, kind, enabled }) => {
      const key = ['admin', 'ai', projectId] as const
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<Record<string, AiSurfaceState>>(key)
      if (previous) {
        queryClient.setQueryData<Record<string, AiSurfaceState>>(key, {
          ...previous,
          [kind]: { enabled },
        })
      }
      return { key, previous }
    },
    onError: (_e, _v, ctx) => { if (ctx?.previous) queryClient.setQueryData(ctx.key, ctx.previous) },
    onSettled: (_d, _e, vars) =>
      void queryClient.invalidateQueries({ queryKey: ['admin', 'ai', vars.projectId] }),
  })
}
```

The optimistic `onMutate`/rollback shape is deliberate — same reason as
`useToggleComponent` (a "busy" flag that clears when `mutateAsync` resolves would let a
rapid second toggle read the stale pre-invalidation cache and revert the first).

### 4. `ProjectsPage.tsx` — extend the per-card child

Rename `ProjectComponentToggles` → **`ProjectSettingsToggles`** (it now owns both the
component and AI settings for one project — hooks still can't loop at page level, so one
child per card stands).

- Consume **both** pairs: `useComponents` + `useToggleComponent` and
  `useAiSettings` + `useToggleAiSetting`.
- **Loading:** spinner while either query is loading.
  **Error:** `ErrorState` if either query errors; its retry refetches both.
- **Busy tracking:** extend the existing `busyKey` scheme with AI keys
  (`ai-assessment`, `ai-chatbot`, `ai-lesson`). Component switches keep their existing
  shared-per-row busy; each AI switch is disabled while its own `ai-<kind>` key is busy.
- **Render:** map `COMPONENT_KEYS` as today; for the `assessment` row only, append a third
  `adm-switch-label` bound to `aiData.assessment?.enabled` → `handleToggleAi('assessment', …)`.
  After the component rows, render two more `adm-comp-row`s for `chatbot` and `lesson`
  from a small local `[{ kind, label }]` list (`Chatbot`, `Lesson helper`).
- **Errors surfaced:** keep the existing bottom `toggleComponent.isError` line and add a
  matching `toggleAiSetting.isError` line (or a shared "Failed to update settings." line).
- Labels: reuse `COMPONENT_LABELS` for components; AI labels are local literals
  (`Chatbot`, `Lesson helper`, and the switch text `AI enabled`). `aria-label`s follow the
  existing convention (e.g. `Chatbot enabled for learners`).

### 5. DevChat cleanup

Strip the temporary toggle card (`DevChat.tsx` ~lines 101–153) and everything that only
served it: state (`projectId`, `settings`, `loadedProjectId`, `loadError`, `loading`,
`togglingKind`, `toggleMessage`, `toggleIsError`), handlers (`loadState`, `toggleKind`),
module constants (`KINDS`, `UUID_RE`), and the now-unused imports (`useState`, `client`,
`errorMessage`, `ChatKind`). What remains: the outer wrapper + `<ChatPanel kind="chatbot" />`,
and an updated header comment noting the AI toggle now lives on the admin Projects card.

**Accepted trade-off** (user's choice): the harness no longer flips surfaces itself — to
chat-test, enable *Chatbot* for your own project on `/admin/projects`, then open `/dev-chat`.
`/dev-chat` and its route stay until Batch B mounts `ChatPanel` for real.

## Testing / verification

- `npm run typecheck && npm run lint && npm run build` clean (run in `frontend/`).
- No backend change → no Python tests affected; `gen:api` not needed (routes already in schema).
- Manual browser pass on `/admin/projects`: toggle Assessment "AI enabled", Chatbot, and
  Lesson helper; confirm each persists across reload; confirm a rapid double-toggle on one
  surface does not revert (the optimistic-cache case); confirm Interview shows only its two
  component toggles.

## Out of scope (YAGNI)

- No "enable all / disable all" bulk control, no per-surface help tooltips.
- No exposure of the `interview` AI surface.
- No change to the AI/chat wiring, the backend, or the `project_ai_settings` schema.
- No change to `/dev-chat`'s route or the `ChatPanel` pane itself.

## Files touched

- `frontend/src/types/domain.ts` — add `AiSurfaceState` alias.
- `frontend/src/pages/admin2/api.ts` — add `useAiSettings` + `useToggleAiSetting`.
- `frontend/src/pages/admin2/ProjectsPage.tsx` — rename + extend the per-card child.
- `frontend/src/pages/DevChat.tsx` — remove the temporary toggle card.
