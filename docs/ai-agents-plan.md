# AI Agents in the Hub — feasibility, design & provider setup (Foundry / Anthropic API)

> **Status (2026-08-10): largely SHIPPED.** The chat foundation, AI interviewer, DB-overridable
> prompts + admin System Prompts page, and feedback-driven content improvement are all live in
> prod (see the root `CLAUDE.md` feature index). This doc remains the authoritative reference
> for the provider seam (§7) and the Anthropic API key / spend-cap setup (§8b); the Foundry
> alternative (§8) is kept as reference. Design details elsewhere in the doc are the original
> plan and may differ from what shipped — trust the code and the per-feature specs.
>
> Original status line (2026-07-23): planning / not started.
>
> **Amended 2026-07-10** after a design challenge — see the "Resolved" list at the end of §10.
>
> **PROVIDER DECIDED 2026-07-23: Anthropic API (direct), Option B — see §7/§8b.** Originally decided
> 2026-07-09 as Azure AI Foundry, reopened 2026-07-10 (Claude quota 0 everywhere on Foundry;
> GlobalStandard-only processing weakened the "in-tenant" rationale), resolved once **IT confirmed
> direct use of the Anthropic API key is allowed** (2026-07-23) — the "dev/test data only until IT
> sign-off" gate in §8b is cleared. Decision drivers (not just "Claude is generally stronger"): the
> interviewer surface's own requirement for a model good at goal-driven probing + structured
> extraction, and the Haiku 4.5 / Sonnet 5 / Opus 4.8 tiering answers the "one model vs small+strong
> split" open question for free, in one vendor/one SDK. Counter-consideration noted and accepted:
> this is the app's first non-Azure vendor dependency and first feature-specific live secret
> (ACS/Entra/Azure PG are all Azure-native with keyless managed identity). The Foundry path in §8 is
> kept as-is (not deleted) since the `LlmClient` seam preserves it as an option if the calculus ever
> changes — see the switching-cost note added to §7.

## 1. What we want to build

Four AI surfaces, all requiring that **every message (both sides) is persisted** so admins can
later see where users struggle / what they're interested in:

1. **General chatbot** — floating icon bottom-right, available on every page.
2. **Assessment deep-dive** — sits alongside the assessment/survey and probes for richer answers
   (follow-up questions, "tell me more", concrete examples). There is no right answer to protect —
   the goal is to get MORE information out of the user during the assessment, not to explain
   questions or steer choices. Its transcript is extra signal for admins: a mini-interview per
   question. (Redefined 2026-07-10 — was "assessment clarifier".)
3. **Lesson helper** — answers questions / helps during a lesson in the learning path.
4. **Interviewer** — a goal-driven agent that interviews the user to surface pain points / AI
   use-cases, and produces a structured summary for admins.

## 2. Key insight: all four are ONE capability

A chatbot, an assessment helper, a lesson helper, and an interviewer are **one LLM-chat capability
with four different system prompts and four different context injections.** Build the plumbing once,
reuse it four times. This is why the effort is modest.

## 3. Shared foundation (build once)

### Backend — one new feature slice (follows `python-be-architecture.md` exactly)

