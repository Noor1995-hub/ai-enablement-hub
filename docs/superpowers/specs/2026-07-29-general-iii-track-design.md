# General III — track design (structure and topics)

**Date:** 2026-07-29
**Status:** design approved, content not yet drafted
**Scope:** the module/lesson structure and authoring contract for the General III track.
Lesson prose is deliberately **out of scope** here and comes next, lesson by lesson.

---

## 1. Why this exists

General III is the only `general` (tool-agnostic) track at the `multiplier` level. Today it holds
one module, `Agentic engineering practices`, with 5 lessons that were generated without much
thought during the 2026-07-20 "For Developers" split. The content owner is not attached to them:
they count as inspiration at most.

Two facts make a rebuild cheap:

- All 5 lessons pass the repo's own `validate_content_blocks`, so nothing is broken, but they
  read as pre-house-style content: 15 to 19 blocks each (650 to 930 prose words), all five on an
  identical skeleton, every one with a recap opener, a forward tease and a "What you can now do"
  closer, `card_group` used as the default summary device, and an engineer's framing throughout
  (a `billing-service` repo, CODEOWNERS, PR review as a contributor, GitHub Spec Kit).
- **Zero `lesson_progress` rows.** 29 learners have the track assigned and 40 have lesson-level
  assignments, but nobody has worked through any of it, because `multiplier` is admin-pin only.
  Replacing the content invalidates no learner progress.

## 2. Track identity

**Audience.** Middle and higher management who are genuinely interested in AI and **not afraid to
get technical**. That is deliberately the same persona house_style.md already names when it
contrasts Code with Cowork ("tailored to people who are not afraid to get technical"). It is not
a developer audience, and lessons must not assume one.

**Thesis.** General I and II taught directing AI one conversation at a time; the tool tracks
taught each product. General III is the rung above:

> You have been directing AI one conversation at a time. General III is about building machinery
> that keeps working when you are not watching, and still being able to govern it.

**Role relative to the tool tracks — this is a hard boundary.** General III owns the **concept and
the judgement call**; Claude II and Copilot II own the **product how-to**. Overlapping material is
cross-referenced, never re-taught. This follows the standing rule in `content-review-lens.md` §3:
teach the underlying pattern and point at the tool track for current product status, rather than
embedding a vendor snapshot that ages out.

Only MCP is tool-neutral by name. For the rest, the transferable concept is "a system of record",
"a standard of a given strength", "deterministic automation on an event", "coordinating parallel
work", with GitHub, instruction files, Actions and Claude Code hooks named openly as the worked
instances.

**Hands-on posture.** Default across the whole track: **direct an agent to build it, then verify
and redirect.** No hand-written code anywhere. This matches both the hub's core thesis and the
audience.

## 3. What is already taught (do not re-teach)

Established by reading the live content of `Claude > Claude Cowork`, `Claude > Claude Code`,
`Copilot > Copilot Cowork` and `Claude II > Claude Code, in depth`, plus General I/II. This table
is the single most load-bearing part of this document: it is why the track is four modules and not
six.

**Claude II is not a stable reference.** Its content is scheduled for a rewrite *after* this track
ships. General III is therefore written first and becomes the reference the Claude II rewrite
aligns to, rather than the other way round. Rows below marked *(provisional)* record what exists
today; they are not boundaries General III has to respect, and General III has latitude to define
the concept properly even where Claude II currently touches it. The **stable** overlap base is the
integrator-level tracks (Claude Cowork, Claude Code, Copilot Cowork) plus General I/II — those are
what this track must not re-teach.

| Concept | Already taught in |
|---|---|
| Chat vs agent; delegating a whole task as a handoff | Claude Cowork L1 · Copilot Cowork L1 |
| Same engine, Code has fewer guardrails | Claude Cowork L1 · Claude Code L1 |
| Runs while you step away, 15+ minutes, parallel sessions | Claude Cowork L1 |
| Sub-agents and automatic parallel decomposition | Claude Cowork L1 |
| Autonomy / permission modes: Manual, Auto, Skip; deletion always protected | Claude Cowork L2, incl. an `interactive` sort on choosing a mode |
| What an agent can reach; acting under your own identity only | Claude Cowork L2 · Copilot Cowork L4 |
| Approval checkpoints before outward or irreversible actions | Copilot Cowork L2 + L4 |
| Briefing well (deliverable, inputs, nuance); watch and steer; review before you call it done | Copilot Cowork L2 |
| Standing instructions / CLAUDE.md | Claude Cowork L3 · Claude II L2 *(provisional)* |
| Skills: what they are, the five-point worth-it test, SKILL.md, where they live, versioning, cross-vendor portability | Copilot Cowork L3 (thorough) · Claude Cowork L5 |
| Plugins reach systems; many plugins talk to MCP servers | Copilot Cowork L3 · Claude Cowork L5 |
| Scheduled tasks: work that runs without you starting it | Claude Cowork L5 |
| Cost of doing more (usage rises with autonomy) | Claude Cowork L6 |
| MCP named and defined; connectors | General I "Beyond chat: agents and connectors" |
| Directing vs doing; brief before you build; review, do not redo | General II "From doing to directing" |
| Plan, act, review as a working rhythm | General II "Plan, act, review" |

