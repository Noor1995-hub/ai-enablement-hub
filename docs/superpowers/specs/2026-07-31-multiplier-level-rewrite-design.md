# Multiplier level rewrite — General III and Claude II

**Date:** 2026-07-31
**Status:** design approved, content not yet drafted
**Scope:** the module/lesson structure and authoring contract for a full content rewrite of
**General III** and **Claude II**. Lesson prose is deliberately out of scope here and comes
next, module by module.

Supersedes the structure in `2026-07-29-general-iii-track-design.md` for General III. That
document's *authoring* guidance (validator rules, the `mcp-builder` facts, the delete-the-old-module
mechanic) remains valid and is carried forward here.

---

## 1. Why this exists

Both tracks were reviewed lesson by lesson on 2026-07-31, read as a learner who had just
finished General I, General II, Copilot, Claude and Obsidian. The prose is good — in places the
best in the hub. The problems are structural and at track level.

**Measured defects** (live content, 33 lessons):

| Finding | Multiplier | Levels below |
|---|---|---|
| `try_it_yourself` blocks telling the learner to send a prompt that is not supplied | **11 of 21** | 0 of 20 |
| Claude referred to as "he/him/his" | **75 occurrences, 14 lessons** | 2 (incidental) |
| Lessons opening on a plain paragraph (context, not a defect — see §7) | 33 of 33 | 43 of 69 |
| Average words / blocks per lesson | 966 / 15.2 | 890 / 16.3 |
| Image blocks per lesson | 0.4 (13 total) | 1.1 (79 total) |
| Cross-references that do not resolve | 2 | — |

**Structural findings:**

- **Neither track has an orientation lesson.** Nothing states what changes at this level or why
  the modules belong together. Every tool track below opens with "What X is, where it fits and
  when to use it"; General III opens with "What is Git(Hub)".
- **General III's best idea is stated last.** The constraint ladder (request → mode → boundary →
  control) is the conceptual payload of the track and appears only as a `card_group` in the final
  block of the fourth lesson of module 2.
- **`Advanced tips & tricks` mis-signals.** General II already has a `Tips & Tricks` module of
  light portable habits. The multiplier module of the same name is `.gitignore`, `PreToolUse` and
  content exclusion.
- **The Git module argues against itself.** Lesson 2 says "You will not be creating branches by
  hand or typing commit messages into a form on a website"; lesson 3's exercise has the learner
  upload files through GitHub's web UI and type a commit message into a form.
- **MCP is taught backwards.** The module has the learner direct an agent to *build* a server
  without ever covering what a server exposes or what connecting one grants. Upstream, General I
  only names MCP.
- **`Agentic engineering practices` is still live and terminal.** `sort_order = 10` (above all
  four real modules) and the last link in the prerequisite chain, so it is the last thing a
  learner reads. It is developer-register (`billing-service`, `CODEOWNERS`, `WebhookDetail.tsx`),
  40% longer per lesson, uses the retired "What you can now do" closer, contains a stale
  cross-reference to an `invoice-parser` that now lives in Copilot II, and re-teaches
  orchestration and governance less well than the modules that precede it.
- **Claude II changes reader four times** without bridging: practitioner → budget holder →
  technical sponsor → operations owner. The hub below is scrupulously role-agnostic.
- **Claude II's platform module never says "API".** A learner has no searchable term for the
  thing they spent four lessons on.

**Two facts make a rewrite cheap and safe:**

- **Zero `lesson_progress` rows** across General III, Claude II and Copilot II. Nobody has worked
  through any of it, so replacing content invalidates no learner progress.
- **Claude II is already dark.** The track is assigned to 91 learners but only **2** have
  lesson-level rows, because cascading assignment fires on the assignment *action* and lessons
  created afterwards do not inherit it. The re-toggle this rewrite needs is already owed.

## 2. Track identity

**Audience.** A non-coding senior manager who understands that for the more advanced material,
technical topics are unavoidable. They will not write code. They direct an agent, verify what
comes back, and redirect. This is the same persona the hub already names when it contrasts Code
with Cowork.

**General III thesis.**