- **2 new tables** (Alembic migration):
  - `conversations` — `id`, `user_id` FK → users, `kind` enum
    (`chatbot`/`assessment`/`lesson`/`interview`), optional `context_ref` (e.g. lesson_id or survey
    question id), `summary` (nullable text/JSONB — for the interviewer's extracted findings),
    `created_on`/`updated_on`. Index on `user_id`.
  - `messages` — `id`, `conversation_id` FK, `role` (`user`/`assistant`/`system`/`tool`),
    `content` text, `metadata` JSONB (token counts, tool calls, model), `created_on`. Index on
    `conversation_id`. **This table IS the "save all dialogue" requirement** — every turn is a row.
- **`LlmService`** — the one genuinely new piece. Thin wrapper over the Foundry chat client
  (mirrors how `EmailService` wraps ACS and `EntraService` wraps OIDC). Feature-flagged like those:
  `Settings.llm: LlmSettings | None` (all-or-nothing), a `LlmClient` Protocol as the seam so tests
  stub it, DI provider 404s / no-ops when unconfigured. `get_llm_service` in `core/dependencies/`.
- **`ChatService` + `ConversationRepository` + `MessageRepository`** — standard layered slice.
  `ChatService` owns the completion loop: persist the user turn → call the model (with tools) →
  stream the assistant turn → persist it on completion → run the tool-call loop if the model asks
  for a tool.
  - **Disconnect-safe persistence (required):** if the user closes the tab or navigates away
    mid-answer, FastAPI cancels the streaming generator — the assistant turn must STILL be saved.
    Persist whatever was generated in a `finally` (or shield the save from cancellation) and mark
    it `truncated: true` in `metadata`. A few lines if built in from day one; if forgotten, the
    "save everything" guarantee fails silently.
- **Streaming router** — `POST /api/chat/{kind}` returning a streaming response
  (FastAPI `StreamingResponse` / SSE — see the bundled FastAPI skill's `streaming.md`). Token-scoped
  via `get_current_user` (see §5). Admin read endpoints under `/admin/*` for analysis (§6).

### Prompt management (decided 2026-07-10)

- **Prompts live in the repo as plain text files** — `backend/prompts/<kind>.md` (chatbot,
  assessment, lesson, interview), loaded by the chat slice at startup. Rationale: a prompt is not
  standalone text — it has slots the code fills (`{lesson_content}`, `{question}`); keeping prompt
  and injection code in one package means they can never drift apart, git gives a full history of
  behavior changes ("why does the bot act differently since last week?" = `git log`), and a prompt
  tweak ships deliberately like any other change (edit the .md, redeploy — minutes via
  `deploy.ps1`). During development, iterate locally in seconds — no deploys involved.
- **Upgrade path, only if live-tweaking becomes a real need** (e.g. admins adjusting the
  interviewer weekly without a dev): promote prompts to a DB table + a small admin edit screen.
  The service seam makes that a contained later feature — do NOT build it up front.
- **Do not manage prompts in the Foundry portal** — it splits the bot's brain across two places,
  has no review trail tied to the code, and drifts toward the server-managed model we rejected (§7).

### Frontend — build once, mount four times

- A `useChat` hook (POST + consume the stream) + a `<ChatPanel>` component. The bottom-right widget
  is one mount; the assessment/lesson helpers mount the same panel with a different `kind` + context;
  the interviewer is its own page/section using the same panel.

### Conversation lifecycle (decided 2026-07-10)

- **Opening the widget starts a NEW conversation.** The panel also shows a **history list** of that
  user's previous conversations (per kind); clicking one reopens it, and further messages continue
  that same conversation.
- Two small extra endpoints (own data only, token-scoped as always):
  `GET /api/chat/conversations?kind=` (list mine) and `GET /api/chat/conversations/{id}` (load one
  of mine, with messages). `POST /api/chat/{kind}` accepts an optional `conversation_id` to
  continue an existing one.

## 4. Per-feature effort (on top of the foundation)

| Feature | Extra work | Notes |
|---|---|---|
| **General chatbot** | Smallest — floating button + panel in `AppNav`/`App.tsx`, `kind='chatbot'`. | Hub context in the system prompt. |
| **Assessment deep-dive** | Small — mount panel in `Assessment.tsx`, inject current question + the user's answer so far, `kind='assessment'`. | System prompt: probe for elaboration, examples and the "why" behind answers — never suggest or evaluate an answer. |
| **Lesson helper** | Small — mount in `LessonPage.tsx`, inject the lesson's `content_blocks` (already loaded there). `kind='lesson'`. | RAG-lite: current lesson text in context, no vector DB needed. |
| **Interviewer** | Largest of the four — multi-turn goal-driven agent + a "wrap up & summarize" step writing structured findings to `conversations.summary`. | Use structured output (JSON) for the extracted pain points/use-cases so admins get more than a raw transcript. |

## 5. Data access, isolation & performance (the three questions answered)

### Readable by the agent?
Yes — but the agent **never touches the DB directly.** It gets a small set of **function tools**
that are thin wrappers over existing service/repository methods (e.g. `get_journey`,
`survey_status`, current lesson blocks, assigned tracks). The model requests data by calling those
functions; they return typed Pydantic objects. `me.py` is the template (compose existing services).
For the lesson/assessment helpers, often no tool is needed — the context is already in the request.

### Can agent-for-user-X see user-Y's data?
**No — structurally, not by discipline.** Every authenticated request resolves the `User` from the
**token only** (`get_current_user` in `core/dependencies/auth.py`: `user_id = claims["sub"]`). The
iron rule (CLAUDE.md): *no endpoint outside `/admin/*` accepts a user identifier from the request.*

**The design rule that makes cross-user leakage impossible:**
> Every data tool given to the agent is hard-scoped to `user.id` from the token. **No tool accepts a
> user identifier as an argument, and the agent gets no raw-SQL / generic-query tool.** Identity is
> injected from the token, never chosen by the model.

Hold that line and a prompt-injected/confused model *cannot* address another user's data — the
parameter doesn't exist. Extend the existing authz test matrix (endpoint × 3 auth levels) to the new
chat endpoints. The interviewer/admin analysis views are the deliberate exception: they live under
`/admin/*`, take user_ids, and are gated by `require_admin` — exactly like `GET /api/admin/surveys`.

### Rapid access / performance?
The **database is never the bottleneck.** Azure PostgreSQL is co-located (same region,
swedencentral), `asyncpg` + pooling + `pool_pre_ping`, all async; per-user indexed lookups are
single-digit ms. The `conversations`/`messages` tables are indexed on `user_id`/`conversation_id`.
**The latency is the model (100s of ms–seconds), 100–1000× the DB.** Mitigations:
- **Stream** the response (time-to-first-token dominates perceived latency; the DB fetch to build
  context is lost in the noise).
- **Don't replay unbounded history** — store everything in the DB (cheap), but only send the last
  N turns to the model (plain window cap; decided 2026-07-10 — no running-summary machinery in v1).
- **Single-replica caveat:** the container app is pinned `min=max=1` (rate limiter + cleanup are
  in-process). Many concurrent streaming chats each hold a connection; if usage grows, revisit that
  scaling constraint. Launch-time concern only.

## 6. Persistence & admin analysis (the core requirement)
Persistence is the storage layer, not a bolt-on — every turn is a `messages` row, so "save
everything" is free. For analysis: admin read endpoints (`GET /api/admin/conversations?kind=&user_id=`,
`GET /api/admin/conversations/{id}`) + a view in the existing `Admin.tsx` shell. The interviewer
additionally writes a **structured summary** per conversation (extracted use-cases/pain points) so
admins can aggregate across users without re-reading transcripts. Render transcripts in the admin
viewer as **plain text** (no markdown→HTML) — chat content is untrusted input in an admin's browser.

### Transparency notice (required before launch)
Storing every message for admin review is employee monitoring in EU/GDPR terms (delaware is
Belgian). Ship a visible line in the chat UI — e.g. *"Conversations are stored and may be reviewed
by hub admins to improve the hub."* — and give the internal privacy owner a heads-up before launch.

## 7. Provider / SDK / model decisions

### Provider: DECIDED 2026-07-23 — Anthropic API (Option B)

Reopened 2026-07-10, resolved 2026-07-23 once IT confirmed direct use of the Anthropic API key is
allowed. Comparison kept for reference (Option A remains available via the `LlmClient` seam if the
calculus ever changes):

| | **Option A: Azure AI Foundry** | **Option B: Anthropic API (direct) — CHOSEN** |
|---|---|---|
| Data path | delaware Azure sub, Microsoft terms; GlobalStandard = global (non-EU-pinned) processing | Anthropic (US) under DPA + SCCs; no training on API data; ~30-day retention |
| Models available today | `gpt-4o` (already deployed + verified), gpt-5.x/mini tiers, DeepSeek, Mistral, Grok, Llama, Phi. **NO Claude** (quota 0 everywhere — needs request) | All Claude models immediately (Haiku 4.5 / Sonnet 5 / Opus 4.8) |
| Auth | Managed identity (keyless, recommended) or key | API key only (container-app secret) |
| SDK | `openai` → `AsyncAzureOpenAI` | `anthropic` → `AsyncAnthropic` (native SDK, **no OpenAI-compat shim**) |
| Blocker | Claude quota request (subscription-scoped; Matthias is RG-Owner only → likely IT) — not pursued | none — IT cleared direct key use 2026-07-23 |
| Config | `LLM__PROVIDER=foundry` + `LLM__ENDPOINT`/`LLM__DEPLOYMENT`/`LLM__API_VERSION` | `LLM__PROVIDER=anthropic` + `LLM__MODEL` + `LLM__API_KEY` |

**Decision drivers (2026-07-23):** the interviewer surface explicitly wants a model that's good at
goal-driven probing + structured extraction (§4) — Claude Opus 4.8 fits that better than gpt-4o.
The Haiku 4.5 / Sonnet 5 / Opus 4.8 tiering also answers the open "one model vs small+strong split"
question (§10) for free, in one vendor/one SDK — Foundry would need a second deployed model family
to get the same split. Counter-consideration, accepted knowingly: this is the app's first
non-Azure vendor dependency and first feature-specific live secret (ACS/Entra/Azure PG are all
Azure-native with keyless managed identity) — mitigated by the key-hygiene step in §8b (dedicated
workspace + spend cap, not a personal dev key).

**Build provider-agnostic anyway:** one `LlmClient` Protocol, `AnthropicLlmClient` as the only
adapter built for v1, selected by `LLM__PROVIDER=anthropic`. Everything downstream (ChatService,
persistence, streaming router, prompts) stays provider-blind — cheap insurance, not because the
choice is still open.

**Switching cost if this is ever revisited:** NOT a bare env-var flip — the seam isolates the
change to one new adapter class, but that class has real content: client construction/auth,
system-prompt handling (Anthropic's top-level `system` param vs OpenAI's `role:"system"` message),
translating the streaming event shapes, structured-JSON output for the interviewer (Anthropic has
no native JSON mode — forced `tool_use`; OpenAI has `response_format: json_schema`), and mapping
each SDK's exceptions to `DomainError`. Realistic estimate for a second adapter once the first
exists and the Protocol is solid: half a day to a day, including its own tests. Contained and
low-risk, not a rewrite — but budget for it as real work, not a config change.

### Option A — SDK: `openai` (`AsyncAzureOpenAI`) against the Foundry endpoint
**Deliberate deviation from Microsoft's `get_azure_bestpractices_ai_app` recommendation** (which
pushes Microsoft Agent Framework + `AIProjectClient` with *server-managed* conversation threads).
Reasoning:
- Our #1 requirement is **persist all dialogue in OUR Postgres** for admin analysis + **token-scoped
  tools**. That wants **client-side orchestration** — we own the loop, save every turn, inject
  identity from the token. Server-managed threads (Foundry Agents) would duplicate/fight that.