**Consequence.** An "agent foundations" module and a "context and skills" module were both designed
and then cut, because between them they were almost entirely covered by the rows above. The
genuinely open ground is:

1. **Git and GitHub as a record.** Absent everywhere. The only GitHub content in the hub is
   Copilot II's coding assistant and a passing Claude II note that the web version only sees what
   has been pushed. It is also the enabling concept for controls and for isolation.
2. **MCP past being named.** Nobody teaches what a server exposes, what you grant when you point
   one at a live system, adopt-vs-build, or building one.
3. **"Telling is not preventing."** Claude II L2 states in passing that CLAUDE.md is "only a strong
   default, not an enforced rule" and that an in-session instruction overrides it. That is the seed
   of the entire governance idea and it is never taught as a principle. Hooks exist only as a
   Claude Code how-to.
4. **Deliberate orchestration.** Cowork uses sub-agents automatically; nobody teaches designing it,
   nor the honest counter-case, nor reviewing more output than a person can read.

## 4. Structure — 4 modules, 14 lessons

Sequence is **record → controls → reach → scale**: govern before extending reach, so the "what you
are granting" lesson has something to lean on. Modules chain with `module_prerequisites` edges
1 → 2 → 3 → 4, so the learning-path graph reads as a path. General III has no edges today;
Claude II already chains its modules this way.

Each lesson below names the upstream lesson it **builds on** rather than repeats. Those
cross-references are obligations, not decoration.

### Module 1 — Git and GitHub

| # | Lesson | Intent | Builds on |
|---|---|---|---|
| 1 | Why agent work needs a record | An agent produces work you did not watch. Without a versioned record you cannot see what changed, undo it, or show what happened. The commit as the unit of change, the diff as the thing you review. | Copilot Cowork L2 (you already know to review; this is about having something reviewable) |
| 2 | Branches, pull requests and review | A branch is a safe place for work in progress; a pull request is where a change is proposed and reviewed before it becomes real. For this audience the point is that the PR is the review point, and the natural home for an approval gate. | Cowork's approval checkpoints, now on a shared record |
| 3 | Issues, history and audit | Work intake and traceability. An issue records what was asked and why; history lets you reconstruct what happened when something goes wrong. | Module 1 L1 |

Callout candidates: "you cannot govern what you cannot see" (L1); "the record is what lets you
reconstruct, rather than remember" (L3).

### Module 2 — Standards and controls

The core module of the track, and the one that replaces the cut "context and skills" module. It
teaches the **spectrum** the learner has never seen, and uses the Cowork material rather than
repeating it.

| # | Lesson | Intent | Builds on |
|---|---|---|---|
| 1 | Instruction, skill, control | Three strengths of standard: an instruction is a strong default an in-session instruction can override; a skill is reusable capability the agent chooses to load; a control fires regardless of what anyone said. Match the strength to the stakes. | Claude Cowork L3 (Claude.md) · Copilot Cowork L3 (skills, five-point test) — referenced, not re-taught |
| 2 | What fires when | What a control actually is: something deterministic that runs on an event. Event, check, pass or block. Named instances (Claude Code hooks, required checks, branch rules) without becoming a vendor snapshot. A control that is slow or noisy gets switched off, so design it cheap. | Module 1 · defines the concept in its own right; the Claude Code how-to is Claude II's job once rewritten |
| 3 | Encode a rule you keep repeating | Hands-on: pick a standard you repeat to people or to agents, direct an agent to turn it into an automatic check. | Module 1 (the check needs somewhere to fire) |

L1's callout is the track's most important line: **an instruction is a default, not a control.**
L1 is also the strongest `interactive` sort candidate in the track (sort standards into
instruction / skill / control), and per house style a sort can stand in for the quiz on a decision
lesson.

### Module 3 — MCP

| # | Lesson | Intent | Builds on |
|---|---|---|---|
| 1 | What a server actually exposes | Open the box: tools (actions), resources (data) and prompts. One protocol, so N tools do not each need N integrations. A server gives an agent a new capability, not new knowledge. | General I (names MCP) · Copilot Cowork L3 (plugins use it) |
| 2 | What you're granting | The risk lesson, and the one this audience will actually be asked to approve. Connecting a server grants reach into a live system, under some identity, at some scope. What a sloppy or compromised server could do. | Copilot Cowork L4 ("acts under your identity, nothing more") · Module 2's controls |
| 3 | Adopt, or build | Judgement: an existing server versus your own, and the cost of ownership (who maintains it, what breaks when the underlying system changes). | Copilot Cowork L3's five-point test — referenced as the model, not cloned |
| 4 | Get an agent to build one | Hands-on, the flagship exercise of the track. The learner installs Anthropic's published **`mcp-builder` skill** and directs an agent through it to build a small server against a service they actually use, then reads the evaluations it produces. No hand-written code. | Module 2 (a skill is the thing doing the work here) · Module 3 L1 to L3 |

