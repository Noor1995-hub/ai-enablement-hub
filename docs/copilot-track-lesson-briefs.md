# Copilot Track — Ready-to-Paste NotebookLM Briefs

Each block below is fully self-contained — copy the whole block (including its header line) straight into NotebookLM, no need to combine it with anything else. Each is written in the same style that got Lesson 1.2 to pass on the third try: concrete caps, named failure modes, explicit "stop and delete" instructions where a specific risk was already observed. Each is under 5,000 characters.

Lesson 1.2 is included for completeness (already validated, v3, 2026-07-16) — reuse it as-is.

---

## Lesson 1.1 — Where Copilot fits and when to use it

Report brief: Copilot track, Module 1, Lesson 1.1 — "Where Copilot fits and when to use it"

Band: Explorer (this opens the whole track).

This lesson's one job: establish the "Work IQ" framing — Copilot is grounded in the organisation's Microsoft Graph data (Teams, Outlook, SharePoint, OneDrive — relationships and permissions), not a generic AI chatbot — and give a feel for when to reach for it vs. general AI chat.

Assume the learner already knows (do not re-explain): general AI literacy, prompting, how LLMs work, grounding/RAG in the abstract — the General track already covers all of this. Do not explain vector embeddings, retrieval pipelines, or RAG mechanics — not in this lesson, not anywhere in this track, ever.

Cover only:
1. What "Work IQ" means in plain terms: Copilot's answers are shaped by the organisation's own data and relationships, not just general knowledge.
2. 2-3 concrete "reach for Copilot instead of general AI chat" scenarios (e.g. "summarise what's already in your inbox/calendar" vs. "brainstorm an idea needing no company context").
3. One sentence mapping what's ahead in this track (interface, grounding, delegation, building agents) — no detail, just a map.