> You have been directing one conversation at a time and reading every reply. From here the work
> happens while you are elsewhere. This track is everything you put in place before that is safe.

**Level promise.** The `multiplier` tagline in `frontend/src/lib/levels.ts` reads "Close the loop —
Share, measure, multiply". That is **treated as decorative**. The real subject is governing your
own agent work at scale, which is what the content is and what this rewrite commits to. Recorded
here so the gap is a known decision rather than an oversight.

**No capstone.** Explicitly decided against. `For Developers` holds a Capstone module at the same
level; a second one was considered and dropped.

**Division of labour between the two tracks.** General III owns the concept and the judgement
call. Claude II owns the Claude how-to. Overlap is cross-referenced, never re-taught. One
deliberate exception: General III module 6 states the written-criteria idea tool-neutrally so a
Copilot-only learner also gets it, and Claude II's managed-agents module then teaches the Claude
mechanics in depth.

## 3. Constraint: what Copilot II immutably owns

Copilot II cannot be changed except for the forward-reference repairs in §6. It is **two
half-tracks stapled together**, and this rewrite must not collide with either.

| Module | Register | Owns |
|---|---|---|
| `Copilot Studio` (3 lessons) | business, house style | Low-code agent building: agent vs workflow, Agent Builder vs Studio, grounding on SharePoint, publishing, channels, analytics, ownership/cost/compliance |
| `Get started with GitHub Copilot` (4 lessons) | **developer** | `invoice-parser` (FastAPI, Pydantic, `po_number`), IDE ghost text, Copilot Chat, GitHub.com PR review and description drafting, issue triage, `gh copilot explain`/`suggest`, `@workspace`, `/tests`, `#selection`, Copilot Spaces |

**Consequences for this design:**

- **`invoice-parser` belongs to Copilot II.** General III must never reference it. The only thing
  referencing it across a track boundary is `Agentic engineering practices`, which this rewrite
  deletes, so the collision dissolves rather than needing a fix.
- **General III must not adopt developer register.** Copilot II already owns it, immutably. A
  second developer-register treatment at the same level is a collision, not depth.
- **General III's PR material is a different altitude, deliberately.** Copilot II teaches a
  developer how to use Copilot on a pull request. General III teaches a manager why the pull
  request is where approval happens and what to read in a diff. Both may exist; neither should
  claim to be the other's coverage.
- **Copilot II carries broken forward promises** to a "Module 3" and a "Developer track" that no
  longer exist. §6 repairs the sentences; nothing else in Copilot II is touched.

## 4. General III — structure (6 modules, 20 lessons)

Sequence is **record → constraints → reach → scale → judgement**. Constraints come before reach so
that "what you are granting" has something to lean on. Modules chain
`1 → 2 → 3 → 4 → 5 → 6` with `module_prerequisites` edges.

### Module 1 — What changes at this level (1 lesson)

| # | Lesson | Intent |
|---|---|---|
| 1 | Directing work you do not watch | The orientation the track has never had. Names the shift (you stop reading every reply), the arc of the five modules that follow, and the one question the track answers: how much of this can happen without me, and what has to be in place first. |

### Module 2 — Git and GitHub: a record you can review (5 lessons)

Kept and properly explained, at manager register, per explicit direction. Five lessons rather
than the current seven; account setup moves into lesson 1's exercise.

| # | Lesson | Intent |
|---|---|---|
| 1 | What Git and GitHub are, and why agent work needs them | Git is the tool, GitHub is the website, version control is a project you move through rather than overwrite. An agent editing files with no history is overwriting every time. |
| 2 | Repositories, commits and the diff you review | The repository as project-plus-history, local vs remote, private as the default that matters, and the commit as the unit of change whose diff is the thing you actually read. |
| 3 | Branches: letting an agent try something without risk | A branch is a safe place for work in progress; `main` is the version that has to work. A failed attempt costs the time it ran. |
| 4 | Pull requests: where the work gets approved or rejected | The payload of the module. The PR is the approval gate, the `Files changed` tab is what you read rather than the agent's own summary, and four things are worth checking. |
| 5 | An agent working in your repository | The workflow assembled: branch, PR, review, merge or delete. Points at Copilot II for the developer-side how-to without claiming Claude II covers it. |