- The `openai` `AzureOpenAI` client gives native function-calling + streaming and drops cleanly into
  the existing layered `LlmService` seam. `azure-ai-inference` is an equivalent alternative.
- **Revisit the Agent Framework** only if we later want multi-agent workflows / handoffs — the
  `LlmService` seam keeps that option open.
- Install (client side): `pip install openai azure-identity` (add to backend `prod` deps via uv).

### Option B — SDK: `anthropic` (`AsyncAnthropic`), native
- Same client-side-orchestration rationale as Option A: we own the loop, persist every turn in OUR
  Postgres, inject identity from the token. The Anthropic SDK is a plain chat client — no
  server-managed threads to fight.
- **Use the native SDK, not an OpenAI-compatibility shim.** The `LlmClient` Protocol is our
  abstraction layer; a compat shim would be a second, leakier one and isn't the supported surface
  for streaming/tool-use/prompt-caching.
- Async is equally mandatory here: `AsyncAnthropic` (the `AsyncAzureOpenAI` rule from §8 applies
  provider-independently).
- Bonus available on this path: `cache_control` on the static system prompt → ~90% cheaper repeated
  context, which fits the static hub-context prompt design.
- Install (client side): `pip install anthropic` (add to backend `prod` deps via uv).

### Model (Option A): choose at deploy time from the live catalog
Pick a **current small/fast chat model** for the helpers (cost-effective, low latency — e.g. the
`gpt-4o-mini` / GPT‑5‑mini tier) and optionally a **stronger model for the interviewer** (better at
goal-driven probing + structured extraction). **Don't hardcode from memory** — at setup, read the
catalog (`az cognitiveservices account deployment list`, or the Foundry portal / models catalog doc)
and use the current deployment name. The deployment name is what goes in `LLM__DEPLOYMENT`.
(For Option B the "model" is just an ID string — pricing table in §8b.)