Hard boundary — do not describe: the chat interface, mode selector, Library, or settings (owned by 1.2); the `/` `\` command syntax or app entry points (owned by 1.3); grounding mechanics, Notebooks, Researcher/Analyst agents (owned by 2.2); Custom Instructions/Saved Memories (owned by 2.3); Cowork (owned by Module 3); custom agents or Copilot Studio (owned by Module 4). Mentioning any of these existing is fine in one clause; explaining how they work is not.

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology: don't coin names for concepts; describe plainly if unsure of Microsoft's own term.

Unverified/specific claims: omit, or flag explicitly as "unconfirmed, verify before use."

Register: plain, concrete, practical language for a non-technical business reader. No "Senior Enterprise Architect" framing, no consulting-whitepaper voice, no dramatic metaphors.

Length: short — this is the conceptual opener, not an operational how-to. Roughly a quarter the length of an old full module-level report. If you catch yourself explaining how any interface or feature works, stop and delete it — this lesson is the "why," not the "how."

---

## Lesson 1.3 — Copilot's commands and app entry points

Report brief: Copilot track, Module 1, Lesson 1.3 — "Copilot's commands and app entry points"

Band: Explorer.

This lesson's one job: teach the reference syntax for linking specific content into a prompt, and map where Copilot shows up across Microsoft 365.

Assume the learner already knows: 1.1's Work IQ framing (reference in one sentence, max); 1.2's interface orientation — the mode selector, Library, and settings panel already exist for the reader, do not re-describe them.

Cover only:
1. The reference syntax: how `/` and `\` let you link a specific file, person, meeting, or email into a prompt so Copilot reasons over that exact thing instead of guessing. Give 2-3 concrete example prompts using the syntax.
2. A plain list of where Copilot shows up: the standalone web/app experience, and as a panel inside Teams, Outlook, Word, and PowerPoint. One sentence per entry point confirming it's present — not what it does differently in each.

Hard boundary — do not describe: what Copilot actually does once inside each app (that's 2.1's entire job — this lesson only maps that it's present there); grounding depth, Notebooks, Researcher/Analyst agents (2.2 owns — one clause max if mentioned at all); personalisation settings (2.3 owns); Cowork (Module 3 owns — do not mention it, even in passing); custom agents or Copilot Studio (Module 4 owns).

If you find yourself writing more than one sentence about what happens inside a specific app, stop and delete it — that content belongs entirely to Lesson 2.1, not here.

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology: don't coin names unless certain it's Microsoft's own documented term.

Unverified/specific claims (exact menu paths, exact syntax variants): omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No consulting-whitepaper voice, no dramatic metaphors ("gateway," "front door," etc.) — describe things plainly.

Length: short — an orientation lesson about where things are and how to reference content, not a workflow lesson. Roughly a third the length of a full module-level report.

---

## Lesson 2.1 — Copilot across the M365 apps

Report brief: Copilot track, Module 2, Lesson 2.1 — "Copilot across the M365 apps (Word, Outlook, Teams, PowerPoint)"

Band: Practitioner.

This lesson's one job: teach concrete, app-specific workflows inside Word, Outlook, Teams, and PowerPoint.

Assume the learner already knows: 1.3's reference syntax and that Copilot is present in these apps — use the syntax naturally in examples, don't re-teach it. Reference 1.1's Work IQ framing at most once, don't restate it.

Cover only, one short scenario per app:
1. Outlook: a realistic scenario (e.g. summarising a long thread before a call, drafting a reply in a specific tone).
2. Teams: a realistic scenario during or after a meeting (e.g. catching up on a missed discussion, pulling out action items).
3. Word: a realistic scenario drafting or restructuring a document, optionally referencing another file via the 1.3 syntax.
4. PowerPoint: a realistic scenario building or refining a deck from existing material.

One concrete scenario per app plus a short "why this matters" line — not an exhaustive feature list per app.

Hard boundary — do not cover: grounding mechanics, Notebooks, Researcher/Analyst agents in depth (2.2 owns — a scenario may use grounded data, but don't explain the mechanism); Custom Instructions/Saved Memories (2.3 owns); safe-use/data boundaries (2.4 owns — no security/compliance content here); Cowork or any background/asynchronous execution (Module 3 owns — every scenario here is synchronous, the user present and driving).

If you catch yourself describing something happening "in the background" or "while you're away," stop and delete it — that's Cowork's job, not this lesson's.

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology.

Unverified/specific claims: omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No whitepaper voice, no dramatic metaphors.

Length: moderate — four short scenarios, not four deep-dives. Roughly half the length of an old full module-level report, spread evenly; if one app's section dwarfs the other three combined, trim it.

---

## Lesson 2.2 — Grounding Copilot on your organisation's data

Report brief: Copilot track, Module 2, Lesson 2.2 — "Grounding Copilot on your organisation's data"

Band: Practitioner.

This lesson's one job: explain grounding in practical terms, and introduce Notebooks and the prebuilt Researcher/Analyst agents. This is the one lesson in the whole track allowed to explain what Researcher and Analyst actually do — 1.2 and 1.3 both deliberately deferred that here.

Assume the learner already knows: 1.1's Work IQ framing (reference once, don't re-derive); 2.1's app scenarios (don't repeat them).

Cover only:
1. What grounding means for the user, in plain terms: Copilot draws on your specific files/data, not just general knowledge, only within what you're already allowed to see. No RAG/embeddings mechanics.
2. Notebooks: a project-scoped workspace where you gather specific files to create a focused, persistent context for one piece of work — when you'd use one instead of ad-hoc grounding.
3. Researcher agent: what it's for (surfacing/synthesising information across sources), one concrete scenario.
4. Analyst agent: what it's for (reasoning over data you provide, e.g. comparing documents/spreadsheets), one concrete scenario.

Hard boundary — do not cover: the `/` `\` syntax mechanics (1.3 owns, already taught); Custom Instructions/Saved Memories (2.3 owns); safe-use/data-boundary specifics (2.4 owns — a one-clause pointer is fine, a paragraph is not); Cowork (Module 3 owns, don't mention it); building your own custom agent (Module 4 owns — Notebooks/Researcher/Analyst are prebuilt tools, not something the reader builds; don't blur this line).

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology beyond Notebooks/Researcher/Analyst as given.

Unverified/specific claims: omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No whitepaper voice, no dramatic metaphors.

Length: moderate — four sub-topics, each a short paragraph plus example, not an architecture deep-dive. Roughly half the length of an old full module-level report.

---

## Lesson 2.3 — Personalizing Copilot

Report brief: Copilot track, Module 2, Lesson 2.3 — "Personalizing Copilot"

Band: Practitioner.

This lesson's one job: explain Custom Instructions, Saved Memories, and Scheduled Prompts — the exact mechanics that Lesson 1.2 deliberately deferred here.

Assume the learner already knows: 1.2 already established that a settings panel exists — don't re-describe where it lives or how to navigate to it; focus entirely on what's inside and why it matters.

Cover only:
1. Custom Instructions: persistent rules you set once (role/context, tone, format preferences) that apply to every future chat. One worked example.
2. Saved Memories: facts Copilot retains across sessions from past interactions, distinct from instructions you explicitly set. One worked example distinguishing it from Custom Instructions.
3. Scheduled Prompts: running a prompt on a recurring cadence (e.g. a weekly summary) instead of asking manually each time. One worked example.
4. The combined payoff: why setting these up once removes the need to re-explain your preferences in every new chat.

Hard boundary — do not cover: grounding, Notebooks, Researcher/Analyst agents (2.2 owns); app-specific workflows (2.1 owns); safe-use implications beyond one clause ("what Copilot remembers is still governed by your data boundaries, more in 2.4" — one clause, not a paragraph); Cowork (Module 3 owns — Cowork also uses personalisation, but that overlap belongs to Module 3 to address, not here).

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology: no coined labels for these features — describe plainly.

Unverified/specific claims (licensing tiers): omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No whitepaper voice, no dramatic metaphors.

Length: moderate — three features, one example each, plus a short closing point. Roughly a third to a half the length of an old full module-level report.

---

## Lesson 2.4 — Using Copilot safely, data boundaries in M365

Report brief: Copilot track, Module 2, Lesson 2.4 — "Using Copilot safely, data boundaries in M365"

Band: Practitioner. This is the track's mandatory safe-use lesson.

This lesson's one job: explain what governs where data goes and what Copilot can and can't do with it.

Assume the learner already knows: everything from 1.1-2.3 — add a risk/governance lens on top, don't re-teach any feature.

Cover only:
1. Permission-aware access: Copilot only ever sees what the user themselves already has permission to see — it cannot surface anything the user couldn't already access directly.
2. Zero-retention in plain terms: organisational data isn't used to train the underlying models — describe as a data-handling policy, not a technical mechanism.
3. The one place in this entire track allowed to state Copilot draws on more than one AI model provider (OpenAI and Anthropic are both used): mention this once, plainly, as a compliance-relevant fact, no version numbers, no claim about which provider handles which task unless flagged "unconfirmed, verify current status." If there's a data-residency/transit nuance (e.g. some reasoning processed outside the EU), state it as flagged, verify-before-use — not settled fact.
4. "You're still accountable": the user is responsible for reviewing Copilot's output before sending/sharing it — fluent isn't the same as accurate.

Hard boundary — do not cover: Cowork's approval-checkpoint/ask-before-acting model in depth (Module 3, specifically 3.3, owns agentic-specific safety — one clause only: "agentic delegation in Cowork has its own additional safeguards, covered in Module 3"); custom agent/Studio governance (4.1/4.2 own that); any feature mechanics from 1.2-2.3.

Hard rule — no model names beyond the one allowed mention in point 3: never write "GPT" or any version number anywhere, even there.

No invented terminology.

Unverified/specific claims: flag explicitly as above, not settled fact.

Register: plain, concrete, practical, non-technical reader, matter-of-fact not alarmist. No whitepaper voice, no dramatic metaphors, no fear-mongering.

Length: moderate — four points, each a short paragraph. Roughly a third to a half the length of an old full module-level report.

---

## Lesson 3.1 — What Copilot Cowork is and when to use it

Report brief: Copilot track, Module 3, Lesson 3.1 — "What Copilot Cowork is and when to use it"

Band: Practitioner/Integrator.

This lesson's one job: establish the difference between chatting with Copilot (synchronous, you present and driving) and delegating to Cowork (asynchronous, it works while you don't).

Assume the learner already knows: full fluency with Modules 1-2 (chat, grounding, personalisation, safe use) — do not re-explain any of it, this lesson is entirely about the new delegation model.

Cover only:
1. The core distinction in plain terms: chat is a conversation you're present for; Cowork is a task you hand off and check back on later.
2. 2-3 concrete "reach for Cowork when..." signals: the task has multiple steps, produces a real file/output rather than just an answer, or spans more than one tool.
3. One short example contrasting how the same request would play out in chat vs. in Cowork.

Hard boundary — do not cover: how to write a good delegation brief or the plan-execute-review lifecycle in detail (3.2 owns — you may say "you'll learn to brief it well next," nothing more); the specific data/security boundaries or approval-checkpoint mechanics (3.3 owns); anything from Modules 1-2 in depth.

If you find yourself explaining how to structure a delegation or what Cowork does step-by-step during execution, stop and delete it — that is Lesson 3.2's job entirely.

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology beyond "Cowork" itself as given.

Unverified/specific claims: omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No whitepaper voice, no dramatic metaphors.

Length: short — a concept lesson, not a how-to. Roughly a third the length of a full module-level report.

---

## Lesson 3.2 — Working with Copilot Cowork

Report brief: Copilot track, Module 3, Lesson 3.2 — "Working with Copilot Cowork"

Band: Practitioner/Integrator.

This lesson's one job: teach how to delegate to Cowork well and stay in control of the outcome.

Assume the learner already knows: 3.1 already established what Cowork is and when to reach for it — don't re-explain the chat-vs-Cowork distinction.

Cover only:
1. What makes a good delegation brief: the deliverable (what you want produced), the inputs (what it should use/reference), and any nuance/constraints (audience, tone, format) — one concrete worked example brief.
2. Monitoring and steering: you can check progress and redirect the task partway through, not only accept/reject the finished output.
3. Approval checkpoints as a working mechanic: Cowork pauses at certain points and waits for your explicit go-ahead before finishing sensitive actions — describe this as day-to-day behaviour, not security policy.

Hard boundary — do not cover: the underlying security/governance reasoning for why approval checkpoints exist, what specific actions always require one, or data-reach/permission boundaries (3.3 owns all of that); anything from Modules 1-2.

If you catch yourself explaining *why* an approval checkpoint exists from a security/compliance angle, stop — that belongs to 3.3. This lesson only covers briefing, steering, and checkpoints as user experience.

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology.

Unverified/specific claims: omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No whitepaper voice, no dramatic metaphors.

Length: moderate — three points, one worked example. Roughly a third to a half the length of a full module-level report.

---

## Lesson 3.3 — Connecting Cowork to your tools and data

Report brief: Copilot track, Module 3, Lesson 3.3 — "Connecting Cowork to your tools and data"

Band: Practitioner/Integrator.

This lesson's one job: explain what Cowork can reach, and the safety/governance boundaries specific to agentic, background execution.

Assume the learner already knows: 2.4's general safe-use framing (permission-aware access, zero-retention) and 3.1/3.2's delegation model — build on both, don't re-explain either.

Cover only:
1. Reach: Cowork acts under the user's own identity and existing permissions — it can touch what the user could already touch, never more, regardless of what it's asked to do.
2. Why approval checkpoints exist: the governance reasoning behind pausing before sensitive/irreversible actions (e.g. sending something externally, deleting a file) — this lesson owns the "why," 3.2 only covered what it feels like.
3. One firm rule stated plainly: certain destructive actions (e.g. permanently deleting a file) always require explicit approval, no exceptions, regardless of user settings.

Hard boundary — do not cover: how to write a delegation brief or day-to-day steering mechanics (3.2 owns, already taught); the general M365 safe-use points already in 2.4 — reference in one sentence, don't restate; custom agent governance (Module 4 owns a separate governance story for building agents, not delegating to Cowork).

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology.

Unverified/specific claims (exact policy names, exact rules): omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader, matter-of-fact not alarmist. No whitepaper voice, no dramatic metaphors.

Length: moderate — three points. Roughly a third to a half the length of a full module-level report.

---

## Lesson 4.1 — No-code custom agents

Report brief: Copilot track, Module 4, Lesson 4.1 — "No-code custom agents"

Band: Practitioner/Integrator.

This lesson's one job: teach how a business user builds a scoped "subject matter expert" agent from their own files, no-code, and the governance reality around sharing one.

Assume the learner already knows: 2.2's grounding concept (a Notebook/Researcher/Analyst are prebuilt tools; a custom agent is something the reader builds themselves, scoped to their own data) — apply the grounding idea, don't re-derive it.

Cover only:
1. What a custom agent is: a narrowed-down Copilot, scoped to answer only from specific files or a SharePoint folder — good for a recurring, specific need.
2. How you'd set one up, conceptually: point it at specific files/folders, give it a name and short purpose description — describe the idea, not an exact click-by-click sequence.
3. Sharing and governance: sharing an agent with a colleague does not grant them access to anything they couldn't already see — the agent still respects the underlying file permissions of whoever's using it.
4. One or two concrete scenarios (e.g. an HR benefits-question agent grounded only in the employee handbook; a project-specific agent grounded in one project's files).

Hard boundary — do not cover: Copilot Studio, or anything requiring branching logic/external system integration (4.2 owns — if a scenario needs more, say "for more complex needs, see Lesson 4.2," nothing more); Cowork (Module 3 owns, a different concept — a custom agent is a scoped knowledge tool, not a task-delegation agent; don't conflate them).

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology.

Unverified/specific claims (exact setup steps, exact limits): omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No whitepaper voice, no dramatic metaphors.

Length: moderate — four points. Roughly a third to a half the length of a full module-level report.

---

## Lesson 4.2 — What Copilot Studio is and when you'd commission one

Report brief: Copilot track, Module 4, Lesson 4.2 — "What Copilot Studio is and when you'd commission one"

Band: Integrator.

This lesson's one job: awareness and governance only — never maker mechanics.

Assume the learner already knows: 4.1's no-code custom agent concept as the baseline comparison.

Cover only:
1. What Copilot Studio is, in one plain paragraph: a more powerful platform for building agents with more complex logic, typically used by IT or a dedicated builder, not a business user directly.
2. The decision test for when a no-code agent (4.1) isn't enough: the task needs multi-step branching logic, needs to connect to systems outside Microsoft 365 (e.g. a CRM or ERP), or needs centralised governance/auditing across the organisation.
3. The commissioning conversation: as a business sponsor, what to ask before greenlighting a Studio build — who builds/maintains it, what it costs/requires ongoing, what the approval process looks like before wider rollout.

Hard exclusion — do not cover, even briefly: Topics or Triggers authoring; variable/state management; Power Automate flows or Power Fx expressions; Model Context Protocol or data-integration implementation detail; specific Data Loss Prevention policy mechanics. If you find yourself writing an example of any of the above, delete the entire paragraph — this lesson answers "when and why," never "how to build."

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology.

Unverified/specific claims (licensing costs, exact approval workflows): omit or flag "unconfirmed, verify before use."

Register: plain, concrete, business-decision-focused — aimed at a sponsor deciding whether to commission work, not a builder learning to build. No whitepaper voice, no dramatic metaphors.

Length: short to moderate — three points, no technical depth. Roughly a third the length of a full module-level report.

---

## Lesson 5.1 — Build a real Copilot solution, guided build (capstone)

Report brief: Copilot track, Module 5, Lesson 5.1 — "Build a real Copilot solution, guided build"

Band: Integrator (capstone).

This lesson's one job: help the reader apply everything from Modules 1-4 to a real task of their own, choosing the right tool for it.

Assume the learner already knows: everything taught in this track (chat, grounding, personalisation, safe use, Cowork, custom agents, Studio awareness) — do not re-explain any single feature, only help the reader decide which to use and how to scope a real attempt.

Cover only:
1. A structured planning framework for the reader's own real task: the deliverable (what they want produced), the inputs (what data/files it should draw on), and the nuance (audience, tone, constraints) — reuse this exact three-part shape, don't invent a new one.
2. A short decision guide for choosing the right tool: plain chat + grounding for a one-off question or draft; Cowork for a multi-step task producing a real file while away from it; a custom agent for a recurring, narrow need asked repeatedly; Copilot Studio only if it needs the complexity described in 4.2.
3. A closing prompt encouraging the reader to run their build against a real, current task rather than a hypothetical one.

Hard boundary — do not re-explain: any individual feature's mechanics (all of Modules 1-4 already did this — reference by name only, e.g. "using grounding from Module 2," not what grounding is); do not introduce a new maturity/delegation framework — if a maturity framing is useful, point to it as something the reader already has from the General track, don't reproduce or rename it here.

Hard rule — no model names: never write "GPT," any version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology.

Unverified/specific claims: omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader — encouraging and action-oriented, not a lecture. No whitepaper voice, no dramatic metaphors, no closing slogans.

Length: moderate — this is the capstone, so it can synthesise across the track, but should stay focused on the decision framework and the call to action, not a restatement of every earlier lesson. Roughly half the length of a full module-level report.

---

## Lesson 1.2 — Getting started with Copilot chat (already validated, v3)

Report brief: Copilot track, Module 1, Lesson 1.2 — "Getting started with Copilot chat" (v3)

Band: Explorer (first-touch, day-one user)

This lesson's one job: orient the learner to the Copilot chat interface — where things are and what the basic controls do. Nothing more.

Assume the learner already knows (do not re-explain): General AI literacy, prompting, how LLMs work, grounding/RAG in general terms — General track already covers this. Lesson 1.1 already gave the "Work IQ" framing — reference in one sentence at most. No RAG internals anywhere in this track.

Cover only these three things:
1. The chat mode selector — practical difference between fast/default and deeper-reasoning modes, when a business user reaches for each. Behavior only.
2. The Library — where saved/starter prompts and the agent gallery live, why a first-timer looks there before writing a prompt from scratch. Do NOT name or describe what any specific agent (Researcher, Analyst, or otherwise) specialises in — say only "specialised pre-built agents also live here, covered in Lesson 2.2."
3. Settings — exactly ONE sentence, no sub-list, no named sub-features, no examples: state only that a settings panel exists and that it's where personalisation happens, full stop. Do NOT name Custom Instructions, Saved Memories, Scheduled Prompts, Draft Instructions, or any other specific setting.

Hard boundary — anything owned by another lesson or module: name that it exists and which lesson owns it, one clause, nothing more. Includes: Researcher/Analyst agents (2.2), Cowork (Module 3), Custom Instructions/Saved Memories/Scheduled Prompts (2.3), M365 app behaviour (2.1), safe-use/data boundaries (2.4).

Hard rule — no model names: never write "GPT," a version number, "Anthropic," "OpenAI," or any model/vendor name.

No invented terminology: no coined names ("Digital Twin," marketing labels) unless certain it's Microsoft's own term.

Unverified/specific claims: omit or flag "unconfirmed, verify before use."

Register: plain, concrete, practical, non-technical reader. No consulting-whitepaper voice, no dramatic metaphors.

Length: short — an orientation lesson. Roughly a third the length of a full module-level report.