**Removed from the current module:** the by-hand upload exercise in `Repositories` (contradicts
the module's own thesis), the standalone `Getting set up with GitHub` lesson (folded into
lesson 1), and the standalone `Commits, staging and syncing` lesson (staging folded into
lesson 2, which drops the `push`/`pull` mechanics a manager does not need).

### Module 3 — Four ways to constrain an agent (5 lessons)

The current `Advanced tips & tricks`, renamed for what it teaches, with the ladder stated first
rather than discovered last.

| # | Lesson | Intent |
|---|---|---|
| 1 | Instructions, boundaries and controls: matching strength to stakes | **New.** States the whole ladder up front: a request the agent may ignore, a mode that holds while you are in it, a standing boundary, a control that fires regardless. Match the strength to what being wrong once would cost. Carries the track's most important line: an instruction is a default, not a control. |
| 2 | Asking first: the dry run that works in any tool | One sentence, no setup, works in tools that do not exist yet. What to ask for, and where it earns its keep. |
| 3 | Plan mode: approving the intention before the work | A mode rather than a request. The plan as a mirror of your brief, and the habit of sending the first one back. |
| 4 | Keeping files out of reach | Two different boundaries: what never enters the repository, and what the agent may never open. Adding a file to `.gitignore` does not remove what is already committed. |
| 5 | Hooks: a rule the agent cannot talk its way past | The strongest rung. A hook you have not tried to break is a belief. The narrower a rule is, the longer it survives. |

Lesson 1 is the strongest `interactive` sort candidate in the track (sort standards into
request / mode / boundary / control) and per house style a sort may stand in for the quiz on a
decision lesson.

### Module 4 — MCP: giving an agent reach into your systems (4 lessons)

Restores the two lessons the current track lost, and now sits after constraints.

| # | Lesson | Intent |
|---|---|---|
| 1 | What an MCP server actually exposes | Open the box: tools (actions), resources (data), prompts. One protocol, so N tools do not each need N integrations. A server gives an agent a new capability, not new knowledge. |
| 2 | What you are granting when you connect one | The risk lesson, and the one this audience will be asked to approve. Reach into a live system, under some identity, at some scope. Leans on module 3's controls. |
| 3 | Adopt an existing server, or build your own | Adopt first, because most of the time it exists. Build for what only you have. The cost is ownership, not construction. |
| 4 | Directing an agent to build a server for you | Hands-on. Anthropic's published `mcp-builder` skill, its four phases, and why the evaluations phase is the one that matters. Read the evaluations, not the code. What a server may *do* is its permission list; start read-only. |

`mcp-builder` is an upstream dependency. Its facts (four phases, the six evaluation-question
properties, preferred language, install command, and the "demonstration and educational purposes
only" statement) must be re-verified immediately before lesson 4 ships.

### Module 5 — Splitting work across several agents (4 lessons)

| # | Lesson | Intent |
|---|---|---|
| 1 | What work can genuinely be split | Independence is the test: neither piece needs the other's answer, neither writes where the other writes. Includes the honest counter-case. |
| 2 | The coordinator and the workers | One agent plans and splits, several do the work, results are gathered. The coordinator does not do the work, so it is not where quality comes from. Read the joins first. |
| 3 | Specialists: defining a worker you reuse | A specialist is a job description, not a personality. Its own working memory, a smaller scope, a cheaper model where cheap is enough. The when-to-use-it line is what decides whether it gets picked. |
| 4 | What running several at once actually costs | Money, collisions, and your attention. Parallel work moves the bottleneck onto you. Closes by forcing the learner back onto modules 2 and 3: at this width, controls stop being good practice and become the only way the work stays reviewable. |

### Module 6 — Judging work you did not watch (1 lesson)

| # | Lesson | Intent |
|---|---|---|
| 1 | Writing down what good looks like | Where the track's thesis lands. You cannot read everything, so you write down what the finished thing must look like, as criteria that can each be marked. Vague criteria produce noisy marking. Do not write them from a blank page: find something genuinely good, ask what makes it good, turn that into the list. Tool-neutral, then hands off to Claude II for the mechanics. |

## 5. Claude II — structure (3 modules, 12 lessons)

Claude II needs far less than General III. The module boundaries are right; two need renaming and
the content needs the §7 contract applied.

| # | Module (was) | Module (becomes) | Lessons |
|---|---|---|---|
| 1 | Claude Code in depth | *unchanged* | 4 |
| 2 | The Claude platform | **Commissioning a build on Claude** | 4 |
| 3 | Managed Agents in Claude | **Managed agents: work that runs without you** | 4 |

**Module 1 — Claude Code in depth.** Lessons keep their titles: `Getting into Code`, `Undo, and
where it stops`, `Work that runs somewhere else`, `What it costs`. Two fixes beyond the contract:
the paid-plan requirement is stated in the module's first paragraph rather than mid-lesson (the
integrator Claude track has already had the learner build something in Code), and the
`Getting into Code` exercise gets its missing prompt.