## 8. Option A — Azure AI Foundry setup (concrete, kept as reference — not the chosen path)

> **Not pursued for v1** (Anthropic API chosen 2026-07-23, see §7). Kept here because the
> `LlmClient` seam preserves this as a real fallback — nothing below is stale, it's just not the
> next thing to build. All Azure mutations below are ask-first (per the standing rule — read-only
> queries are fine). Nothing here has been run.

**Existing resources (verified 2026-07-09, read-only, RG `imaginemore-playground`,
sub `e2b785b0-d93d-4c19-9537-4f752f759cb1`, swedencentral):**
- **Foundry account already exists:** `imaginemore-playground-mf`
  (`Microsoft.CognitiveServices/accounts`) with project `imaginemore-playground-mf/playground`.
  → **Prototype on this — zero new resources needed.**
- App: container app `ai-enablement-hub`; PG `imaginemore-playground-pg`; ACS/email already wired.

**Access + models verified 2026-07-10 (read-only + one test inference):**
- Matthias has **Owner on the RG + Foundry Owner + Foundry User on the account** — full control
  plane AND data plane, incl. `roleAssignments/write` (can grant the container app's managed
  identity himself, no IT needed).
- **Two deployments already live:** `gpt-4o` (2024-11-20, GlobalStandard, cap 2795) and
  `DeepSeek-V4-Pro` — step 1 below may already be satisfied by `gpt-4o` for prototyping.
