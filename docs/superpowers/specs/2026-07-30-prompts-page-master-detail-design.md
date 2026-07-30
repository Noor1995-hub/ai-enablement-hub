# System Prompts page → master–detail layout — design (2026-07-30)

**Branch:** `feature/prompts-page-redesign` (off `main` `4c2d27a`, which shipped the prompt editor).

## Goal
Make it obvious which prompt you're editing on the admin **System prompts** page (`/admin/prompts`).

## Problem
Today the page stacks three group Cards (*Interviewer / Chat / Content (Plan C/D/E)*), each a list of
clickable rows, and renders a **single editor panel below all of them**. Clicking a row swaps that
bottom panel — but on a tall page the editor is off-screen, so selecting a prompt appears to do
nothing where the user is looking. The selection (top) and the thing that changes (bottom) are
visually disconnected.

## Design: master–detail (two-column)
Replace the stacked list + bottom-editor with a two-column layout inside the page content:

- **Left column — the list.** The prompt list, still grouped by `group` (*Interviewer / Chat /
  Content (Plan C/D/E)*) with group headers, each row showing the label + the **Edited / Default**
  source chip. The selected row is highlighted. Reuses the existing `PromptRow`. Keeps the
  at-a-glance overview of which prompts are overridden.
- **Right column — the editor.** The existing `PromptEditor`, moved into the right pane, with
  **internals unchanged**: textarea, required-token hint, **Save** (with the confirm modal),
  **Reset to default** (with its confirm), inline missing-token + mutation errors, last-edited.
  Selecting a row on the left updates this pane immediately beside it — the adjacency removes the
  off-screen disconnect.

### Behavior
- **Default selection:** on load, auto-select the first prompt (first group's first row) so the
  right pane is immediately useful — no empty "nothing selected" state.
- **Selection:** unchanged mechanism — local `selectedKind` state in `PromptsPage`; the editor stays
  keyed by `kind` (remount-on-switch) so its `content` state starts clean on each prompt and reseeds
  after a save/reset (the current behavior — see `PromptEditor`'s doc comment).
- **Responsive:** two columns at normal admin width; below a narrow breakpoint it collapses to a
  single column (list above, editor below — roughly today's stacking). Admin is desktop-first, so
  this is a graceful fallback, not the primary target.
- **Last-edited on list rows:** keep it (it already renders per row); it's the only per-row datum
  besides the chip and doesn't crowd a dedicated left column. (If it looks noisy in the narrower
  left column during implementation, dropping it from rows — it still shows in the editor header —
  is an acceptable in-implementation call.)

## Scope
- **Frontend only.** No backend, no API, no new routes, no new dependencies.
- **Touches:** `frontend/src/pages/admin2/PromptsPage.tsx` (restructure the render into two columns;
  add auto-select-first) and `frontend/src/styles/admin.css` (a two-column grid + selected-row /
  responsive styling; reuse existing `adm-*` classes where they fit).
- **Unchanged:** the API hooks (`usePrompts` / `usePrompt` / `useUpdatePrompt` / `useResetPrompt`),
  the `PromptEditor` behavior + validation + confirms, the grouping data, the `/admin/prompts` route
  and nav entry.

## Non-goals
Backend/API changes · new prompt kinds or grouping data · search/filter of the prompt list ·
version history / diff · any change to the editor's save/validation semantics · mobile-first design.

## Testing
- `npm run typecheck && npm run lint && npm run build` clean (the repo has no JS component-test
  runner — the frontend gate is typecheck/lint/build).
- Visual check in the running app: list on the left with group headers + Edited/Default chips;
  clicking a row highlights it and updates the right pane in place; first prompt auto-selected on
  load; narrow-width collapses to single column; Save/Reset/validation still behave as before.