**Module 2 — Commissioning a build on Claude.** Reframed from a platform tour to the decision a
sponsor is actually asked to make, per approval. Lessons: `The product and the platform: what you
take on`, `What you are paying for`, `Choosing a model`, `Keys, data and spend`. The module must
**say "API" explicitly** — currently the word appears nowhere in the track. Framing is the
decision and the questions to ask a build team, not an implementation guide.

**Module 3 — Managed agents: work that runs without you.** Content is the strongest in either
track and stays substantially as written: `What is actually being managed`, `Work that starts
without you`, `Marking work you did not watch`, `Before anyone depends on it`. Its opening
cross-reference to General III module 6 is updated to the new module title.

**Reader continuity.** The track currently swings between four readers with no bridge. Fix is
one sentence at the top of modules 2 and 3 naming who the module is for and what a reader in a
different role should take from it — not an audience-branching aside in every lesson, which the
review lens warns against.

## 6. Copilot II — repairs only

Two sentences in `Get started with GitHub Copilot` lesson 0 reference a structure that no longer
exists. **No teaching content is touched.**

1. "Claude Code … lives later in this same Developer track, in Module 3" → point at **Claude II**,
   which is where Claude Code depth actually lives.
2. "this same Developer track" → the track is named **Copilot II**.
3. "Module 2 moves from assistant to agent, the same shift you'll notice again in Module 3, when
   Claude Code gets a much deeper treatment" → same repair; Copilot II has two modules.

The card in the same lesson describing Claude Code as "Covered later in this same track, Module 3"
gets the same correction.

## 7. Authoring contract

Every lesson is written to `backend/prompts/house_style.md`. Where the older Cowork lessons
conflict (they close with "What you can now do"), house style wins.

**Shape**

- 700 to 800 words, 8 to 12 blocks. The current tracks average 966 words and 15.2 blocks; that is
  the anti-target.
- Many short H2 sections, roughly one paragraph each. Short bare titles, no comma elaboration.
- Exactly **one `callout`** per lesson, carrying the single most memorable rule, core claim bolded.
- **No "What you can now do" closers**, no recap openers, no forward teases.
- A `kicker` opener is **optional** — used where it earns its place, not mandated.
- Inline bullets in preference to `card_group`. Cards only for genuinely parallel, weighty items.
- `whitespace` size `md` before a closing quiz.
- **Vary the skeleton across lessons.** Five identical shapes is a known trap.

**Images**

- **At least one `image` block per lesson**, in both tracks. No exceptions.
- Shipped as placeholder blocks with an **empty `blob_path`** and the paste-ready
  diagram-generator prompt as the alt text; art is generated and uploaded afterwards through the
  editor, which writes into the same block.
- Consequence, accepted: this takes the placeholder backlog from 13 images to ~32 across the two
  tracks, roughly 19 new diagrams to generate. Logged as a follow-up in §10.

**Exercises**

- **Every `try_it_yourself` ships copyable prompt text** in a step labelled `Prompt`. This is the
  single most learner-visible defect in the current content (11 of 21 blocks reference a prompt
  that does not exist) and it is a hard gate, not a preference.
- Exercises stay in the track's posture: direct an agent, then verify and redirect. No
  hand-written code anywhere.
- The exercise scenario must match the lesson's own running example.