- **Keyless AAD inference tested working** against `gpt-4o` (endpoint
  `https://imaginemore-playground-mf.cognitiveservices.azure.com/`, api-version `2024-10-21`).
- Quota headroom in swedencentral for gpt-4o/gpt-5.x(-mini/nano), DeepSeek, Grok, Mistral, Llama,
  Phi. **All `claude-*` meters (and `gpt-5.5`) are quota 0 — in every region of the sub.** Unlock
  via Foundry portal → Management center → Quota → request increase (subscription-scoped; may need
  a subscription admin).

### Resource strategy
- **Now (prototype):** reuse `imaginemore-playground-mf` + project `playground`. Same shared-playground
  pattern already used for ACS email.
- **At cutover / hosting move:** provision a **dedicated** Foundry resource that moves with the app
  (bundle with the IT hosting ticket). The `LlmService` seam means only env vars change.

### Steps
1. **Deploy a chat model** in the Foundry project (portal → the `playground` project → *Models +
   endpoints* → deploy, e.g. a current `gpt-4o-mini`-tier model), OR via CLI:
   `az cognitiveservices account deployment create -g imaginemore-playground -n imaginemore-playground-mf --deployment-name <name> --model-name <model> --model-version <ver> --model-format OpenAI --sku-name GlobalStandard` (ask-first). Note the **deployment name**.
