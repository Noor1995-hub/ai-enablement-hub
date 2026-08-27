# AI Enablement Hub — Content Enrichment Game Plan

**Written:** 2026-07-10. This is the output of a fit-gap analysis (`docs/external-sources/fit-gap-analysis.md`)
and a follow-on brainstorm session that turned its findings into concrete decisions. **This document
records decisions and pointers to source material — it does not contain drafted lesson prose.**
Actual content generation is the next session's job. Read this document and the fit-gap analysis
first; treat the reasoning in the fit-gap analysis as background for *why* each decision below was
made, in case anything here needs re-litigating.

## How to use this document (read this section first)

- **Ground truth on current structure:** `db/baseline/data/{tracks,modules,lessons}.json`. Check
  whether a live DB query path exists in your session before trusting this snapshot as current — it
  was last confirmed accurate 2026-07-09/07-10 (see `db/README.md`'s own staleness caveat). If the
  content generation session runs after other content edits have landed, re-verify lesson IDs and
  titles before writing.
- **Content block schema:** `frontend/src/types/contentBlocks.ts` — block types are `heading`,
  `paragraph`, `callout`, `card_group`, `quiz`, `question`, `whitespace`, `interactive` (sort/predict/
  spot-the-flaw variants), and `try_it_yourself`. Match this schema exactly when drafting
  `content_blocks` JSON.
- **Match the hub's existing voice before drafting anything new.** Pull 2-3 real lessons' full
  `content_blocks` (from `db/baseline/data/lessons.json`, filter by `id` or `title`) and read them
  before writing a single new block. Every existing lesson opens with a concrete, specific scenario
  (a named situation, not an abstract definition) and stays conversational — this is a strong,
  consistent pattern across all 68 lessons and new content should match it, not read like a
  compressed MS Learn/Skilljar summary.
- **External source files** live in `docs/external-sources/*.md` — cited per item below by file and
  section/course title. These are pointers, not text to copy: read the cited section in full before
  drafting, and follow the same framing rule the hub already uses (`external-source-inventory.md`):
  strip vendor/certification framing (Skilljar's "Certificate of completion," MS Learn's "Module
  assessment") when repurposing language.
- **Where this doc says "cross-reference X" or "check for overlap,"** actually open the named lesson
  and read it — these are real continuity risks, the same class of bug the hub found and fixed in
  `scratch_review/example_continuity_sweep.md`. Don't add new content blind to what's already there.
- **No structure or content has been touched yet.** This session's predecessor was fit-gap analysis
  only. The mechanism for applying finished content to the live DB (admin UI `PATCH
  /api/admin/lessons/{id}`, per `CLAUDE.md`, vs. some bulk path) has not been decided — don't assume
  it, confirm with the user before writing anything to Azure.

---

## Part A — Enrichments to existing tracks

All five of these are **content-depth additions to existing lessons** — no new lessons or modules,
lesson counts stay exactly as they are today.

### Copilot track (10 lessons, unchanged)

| Existing lesson (id) | Add | Source |
|---|---|---|
| "Copilot across the M365 apps (Word, Outlook, Teams, PowerPoint)" (`a3b1ac30-d7fb-45ac-8016-02343e7d6c89`) | An Excel example (summarize a table/pivot, verify figures before trusting output) — Excel is currently absent from a lesson whose title names every other core M365 app | `ms-learn-m365-copilot-modules.md` → "Summarize sales data using Copilot in Excel" |
| "Copilot's commands and app entry points" (`55604076-1817-4d1b-825d-930be1425302`) | Name and briefly describe the prebuilt M365 Copilot agents (Analyst, Researcher, Prompt Coach, Idea Coach, Writing Coach) — the lesson currently gestures at "summon a specific agent" via `@` without ever naming one | `ms-learn-m365-copilot-modules.md` → "Explore prebuilt Microsoft 365 Copilot agents" |
| "Getting started with Copilot chat" (`ff83b265-ad48-40f9-a67a-a4a56cb9976b`) | Mention scheduled/automated prompts as a feature | `ms-learn-m365-copilot-modules.md` → "Employ Copilot Chat as your AI assistant" |
| "What Copilot Studio is and when to build an agent" (`1b83573a-557b-4193-8dad-8d3221a93b8b`) + "Building your first Copilot agent" (`92359cd1-7d72-4364-8177-fe81e1a3ac96`) | Clarify two build paths: the lightweight in-chat Agent Builder vs. full Copilot Studio (currently conflated/undifferentiated) | `ms-learn-m365-copilot-modules.md` → "Scale how you work by creating AI agents." **For drafting "Building your first Copilot agent" itself: use "Build your first declarative agent for M365 Copilot using Copilot Studio" (same file) as the source — NOT `ms-learn-copilot-agent-sharepoint-module.md`, which the fit-gap analysis found is the wrong product tier (SharePoint agent tool + Agent Builder, explicitly excludes full Copilot Studio).** |

**Explicitly dropped, do not add:** a Purview/DLP-mechanics addition to "Using Copilot safely, data
boundaries in M365" (`33ba7526-8005-49e1-8844-5e3b8fdce514`) — verified redundant with the General
track's "Data, privacy, confidentiality, and approved tools at work" lesson (shadow AI, approved-tool
vetting, the "would this embarrass us" test are already covered there), and the deeper Purview admin
mechanics (sensitivity labels, eDiscovery, audit logs) are IT-admin-persona content, not this track's
business-user audience.

### Power Automate/Apps track (6 lessons, unchanged)

| Existing lesson (id) | Add | Source |
|---|---|---|
| "Your first build, what's possible without code" (`ddbc4b92-d3ae-4a23-b684-a21c2d672f3b`) | A short mention of **Copilot in Power Apps** (generate/extend an app from a description) | `ms-learn-power-platform-modules.md` — Copilot-in-Power-Platform cluster |
| "Automating a process with Power Automate" (`9639e439-5c76-4ec4-b9f7-29994a2be9d6`) | A short mention of **Copilot in Power Automate** (describe a flow in natural language), plus error-handling (`Configure run after`) alongside the existing escalation/cadence content | Same file — "Best practices for error handling in Power Automate flows" |
| "Combined solution build (app + automation together), guided build" (`64b38ef8-e585-4491-91b7-dbe1c3931175`) | Expand the closing "publish/share/reflect" note to cover sharing flow ownership and managing app versions | Same file — "Share a cloud flow with Power Automate," "Manage apps in Power Apps" |

**Naming discipline (load-bearing):** name each Power Platform Copilot feature precisely — "Copilot
in Power Apps" / "Copilot in Power Automate" — never a bare "Copilot," which would read as the
separate Microsoft 365 Copilot / Copilot Studio content in the Copilot track. This was a specific
concern raised during the brainstorm; don't lose the distinction when drafting.

**Explicitly recorded as a non-goal — do not treat as a gap to fill:** model-driven Power Apps
(Dataverse-based, typically requires a "system customizer" role — more admin/power-user territory
than this track's deliberately canvas-only, no-code framing). MS Learn has a 5-module cluster on this
that the track doesn't touch; that's a deliberate scope choice, confirmed with the user, not an
oversight.

**Explicitly downgraded, no action needed:** the DLP/governance cluster (already well covered at the
right depth by "Governed, safe use, DLP and connectors") and the MS Learn "booking requests"
capstone template (scenario clash with this track's kit-tracker consolidation across all its build
lessons — importing it would reintroduce a competing narrative the recent consolidation eliminated).

### Claude track (15 lessons, unchanged)

| Existing lesson (id) | Add | Source |
|---|---|---|
| "Working collaboratively with Claude" (`83d693a3-d2d4-483f-a782-f7b047a0c7ac`) | Fold in **Cowork Plugins** + "share what you build with your team" as a short section (confirmed: not worth a standalone lesson) — the word "plugin" currently appears nowhere in the track | `anthropic-skilljar-courses.md` → "Introduction to Claude Cowork," "Sharing and Safety" unit |
| "What Claude Code is, an agentic assistant beyond chat" (`424b5595-e6e8-4a8f-9b76-08b570bea74d`) | A short mention of entry points: **the Desktop app** (no setup) and **VS Code** (with a pointer to its setup guide). No full multi-platform install walkthrough — neither entry point is mentioned anywhere currently | `anthropic-skilljar-courses.md` → Claude Code 101, "Getting Started" unit |
| "Advanced Claude Code patterns" (`cc8aad20-ebb9-4d47-9438-f7dc5a4a9513`) | **Accuracy fix:** the lesson currently calls a custom slash command "the Claude Code counterpart of the Skills you met in chat" — that's describing the wrong feature (Claude Code Skills are a separate SKILL.md-based feature). Fix the description; optionally also name the actual context-management commands (`/compact`, `/clear`, `/context`) since the concept is already taught, just not the command names | `anthropic-skilljar-courses.md` → Claude Code 101 curriculum (Customization unit) |

**Explicitly dropped:** Enterprise search / Research mode as Claude-track content — the user's call:
Copilot is the better tool for this use case. Not a gap to fill here.

### Lovable track (5 lessons, unchanged)

| Existing lesson (id) | Add | Source |
|---|---|---|
| "Deploying, sharing, and connecting your app to data" (`101cb359-cb59-444d-af48-cfaabbfe3917`) | Resolve the auth question the lesson already raises ("no sign-in wall unless you build one") with a short concrete section — e.g. asking Lovable to add email/Google sign-in and gate a route | `lovable-academy.md` — Go Deeper "Add Authentication" + Supabase auth video pointer |
| "Iterating on your app" (`a3dd6c59-26ed-4d2a-a95a-95e3d30caac2`) | Name Lovable's actual product modes (Plan mode / Agent mode / Visual Edits); add "remix/clone when a build gets tangled" next to the existing revert guidance | `lovable-academy.md` — Learn to Prompt #4, docs guide "Remix when needed" |

No non-goals recorded for this track beyond what's already out of scope (payments/Stripe, GitHub
sync, custom domains, Knowledge Files — reasonable omissions for this audience, not flagged as gaps).

### Confluence track (2 lessons/2 modules → 4 lessons/3 modules) — the one structural change in Part A

| Item | Detail | Source |
|---|---|---|
| Edit "Using AI features in Confluence (search, summarise, draft), with a safe-use callout" (`14164161-e42b-4007-b1cc-0e7e832fa814`) | Add **content enhancement** (tone/grammar/translate *existing* text) — currently only search/summarize/draft-*new* are covered | `atlassian-university-rovo.md` — high-confidence section sourced from Atlassian's own Confluence-AI marketing page |
| **NEW lesson** in module "Confluence AI – Use it well" (`bfa0b638-6554-413b-997f-0d96b978dbd0`) | *"Rovo Chat and Agents: beyond single actions"* — the ongoing-conversation chat surface (entry points, side-panel/full-screen modes) and the two named prebuilt agents (Meeting Insights Reporter, Brainstorm Facilitator) | Same file |
| **NEW module** "Confluence AI build" + **NEW capstone lesson** | Guided build using Rovo Studio (custom agent/automation builder) + a named prebuilt agent — brings this track in line with every other tool track's guided-build capstone. Note: Rovo Studio's source material is currently thin (one descriptive sentence) — this lesson will need either a live product walkthrough or accept a lower-confidence draft; flag this to the user before finalizing if source material still isn't sufficient | Same file — treat as a genuine content-generation challenge, not a simple reuse |

**Explicitly dropped:** the TCREI prompt framework (Task/Context/References/Evaluate/Iterate) —
verified redundant with the General track's own prompting content (its own four-lever framework in
"How to write a good prompt," plus dedicated lessons on context and iteration). Do not introduce a
second, competing prompting framework in one tool track.