**Voice**

- **Claude is "it", never "he"/"him"/"his"** — both tracks, all lessons. 75 occurrences across 14
  lessons to normalise.
- British and EU spelling. Real product UI labels keep their own spelling (e.g. Claude Code's
  `Summarize from here`).
- Do not invent product specifics: exact labels, timings, UI placement, statistics, capabilities.
  Prefer vaguer over wrong.

**Tool pairing**

- The concept must stand complete in the body of the lesson. Product specifics go in **one
  marked, skippable closing section** per lesson titled `How this looks in your tool`, naming
  Claude Code and Copilot.
- Rationale: 8 of 16 current lessons carry `In Claude Code` / `In Copilot` sections, and module 2
  lesson 1 says "both of the tools in this path" — which strands a learner assigned only one
  tool. Confining the specifics also makes them findable when they age.
- Specifics currently scattered through prose that must move into these sections: `Shift+Tab`,
  `/plan`, `PreToolUse`, `preToolUse`, `/fleet`, `.gitignore`, `content exclusion`,
  `Compare and pull request`, `Files changed`.

**Running thread**

- One thread across General III: **a recurring reporting pack assembled from several systems.**
  It survives the whole arc — it needs a reviewable record, it needs constraints, it needs reach
  into systems, it splits into parallel parts, and it eventually wants to run unattended.
- Used at each module's hands-on rather than forced through every lesson.
- **Must not be `invoice-parser`**, which belongs to Copilot II (§3).

**Cross-references**

- Every cross-reference names the real upstream lesson and is **verified against the live title**
  before shipping. Two in the current content do not resolve (named by current lesson title, since
  the module numbering changes in §8):
  - `AI agents in GitHub` claims Claude II "goes into how their own tool does it" for the branch/PR
    workflow. Claude II never mentions `pull request`, `branch` or `merge`.
  - `Running several at once` says "Claude II covers it" for running several separate jobs at once.
    It does not; the integrator Claude Cowork track does.

**Validator-enforced — a lesson breaking one of these does not ship**

1. No em dash, en dash or ellipsis character in any text field.
2. At most two bold spans per text field (`- **Term.**` bullet lead-ins exempt).
3. "Artefact", never "Artifact".
4. A quiz's correct answer is never the unique longest option.
5. Correct position varies across a quiz's questions. The current tracks underuse position 0
   (10 of 92, against 33 of 132 in the levels below) — distribute deliberately.
6. A `Check your understanding` heading immediately precedes every quiz block.
7. No stray double periods (`..`). Fourteen were removed from the integrator tracks on
   2026-07-31; do not reintroduce them.

Run `scratch_review/general_iii/check_draft.py` over every drafted lesson before applying it. It
covers rules 1 to 6 plus schema validation, and reports empty-`blob_path` errors separately as
expected rather than as failures.

## 8. Mechanics

**Content-only. No migration, no code change, no deploy.** `track_type` stays `general` for
General III and `tool` for Claude II; `required_level` stays `multiplier` for both.

**General III module rows.** Four existing rows are reused and renamed; two are created; one is
deleted. `sort_order` is rewritten so the path reads 1 to 6. Note MCP and orchestration **swap
order**.

| Existing module | Action | New title | New `sort_order` |
|---|---|---|---|
| *(none)* | create | What changes at this level | 1 |
| Git and GitHub | rename, rewrite | Git and GitHub: a record you can review | 2 |
| Advanced tips & tricks | rename, rewrite | Four ways to constrain an agent | 3 |
| Building an MCP server | rename, rewrite, +2 lessons | MCP: giving an agent reach into your systems | 4 |
| Agent orchestration | rename, rewrite, +1 lesson | Splitting work across several agents | 5 |
| *(none)* | create | Judging work you did not watch | 6 |
| Agentic engineering practices | **delete** | — | — |

**Deleting the old module.** `DELETE /api/admin/modules/{id}` cascades to lessons,
`module_prerequisites`, `user_modules`, `user_lessons` and `lesson_progress`. Delete **only after**
the replacement modules exist, so the track is never empty for the 91 assigned learners. Nothing
in it needs harvesting: its orchestration and governance material is covered better by the new
modules 3 and 5.