**Module 3 L4 in detail — the track's flagship exercise.** It uses Anthropic's published
`mcp-builder` skill (`anthropics/skills`, path `skills/mcp-builder`) rather than an invented
walkthrough. Facts verified from its raw `SKILL.md` on 2026-07-29, and to be re-verified before the
lesson ships, since an upstream repo can change:

- The skill contains `SKILL.md`, a `reference/` folder and a `scripts/` folder.
- It defines four phases: deep research and planning, implementation, review and test, then
  **create evaluations**.
- Its stated measure of quality: "The quality of an MCP server is measured by how well it enables
  LLMs to accomplish real-world tasks."
- Phase 4 makes the agent write 10 realistic questions, each required to be "Independent,
  Read-only, Complex, Realistic, Verifiable, Stable".
- TypeScript is the preferred target ("high-quality SDK support and good compatibility in many
  execution environments"); Python via FastMCP is also supported.
- In Claude Code it installs with `/plugin marketplace add anthropics/skills`.
- The repository states its skills are "provided for demonstration and educational purposes only".
  Say so in the lesson: honest and non-hyped is the house voice, and it sets the right expectation
  for a first build.

Why this exercise and not a generic one: **the learner uses a skill (Module 2) to produce an MCP
server (Module 3), and the skill itself forces them to produce evaluations (Module 4).** Three
modules pay each other off in one exercise, with nothing invented. The technical depth sits inside
the skill rather than on the learner, which is what makes it viable for this audience under the
track's no-hand-written-code posture, and it naturally takes the "ask your questions first, then
walk away" shape house_style.md recommends for an autonomous build.

The learner's actual job, which is what the lesson must make clear: choose a service worth reaching,
answer the agent's opening questions well, then read the evaluations to judge whether the thing
works. Choosing a weak target is the main failure mode, so the lesson supplies a small concrete set
of candidate targets rather than leaving it open-ended, per `content-review-lens.md` §2.

### Module 4 — Orchestrating agents

| # | Lesson | Intent | Builds on |
|---|---|---|---|
| 1 | When one agent isn't enough | What makes work splittable (independent pieces, no shared state, no sequential dependency) and the honest counter-case: coordination cost, spend and review burden can exceed the gain. | Claude Cowork L1 — Cowork already does this automatically; the new thing is deciding it deliberately |
| 2 | Conductor and workers | The pattern: one agent plans and splits, several do the work, results are gathered and synthesised. | Module 4 L1 |
| 3 | Keeping them out of each other's way | Isolation: separate branches or folders so parallel agents do not overwrite each other. What a collision looks like, and recovery. | Module 1 L2 (branches) |
| 4 | Reviewing more than you can read | The multiplier verification problem. When agents produce faster than you can read, you stop reading everything and start designing what gets checked automatically, then sampling the rest. Closes the track by tying Module 2's controls to Module 4's scale. | Module 2 · Copilot Cowork L2 |

Module 4 L2 has a real self-referential example available, which house_style.md rates as the
single strongest device: the multi-agent workflow scripts in `backend/scripts/content_qa/` that
swept and rewrote this hub's own lessons. Use it if it can be told at management altitude.

Closing callout candidate: at scale, review is something you design rather than something you do.

## 5. Authoring contract

Every lesson is written to `backend/prompts/house_style.md` as the current authority. Where the
existing Cowork lessons conflict (they close with "What you can now do"), house_style.md wins: it
was last updated 2026-07-28 and post-dates that content.

**Budget and shape**

- 6 to 12 blocks, well under 1000 words. Today's General III lessons run 15 to 19 blocks; that is
  the anti-target.
- Many short H2 sections, roughly one paragraph each. `heading` level 2. Short bare titles, no
  comma elaboration clause.
- No recap openers, no forward teases, no "What you can now do" closer. Where an opener earns its
  place, use a `kicker` line, the pattern Copilot Cowork L2 and L4 already use.
- Exactly one `callout` per lesson, carrying the single most memorable rule, core claim bolded.
- Inline bullets inside a paragraph in preference to `card_group`. Cards only for a few genuinely
  parallel, weighty items.
- `whitespace` size `md` as a separator before a closing quiz.
- **Vary the skeleton across lessons.** The abandoned content's defining flaw was five identical
  shapes, which house_style.md lists as known trap 5.

**Exercises and assessment**

- `try_it_yourself` used liberally, always in the track's posture (direct an agent, then verify).
  `whatToNotice` describes what the tool will do, not how the learner should feel.
- `interactive` sort mode is a legitimate replacement for a quiz on a decision lesson.
- Quiz optional. When present: 3 questions, 3 to 4 options, a teaching explanation on each, and a
  `heading` reading exactly "Check your understanding" immediately before the block.

**Validator-enforced (a lesson breaking one of these does not ship)**

1. No em dash, en dash or ellipsis character in any text field.
2. At most two bold spans per text field (`- **Term.**` bullet lead-ins exempt).
3. "Artefact", never "Artifact".
4. A quiz's correct answer is never the unique longest option.
5. Vary which position is correct across a quiz's questions.
6. A "Check your understanding" heading immediately precedes every quiz block.

British and EU spelling throughout. Do not invent product specifics: exact labels, timings, UI
placement, statistics or capabilities. Prefer vaguer over wrong.

**Cross-references** must name the real upstream lesson and be verified against the live title
before shipping. This is not theoretical: Copilot Cowork L3 currently cites the General I lesson
as "Beyond chat: agents, connectors, and what they can do" when the real title is "Beyond chat:
agents and connectors".

**Diagrams.** Lessons include placeholder `image` blocks where a diagram would genuinely help,
with the alt text carrying the paste-ready diagram-generator prompt, art generated and uploaded
afterwards through the editor. This matches existing General I/II practice and adds to the
placeholder backlog already logged in `docs/content/README.md`.

## 6. Mechanics

- **Content-only.** No migration, no code change, no deploy. `track_type` stays `general`,
  `required_level` stays `multiplier`.
- **The old module.** Harvest `Agentic engineering practices` for any reusable framing, then delete
  it with `DELETE /api/admin/modules/{id}`, which cascades to lessons, prerequisites and
  assignment rows. Delete only once the replacement modules exist, so the track is never empty for
  the 29 assigned learners.
- **Prerequisites.** Add `module_prerequisites` edges 1 → 2 → 3 → 4 after the modules exist.
- **Assignment.** The cascading assignment added 2026-07-23 fires on the assignment *action*, so
  lessons created after a module was assigned do not inherit it. The 29 learners with General III
  assigned need the track re-toggled once the new lessons exist.

## 7. Process and verification

From `content-review-lens.md` §5 and `review-process-technical-notes.md`:

- **Draft, confirm, apply.** Never blind-edit live content. Produce the draft in a plain review
  file, get it confirmed, only then write to the database.
- **Fetch fresh before every single edit**, not just at the start of a session.
- **Never reuse a block id across turns.** They churn on every admin-UI re-save. Match by locator
  text against a fresh fetch.
- **Treat a vanished quiz or card group as a bug report**, not a content decision. Root cause was
  never found in the Copilot round.
- **Run `validate_content_blocks` over every drafted lesson before applying it.** This is a real
  gate, confirmed runnable from the CLI against the live blocks, not an aspiration. It covers all
  six enforced rules including the quiz answer-length and position checks that
  `content-review-lens.md` §4 asks for on any new batch of generated quiz content.
- **Re-check every quiz and exercise against the final text** after any trim, since a cut section
  can silently orphan an assessment item.

## 8. Out of scope, and follow-ups logged

- Lesson prose. Drafted next, module by module, against this structure.
- Real diagram art for the placeholder image blocks.
- **Content bug:** Copilot Cowork L3's broken cross-reference to the General I lesson title
  (see §5).
- **Content bug:** the abandoned General III lesson 1 opens by referencing "Module 1's
  invoice-parser", which has lived in a different track since the 2026-07-20 split. Moot once the
  module is deleted, but the same class of stale cross-track reference may exist elsewhere in the
  split tracks.
- **Claude II rewrite alignment.** Claude II's content is being rewritten after this track. Since
  General III defines instruction / skill / control, the record, MCP and orchestration first, the
  Claude II rewrite should adopt General III's vocabulary and confine itself to the Claude Code
  how-to, rather than re-deriving the concepts. Worth carrying into that piece of work as an input.
- **`mcp-builder` is an upstream dependency.** Its facts (phases, the six evaluation-question
  properties, preferred language, install command) were verified 2026-07-29 and must be re-verified
  immediately before Module 3 L4 ships, and periodically after. Per `content-review-lens.md` §3,
  prefer teaching the shape of the workflow over transcribing details that age out.
- `Claude II > Managed Agents in Claude` is an empty module (0 lessons) at the same level.
  Unrelated to this work, still outstanding.
- No capstone. `For Developers` already holds a Capstone module at `multiplier`; a second one was
  considered and deliberately dropped.
