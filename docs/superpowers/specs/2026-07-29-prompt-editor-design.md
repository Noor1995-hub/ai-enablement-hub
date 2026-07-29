# DB-backed system prompts + admin editor — design (2026-07-29)

**Branch:** `feature/prompt-editor` (worktree `C:\tmp\aiiv2`, off `main` `b430a90`).

## Goal
Let admins view and edit any system prompt from the admin panel and have the change take effect
**live, without a redeploy**. Global (hub-wide), edit-in-place, with a shipped-default fallback and
a confirm-on-save guardrail. This is the documented upgrade path in `docs/ai-agents-plan.md`; it does
NOT include AI self-editing of prompts (that's a separate, later feature needing eval/guardrails).

## Decisions (locked in brainstorming)
- **Scope:** all system prompts, not just the interviewer's. Today that's 9 files under
  `backend/prompts/`: `interview`, `interview_playbook`, `chatbot`, `assessment`, `lesson`,
  `content_improvement`, `content_improvement_critique`, `house_style`, `feedback_triage`. The last
  four are Matthias's Plan C/D/E — **coordinate with him** since the editor surfaces them.
- **Global**, not per-project — one value per prompt kind, hub-wide. `load_prompt(kind)` keeps its
  signature (no project in context).
- **Edit-in-place + reset-to-default** — no version history in v1 (fast-follow; pairs with the future
  self-improvement loop).
- **Confirm-on-save** — saving opens a modal: "This changes the live `<kind>` prompt for everyone,
  immediately. Are you sure?"
- **Placeholder validation** — reject a save that drops a prompt's known-required tokens (below).

## Data model
New table **`prompts`**:
| column | type | notes |
|---|---|---|
| `kind` | text, PK | e.g. `interview_playbook`; matches the file stem |
| `content` | text, not null | the override |
| `updated_at` | timestamptz | `server_default=now()`, `onupdate=now()` |
| `updated_by` | uuid FK users(id), nullable, `ON DELETE SET NULL` | who last edited |

**No row for a kind ⇒ the file is used** (the shipped default). One Alembic migration, chained off
the current single head `f9a0b1c2d3e4`. Coordinate timing with Matthias to avoid a second head.

## The `load_prompt` seam (minimal blast radius)
`load_prompt(kind)` stays **synchronous** so **no call site changes** (chat_service, interview_service,
content_improvement_service, feedback_triage_service — some Matthias's). Redesign its internals:
- Reads from an in-process cache: `_CACHE.get(kind)` → else read the file (current behaviour, the
  ultimate fallback) and cache it.
- A small async `PromptService.refresh()` overlays DB rows into `_CACHE` **at app startup** and
  **after every save/reset**, so edits are live immediately.
- Drop the current `@lru_cache` (replaced by the explicit, bustable `_CACHE`).
- Single replica (`min=max=1`) ⇒ in-process invalidation is sufficient. If ever scaled out, switch to
  a short TTL on `_CACHE` (out of scope now; noted).
- Unit tests (no DB) naturally hit the file fallback → existing prompt-consuming tests unaffected.

## Backend
- `PromptRepository` (get/upsert/delete by kind; list all rows).
- `PromptService`: `list_all()` → for every known kind, `{kind, label, content, source: 'file'|'db',
  updated_at, updated_by}`; `get(kind)`; `update(kind, content, user)` (validate → upsert → refresh
  cache); `reset(kind)` (delete row → refresh cache). Known-kinds list is the union of the prompt
  files + the `load_prompt` call sites.
- Router `/api/admin/prompts`, all `require_admin`: `GET` (overview), `PUT /{kind}` (update),
  `DELETE /{kind}` (reset).
- **Placeholder validation:** a `REQUIRED_TOKENS: dict[kind, list[str]]` registry. On `PUT`, if any
  required token for that kind is absent from the submitted content → `422` with a clear message.
  Registry is built by auditing each consumer (what it `.replace()`/`.format()`s):
  - `interview_playbook` → `{first_name}`, `{assessment_json}`, `{company_context}`, `{transcript}`
    (from `interview_service._generate`).
  - `interview`, `chatbot`, `assessment`, `lesson` → none (interview.md is confirmed slot-free;
    verify the other three during the plan).
  - `content_improvement*`, `house_style`, `feedback_triage` → **audit Matthias's services during
    the plan** and register whatever tokens they interpolate.

## Frontend (admin2)
New **"System prompts"** admin page:
- Overview list of all known kinds: human label, a **source badge** (`Default` vs `Edited`), and
  last-edited (who/when) when edited.
- Click a kind → editor: a textarea (current content), **Save** and **Reset to default**.
- **Save → confirm modal** (the guardrail above). On confirm, `PUT`; on validation `422`, surface the
  missing-token message inline.
- **Reset to default → confirm modal**, then `DELETE`.
- Mirror the existing `admin2` idioms (query hooks in `admin2/api.ts`, the kit components, the
  email-template editor as the closest precedent).

## Testing
- Backend unit: `PromptService` (list/source-labelling, update+validate reject, reset), the seam
  (`load_prompt` file-fallback + cache overlay + bust-on-save), the token registry.
- Backend integration: `/api/admin/prompts` GET/PUT/DELETE + `require_admin` (403) + a DB row
  overriding the file + reset restoring the file + a `422` on a dropped required token.
- Frontend: typecheck / lint / build (repo has no JS component-test runner).

## Non-goals (v1)
Per-project overrides · version history / rollback · AI self-editing of prompts · live preview/test
· editing prompts that aren't loaded via `load_prompt`.

## Coordination
The editor + the `load_prompt` seam touch prompts Matthias owns (Plan C/D/E). The migration must
chain off `f9a0b1c2d3e4` as a single head. Flag both to Matthias before merge.