**Prerequisites.** Rewire General III to a straight chain `1 → 2 → 3 → 4 → 5 → 6`. The existing
chain (`Git → Advanced → Orchestration → MCP → Agentic`) is replaced. Claude II already chains
`1 → 2 → 3` and keeps that.

**Module `sort_order` hygiene.** Claude II's third module sits at `sort_order = 30` against 5 and 6
for its siblings; renumber to 7 so the track reads 5, 6, 7. (The integrator Claude track has a
genuine `sort_order` collision at 30 between `Claude Cowork` and `Claude Code`; that is a separate
pre-existing bug, not in scope here.)

**Assignment.** Cascading assignment fires on the assignment *action*, so lessons created after a
module was assigned do not inherit it. After the rewrite, **re-toggle the track assignment for all
91 learners on both tracks.** This is already owed for Claude II independently of this work: 91
learners have the track and only 2 have lesson-level rows.

**Editing discipline**, per `docs/content/review-process-technical-notes.md`:

- Back up the affected lessons to a timestamped file before any write.
- **Fetch fresh before every single edit**, not just at session start.
- **Never reuse a block id across turns** — they churn on every admin-UI re-save. Match by
  locator text against a fresh fetch.
- Assert the `(id, type)` block skeleton before each write.
- Treat a vanished quiz or `card_group` as a bug report, not a content decision. Root cause was
  never found in the Copilot round.
- **Draft, confirm, apply.** Produce the draft in a plain review file, get it confirmed, only then
  write to the database.

## 9. Verification

Content is verified by re-reading and by script, not by assertion.

1. **Per lesson, before applying:** `check_draft.py` passes; word and block count inside budget;
   exactly one callout; at least one image block; every `try_it_yourself` has copyable prompt
   text; no "he/him/his"; no "What you can now do".
2. **Per track, after applying:** re-fetch fresh and re-run the counts from §1 as a regression
   check — expect prompt-less exercises at 0, "he" at 0, images at ≥1 per lesson, cross-references
   resolving.
3. **Structural diff against the backup:** identical block skeletons except where a lesson was
   deliberately rewritten; no quiz or `card_group` lost silently.
4. **Cross-reference sweep:** every quoted lesson title in both tracks resolves to a live lesson
   title, and every "the tool track covers this" claim is confirmed by searching the target
   track's live content.
5. **Read the sequence as one arc** once both tracks are applied, checking each lesson bridges to
   the one before it — the failure mode a lesson-by-lesson review misses.

## 10. Out of scope, and follow-ups logged

- Lesson prose. Drafted next, module by module, against this structure.
- **Art for ~32 placeholder image blocks** across the two tracks (~19 new). The largest single
  follow-up this design creates.
- **`sort_order` collision in the integrator Claude track** between `Claude Cowork` and
  `Claude Code` (both 30). Pre-existing; the prerequisite edge currently rescues ordering.
- **Copilot II's remaining internal inconsistencies** beyond the three sentences in §6 — for
  example its MCP reference to "the open standard you met earlier in this track" when MCP is
  taught in General III. Left alone under the immutability constraint.
- **Claude II vs the integrator Claude track on interface count.** Claude II says the desktop app
  "has three tabs across the top: Chat, Cowork and Code" and never mentions Design; the integrator
  track teaches four interfaces including Design. Confirm which is true of the current product
  before the Claude II rewrite ships.
- **Product and pricing claims needing independent verification** before anyone quotes them:
  `/plan` as a Claude Code prefix; the Copilot content-exclusion gap in Chat Edit and Agent modes;
  "output costs about five times input"; caching "around a tenth"; batch at half; "Fable at
  roughly twice Opus"; "a developer at roughly a hundred and fifty to two hundred and fifty a
  month"; the tenfold spread across the model range.
- **The `multiplier` tagline gap.** "Share, measure, multiply" is not what either track teaches.
  Decided as decorative (§2); revisit if the level is ever renamed or a team-facing track is added.
- **No reachable capstone at multiplier level.** `For Developers` holds one but is not assigned to
  the learners who have these tracks. Out of scope by decision.