2. **Get the endpoint** (don't guess it): `az cognitiveservices account show -g imaginemore-playground -n imaginemore-playground-mf --query properties.endpoint -o tsv`
   (Azure OpenAI form is typically `https://imaginemore-playground-mf.openai.azure.com/`; the
   AI-services form is `https://imaginemore-playground-mf.services.ai.azure.com/`).
3. **Auth — keyless (Entra ID / managed identity), recommended:**
   - Give the container app a **managed identity** and assign it **`Cognitive Services OpenAI User`**
     on the Foundry account scope. In code use `DefaultAzureCredential` → bearer token
     (`https://cognitiveservices.azure.com/.default`). No key to leak, matches security posture.
   - **Local dev:** `DefaultAzureCredential` uses `az login` — no secret in `.env`.
   - **Fallback (fastest to prototype):** an API key stored as a container-app secret (same pattern
     as `acs-connection-string`/`jwt-secret`) + `LLM__API_KEY`. Migrate to managed identity before
     prod-hardening.
4. **Backend config** (`Settings.llm: LlmSettings | None`, all-or-nothing, `SecretStr` for any key):
   - `LLM__ENDPOINT`, `LLM__DEPLOYMENT`, `LLM__API_VERSION` (e.g. a current `2024-xx-xx` GA/preview),
     and either managed identity (no key) or `LLM__API_KEY`.
   - Local `backend/.env` gets these; prod via `az containerapp secret set` + `--set-env-vars`
     (ask-first), same as the Entra/email wiring.

### Minimal client sketch (Python, `AsyncAzureOpenAI`, keyless + streaming)
```python
# core/configs/llm.py  → LlmSettings (endpoint, deployment, api_version, optional api_key)
# services/llm_service.py — the seam
from openai import AsyncAzureOpenAI
from azure.identity.aio import DefaultAzureCredential
from azure.identity.aio import get_bearer_token_provider

# keyless:
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)
client = AsyncAzureOpenAI(
    azure_endpoint=settings.llm.endpoint,
    api_version=settings.llm.api_version,
    azure_ad_token_provider=token_provider,   # or api_key=... for the fallback
)

stream = await client.chat.completions.create(
    model=settings.llm.deployment,            # the DEPLOYMENT name, not the model name
    messages=[{"role": "system", "content": system_prompt}, *history],
    tools=token_scoped_tools,                 # see §5 — no user_id args
    stream=True,
)
async for chunk in stream:
    delta = chunk.choices[0].delta.content if chunk.choices else None
    if delta:
        yield delta                            # → FastAPI StreamingResponse; persist full text at end
```
**`AsyncAzureOpenAI` is mandatory, not optional (decided 2026-07-10).** The sync-client-in-a-
threadpool pattern (fine for ACS's ~1s email sends) breaks here: a streaming chat holds its thread
for 10–60s and the default threadpool has ~40 threads, so a handful of concurrent chats would
exhaust it on the single replica. Async-all-the-way also matches `python-be-architecture.md`.

## 8b. Option B — Anthropic API setup (concrete) — CHOSEN PATH FOR V1

> **IT governance sign-off cleared 2026-07-23** — direct use of the Anthropic API key is allowed;
> the "dev/test only" gate that applied through 2026-07-10 no longer applies. Matthias has access
> to an API key. **Step 1 below (key hygiene) is the next concrete action.**

### Steps
1. **Key hygiene, split by environment (clarified 2026-07-23 — dev is NOT blocked on this):**
   - **Local dev (unblocks Batch A immediately):** use Matthias's existing personal/dev Anthropic
     key in local `backend/.env` via `LLM__API_KEY` — same precedent as the local `AUTH__JWT_SECRET`
     (root CLAUDE.md "Key facts"), git-ignored, dev-only blast radius. Worth a quick **read-only**
     check in the Anthropic Console first (which org/workspace it belongs to, its spend/rate
     limits) so dev testing doesn't quietly eat someone else's budget — but that's it, no setup
     required to start building. The code never cares which key it holds:
     `settings.llm.api_key` is just a `SecretStr` env var.
   - **Before this is ever wired into the Container App (i.e. before prod, before any real user's
     data flows through it):** create a **dedicated workspace for the hub with its own key and a
     monthly spend cap** — never a personal dev key in the container app. Swapping is then
     `az containerapp secret set` + `--set-env-vars` (ask-first, same pattern as
     `acs-connection-string`) — no code change, no redeploy of the adapter.
2. **Install:** `pip install anthropic` (backend `prod` deps via uv). Native SDK only (§7).
3. **Backend config** (same `Settings.llm: LlmSettings | None` seam, `SecretStr` for the key):
   - `LLM__PROVIDER=anthropic`, `LLM__MODEL=<id from the table below>`, `LLM__API_KEY=<key>`.
   - Local `backend/.env` gets these; prod via `az containerapp secret set` + `--set-env-vars`
     (ask-first), same pattern as `acs-connection-string`.
4. **Model choice** (per-1M-token pricing, checked 2026-07):

   | Model | ID | Input / Output | Hub fit |
   |---|---|---|---|
   | Claude Haiku 4.5 | `claude-haiku-4-5` | $1 / $5 | chatbot + lesson/assessment helpers (fast, cheap) |
   | Claude Sonnet 5 | `claude-sonnet-5` | $3 / $15 (intro $2 / $10 until 2026-08-31) | single-model all-rounder |
   | Claude Opus 4.8 | `claude-opus-4-8` | $5 / $25 | interviewer (goal-driven probing + structured extraction) |

   Typical helper turn (~3K in / ~300 out) ≈ $0.004 (Haiku) – $0.02 (Opus): model cost is
   negligible at internal-tool volume, so pick by capability, not price.

### Minimal client sketch (Python, `AsyncAnthropic`, streaming)
```python
# services/llm_service.py — the AnthropicLlmClient adapter behind the same LlmClient Protocol
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=settings.llm.api_key.get_secret_value())

async with client.messages.stream(
    model=settings.llm.model,             # e.g. "claude-sonnet-5"
    max_tokens=1024,                      # doubles as the Batch-A output-token guardrail
    system=system_prompt,                 # add cache_control for ~90% cheaper repeated context
    messages=history,                     # last-N window, identical to Option A
) as stream:
    async for text in stream.text_stream:
        yield text                        # → FastAPI StreamingResponse
    final = await stream.get_final_message()  # persist + final.usage token counts → messages.metadata
```
Tool use works via `tool_use` content blocks when the tool-call loop lands (deferred out of
Batch A) — the token-scoped-tools rule from §5 is provider-independent.

## 9. Suggested batch plan (in the style of `docs/history/rebuild-plan.md`)
- **Batch A — Foundation:** `LlmService` + config/DI seam (**provider-agnostic:** `LlmClient`
  Protocol + `LLM__PROVIDER`-selected adapter — `AnthropicLlmClient` is the only adapter built for
  v1 per §7, Foundry stays swappable via the seam if ever revisited), `conversations`/`messages` tables +
  migration, `ChatService`/repositories (incl. disconnect-safe persistence), streaming
  `POST /api/chat/{kind}` + the conversation list/continue endpoints, `useChat` + `<ChatPanel>`
  with history list, **guardrails** (max output tokens, per-user rate limit via `core/ratelimit.py`,
  daily turn cap — reclassified into Batch A on 2026-07-10: day-one work, not open options),
  transparency notice in the UI, tests (incl. authz matrix for the new endpoints + the
  no-cross-user-tool guarantee). Deploy dark behind the `Settings.llm` flag. *Bulk of the work.*
  **Recommended: skip the tool-call loop in Batch A** — the helpers get their context injected and
  chatbot v1 runs on a static hub-context system prompt; add the lookup-tools loop later when a
  concrete need shows up in real transcripts.
- **Batch B — Chatbot + assessment + lesson helpers:** three mounts of the panel + three system
  prompts + context injection. ~1 day each incl. browser verification.
- **Batch C — Interviewer + admin analysis:** goal-driven prompt, structured summary extraction +
  storage, admin conversation-viewer in `Admin.tsx`. A few days.

## 10. Open decisions / to confirm next session
- Exact model split: leaning toward Haiku 4.5 for the chatbot/assessment/lesson helpers + Opus 4.8
  for the interviewer (the tiering that motivated the provider choice, §7) — not yet locked in;
  confirm once real transcripts show whether Haiku is sufficient for the helpers.
- Exact value of N for the history window cap.
- Foundry-specific items (managed identity vs key, reusing `imaginemore-playground-mf`, extra
  content filtering) are moot for v1 now that §8 isn't the chosen path — revisit only if Anthropic
  is ever swapped out.

**Resolved 2026-07-10 (moved out of open):** conversation lifecycle = new conversation per
widget-open + history list with resume; plain window cap instead of a running summary; guardrails
and the transparency notice are Batch A work; `AsyncAzureOpenAI` mandatory; disconnect-safe
persistence required; assessment surface redefined from "clarifier" to "deep-dive prober";
admin viewer renders transcripts as plain text; tool-call loop recommended deferred out of Batch A;
prompts live as text files in the repo (2026-07-10; DB + admin edit screen only if live-tweaking
ever becomes a need).

**Resolved 2026-07-23 (moved out of open):** provider = Anthropic API direct (Option B, §7/§8b) —
IT cleared direct use of the API key, closing the "dev/test only" gate that applied from
2026-07-10; `AsyncAnthropic` mandatory (the async-all-the-way rule from 2026-07-10 applies
provider-independently, §8b); Foundry (§8) stays documented as a fallback via the `LlmClient`
seam, not built for v1.