**Separate, unrelated, low-priority:** four module titles across Copilot and Confluence
("Copilot chat – Get started"/"Use it well", "Confluence AI – Get started"/"Use it well") contain a
literal U+FFFD replacement character in the stored title text where an en dash should be — a small
data bug, worth a one-line fix whenever someone's next in the DB for something else, not part of this
enrichment work.

---

## Part B — New track: "For Developers"

### Why, and for whom

Confirmed with the user: this is a **standalone 7th tool track** (not a build-out of the Copilot
track's existing empty "Github copilot" module), aimed at technically knowledgeable learners —
engineers, not the business-user audience every other track targets. Two things independently point
at this being overdue rather than speculative:

1. The Claude track's own lesson "What Claude Code is, an agentic assistant beyond chat" already
   says *"if shipping an application is your goal, **the developer track is where that lives**"* —
   a dangling reference to a track that doesn't exist yet.
2. `docs/external-sources/external-source-inventory.md` already earmarked the Anthropic
   developer/API courses (Platform 101, Claude API, MCP intro/advanced, Bedrock, Vertex AI) as
   *"not relevant to management-first tracks, only to **Track 7**"* when they were originally
   scraped — this track is that Track 7.

### Cleanup that falls out of this

Once this track exists, delete the empty, orphaned **"Github copilot"** module
(`b5693f1f-8170-482c-98fd-221f023f8e9f`, 0 lessons) currently sitting dead inside the Copilot track
(`ba2023f5-a75d-408c-a6a6-d1e841fc7d65`) — otherwise there would be two GitHub-Copilot homes, one
real and one empty.

### Module/lesson breakdown

Each lesson is tiered **Core** (the essential arc — build this first), **Recommended** (adds real
value, include unless trimming for time), or **Stretch** (most advanced/niche — cut first if the
track needs to shrink). As drafted this is **21 lessons**, larger than any existing tool track (max
is Claude's 15) — see the sizing note at the end of this section before committing to the full set.

#### Module 1 — Get started with GitHub Copilot

| Lesson | Tier | Content points | Source |
|---|---|---|---|
| What GitHub Copilot is, and how it fits alongside Claude Code and M365 Copilot in this hub | Core | Position it clearly against the other two "Copilot"/agentic-coding surfaces already in the hub (M365 Copilot lives in the Copilot track; Claude Code lives in Module 3 of this track) — the hub's own "where this fits" opening-lesson pattern, applied here | `ms-learn-github-vscode-modules.md` → "Introduction to GitHub Copilot" |
| Copilot across your workflow: IDE, Chat, GitHub.com, and CLI | Core | Code completion, Copilot Chat, GitHub.com PR/issue assistance, CLI | Same file → "Get started with GitHub Copilot," "GitHub Copilot Across Environments" |
| Prompting Copilot well | Recommended | Copilot-*specific* mechanics only (comment-driven prompting, chat participants/slash commands/variables) — **check for overlap with the General track's prompting lessons first**, same discipline as the Confluence TCREI decision; don't re-teach prompt basics from scratch | Same file → "Introduction to prompt engineering with GitHub Copilot" |
| Copilot Spaces: giving Copilot durable context | Recommended | Creating a Space, sharing/governance, do's and don'ts | Same file → "Introduction to Copilot Spaces" |

#### Module 2 — Agentic engineering practices

*The "agentic DevOps" cluster the original scrape flagged as having no counterpart anywhere in the hub.*

| Lesson | Tier | Content points | Source |
|---|---|---|---|
| From assistant to agent: the plan → act → evaluate loop | Core | Agents vs. assistants, GitHub as system of record/control plane, the contributor model for evaluating agent-generated work | `ms-learn-github-vscode-modules.md` → "Foundations of Agentic AI in GitHub" |
| Governance for agentic engineering | Core | Risk-based autonomy boundaries, GitHub-native controls (CODEOWNERS, rulesets, environments), human-in-the-loop for high-risk actions, observability/audit | Same file → "Governance, guardrails, and operations" + PR-governance parts of "Designing Agent Architecture and SDLC Integration" |
| Spec-driven development | Recommended | The constitution/spec/plan/tasks workflow via GitHub Spec Kit, intent-first philosophy | Same file → **use the beginner/greenfield module** "Get started with spec-driven development and GitHub Spec Kit," not the advanced enterprise/brownfield one — better fit for this audience |
| Vibe coding, the deeper version | Recommended | What vibe coding is, effective prompts, generating requirements/wireframes. **Must explicitly cross-reference the Lovable track's existing "Vibecoding, build a real app by describing it" lesson** — the hub already uses this exact term for a lighter, no-code audience; this lesson needs to acknowledge that continuity rather than silently redefine the term | Same file → "Introduction to vibe coding" |
| Multi-agent workflows and orchestration | Stretch | The conductor pattern, coordinating agents via GitHub Actions events, isolation and conflict resolution — most advanced lesson in the track | Same file → "Multi-Agent Systems and Orchestration," "Transition from traditional ops to agentic DevOps workflows" |

#### Module 3 — Claude Code, in depth

*The granular content deliberately excluded from the Claude track's light Claude Code module.*

| Lesson | Tier | Content points | Source |
|---|---|---|---|
| Installing and running Claude Code | Core | Terminal, VS Code, JetBrains, Desktop app, web — picking an entry point | `anthropic-skilljar-courses.md` → Claude Code 101, "Getting Started" |
| The agentic loop, in practice | Core | Deeper version of Explore → Plan → Code → Commit — **cross-reference the Claude track's light version rather than re-teach it from scratch** | Claude Code 101 + Claude Code in Action, "Getting hands on" |
| Context management and CLAUDE.md | Core | `/compact`, `/clear`, `/context`; writing a real CLAUDE.md for persistent project memory | Claude Code 101 "Customization" + Claude Code in Action "Controlling context" |
| Skills and subagents for engineering work | Recommended | SKILL.md authoring (frontmatter, progressive disclosure, allowed-tools), Skills vs. CLAUDE.md/hooks/subagents, creating custom subagents via `/agents`, design patterns (structured output, obstacle reporting, limiting tool access). **This is also where the Claude track's Skills-vs-slash-commands mislabeling (Part A) should get a proper, accurate treatment once this lesson exists** | "Introduction to agent skills," "Introduction to subagents" |
| MCP and hooks in Claude Code | Core | Connecting external tools/services via MCP (e.g. browser automation), GitHub integration, custom commands, hooks (defining, implementing, gotchas, useful hooks) | Claude Code in Action, "Advanced Topics" + "Hooks and the SDK" |
| Code review and the Claude Code SDK | Stretch | Automated GitHub code review setup; SDK mentioned as a brief "go further" pointer, not full depth | Claude Code 101 "Code review" + Claude Code in Action "The Claude Code SDK" |

#### Module 4 — Building on Claude (API + MCP)

| Lesson | Tier | Content points | Source |
|---|---|---|---|
| Calling Claude directly: the API fundamentals | Core | API keys/auth, single/multi-turn requests, system prompts, choosing a model (Opus/Sonnet/Haiku) by cost-latency tradeoff, streaming, structured output | Claude Platform 101 "Platform Fundamentals" + Building with the Claude API "Accessing Claude with the API" |
| Prompt engineering and evaluation for production | Recommended | XML structuring, example-based prompting, building an eval harness (test datasets, model-based/code-based grading). **Same overlap check as elsewhere** — focus on what's genuinely production/API-specific (evals), not prompt basics already covered in the General track | Building with the Claude API "Prompt Evaluation" + "Prompt Engineering Techniques" |
| Tool use and agent loops, built by hand | Core | Defining tool schemas, message blocks/tool results, building an agent loop manually, extended thinking | Claude Platform 101 "Teaching/Extending Your Agent" + Building with the Claude API "Tool Use with Claude," "Agents and Workflows" |
| Building MCP servers and clients | Core | The three primitives (tools/resources/prompts), Python SDK with decorators, the Server Inspector, defining a client | "Introduction to Model Context Protocol." Nod to "Model Context Protocol: Advanced Topics" (sampling, transports, production scaling) as a further-reading pointer, not full lesson depth — that course is quite deep |
| Managed agents and deployment options | Recommended | What managed agents are, event streaming, **plus the Bedrock/Vertex AI awareness paragraph** (per the resolved decision: same model, different door in via AWS/GCP — worth knowing if a client's cloud infrastructure dictates it; NOT full standalone depth on either) | Claude Platform 101 "Managed Agents" + a short pull from "Claude with Amazon Bedrock" / "Claude with Google Cloud's Vertex AI" |

#### Module 5 — Capstone

| Lesson | Tier | Content points |
|---|---|---|
| Guided build: ship something real with Copilot + Claude Code | Core | Combine Module 1 (GitHub Copilot), Module 2 (agentic engineering practice), Module 3 (Claude Code) — optionally touching Module 4's API/MCP content — on one running technical scenario. Same capstone pattern as every other track: one concrete build, not a survey. |

### Sizing note

Full draft = **21 lessons** across 5 modules (4+5+6+5+1). That's meaningfully larger than any
existing tool track. Suggested trim path if needed:

- **Core spine only: 12 lessons** (drop every Recommended and Stretch lesson).
- **Core + Recommended: 19 lessons** (drop only the 2 Stretch lessons: "Multi-agent workflows and
  orchestration," "Code review and the Claude Code SDK").
- **Everything: 21 lessons.**

Recommendation: build Core + Recommended (19) by default, and treat the 2 Stretch lessons as a
judgment call based on time/appetite rather than dropping or keeping them by default — flag this to
the user rather than deciding unilaterally when the content-generation session actually gets there.

---

## Part C — Non-goals / parked items (recorded so they aren't rediscovered as "new" gaps later)

- **Power Automate/Apps: model-driven Power Apps** — deliberately out of scope, canvas-only track by
  design (confirmed with the user).
- **Claude: Enterprise search / Research mode** — deliberately out of scope; Copilot is the preferred
  tool for this use case (confirmed with the user).
- **Confluence: TCREI prompt framework** — deliberately dropped as redundant with the General track's
  own prompting content (verified, not just assumed).
- **Lovable: "Add AI to your app," payments/Stripe, GitHub sync, custom domains, Knowledge Files** —
  reasonable scope omissions for a non-technical, management-first audience; not flagged as gaps.
- **Mojibake title-character bug** (4 module titles, Copilot + Confluence tracks) — unrelated data
  bug, small fix, not part of this content work.

---

## Part D — Handoff instructions for the content-generation session

1. Read this document and `docs/external-sources/fit-gap-analysis.md` in full before drafting anything.
2. For each item above, read the cited external source section in full — the summaries here are
   pointers for orientation, not text to copy or paraphrase directly.
3. Before drafting any lesson (new or edited), pull 2-3 real existing lessons' full `content_blocks`
   and match their voice, structure, and scenario-first opening style.
4. Validate every new/edited `content_blocks` payload against `frontend/src/types/contentBlocks.ts`.
5. Where this document flags a cross-reference or overlap check, actually open and read the named
   lesson before writing — don't assume the flag is satisfied by intent alone.
6. Do not apply anything to the live database without confirming the write mechanism and getting
   explicit sign-off first — this document is a content/structure plan, not an execution authorization.
