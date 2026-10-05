# Claude Track — Lesson Authoring Brief

A complete, reusable brief for writing lessons in the Claude learning track (and similar
tool-track modules) in the house style. It is deliberately long: the abstract rules under-specify
the taste, so this document keeps the **actual before → after edits** that teach it (§8) alongside
the principles. Audience for the lessons is **middle-to-higher management using AI day to day, not
developers or designers**.

Derived from the two chat modules Matthias wrote himself, and from his edits across the Cowork,
Design and Code modules. His live edits are always authoritative — when in doubt, imitate them.

---

## 0. Do this first: read the gold-standard lessons

Rules cannot fully capture voice. **Before writing anything, read the real lessons as exemplars:**

- The two chat modules **"Claude chat · Get started"** and **"Claude chat · Use it well"** — these
  are Matthias's own writing and are the truest reference for the house voice.
- One finished tool module (Cowork, Design or Code) to see the voice applied to a tool.
- Pull them live from the DB (see §11 for how / module IDs in §13). Do not trust any older export;
  content is edited directly in the admin UI.

Imitate those first; use the rest of this brief to stay consistent and avoid known mistakes.

---

## 1. Voice & tone

- **Second person, direct, plain, warm.** Talk *to* the learner. Use author "we" for
  recommendations and for the self-referential examples ("we recommend", "we built this with").
- **Concrete over abstract.** Real scenarios and analogies, never theory for its own sake.
- **Honest and non-hyped.** Name limits and traps. Honest, slightly self-deprecating credibility
  is a feature, not a bug ("Does it look pretty or can it be commercialized? No, of course not.
  What it did do is save us a lot of time.").
- **Reassuring for a nervous, non-technical audience.** Casual, calming openers ("No worries"),
  and **always relate a new tool to one they already know**. Never condescend, and never belittle
  a tool (frame the contained option as *safer / more guarded*, never "hand-holding / on a leash /
  training wheels").
- **Precise, professional vocabulary** ("deliverable", not "thing").
- **Refer to Claude as he/him.** Established convention for this track.
- **Why it matters:** the reader is a sceptical manager who thinks "code / agents / AI tools" are
  not for them. Warmth + realness + honesty is what earns their trust; hype loses it instantly.

## 2. Length & structure

- **Lean. Say it once, plainly, then stop.** Aim well under 1000 words; ~6–12 blocks is normal,
  and shorter is fine. Matthias consistently trims 30–50% off first drafts (one lesson went 16 → 9
  blocks, another 13 → 7).
- **Short, bare titles.** No comma-elaboration clause. He shortened every one:
  "What Cowork is, and how it is different from chat" → **"What Cowork is"**; "Outputs and
  deliverables, from live artifacts to finished files" → **"Live Artefacts"**.
- **Cut scaffolding.** Remove most recap openers ("In the last lesson you saw…"), forward-teases,
  and throat-clearing lead-ins ("Here is the difference that matters in real life."). A "What you
  can now do" closing is optional and often better dropped.
- **Many short H2 sections** (heading level 2 only), roughly one paragraph each.
- **The one exception: add length for a strong, real example.** He grew a Code lesson 7 → 11
  blocks to fit the story of a tool he built. Realness beats brevity — do not over-trim a genuine
  concrete example. See §6 and §8-G.

## 3. Elements

- **heading** — level 2, short noun-phrase label.
- **paragraph** — 2–5 sentences, one idea. **Bold** the key term/concept and punchy facts. One
  emphasis per block: bold a single term or the one punchy claim, not several (bulleted lead-ins like
  `- **Term.**` are the exception). Over-bolding a block leaves nothing standing out (a real
  2026-07-17 over-correction).
- **Inline bullet lists** — newline + `- ` inside a paragraph block; the renderer turns them into a
  real `<ul>`. **Prefer these over card groups** for enumerations (the memory rules, plugin parts,
  scheduled-task caveats were all converted to inline bullets). `1. ` ordered lists and `| a | b |`
  tables also render inside a paragraph block.
- **card_group** — only for a *few* genuinely parallel, weighty items (a comparison, a do/don't).
  Do not default to it; several of ours were deleted or converted to inline bullets.
- **callout** — one crisp idea. **Promote the single most memorable rule into a callout with the
  core claim bolded** (e.g. he pulled "a design system is not reinvented by each person" out of a
  paragraph into its own callout).
- **quiz** — **OPTIONAL** per lesson; skip on light / curiosity / decision lessons (the Design L4
  and the whole Code module have none). When used: 3 questions, 3–4 options, a teaching explanation
  each, and:
  - **the correct answer must never be the longest option** (a real tell; validate it),
  - **vary which position is correct** (do not let it sit on option 2 every time),
  - **distractors must be plausible** — no cartoonish strawmen ("Cowork is being retired").
  - **always put a `heading` "Check your understanding" immediately before the quiz** (Matthias's
    convention, confirmed 2026-07-17; the chat modules already do this).
- **try_it_yourself** — use it actively (see §8-J). Fill `whatToNotice` as **what Claude will DO /
  what to expect in the interaction**, not "notice how you feel". Tie the prompt back to one from
  an earlier module where you can. For an autonomous build, structure it as **"ask questions first,
  then walk away"** and link it to the permission modes / safety.
- **interactive (sort)** — a strong "decide for yourself" device; a sort can *replace* a quiz on a
  decision lesson.
- **whitespace** — `md`, a separator, usually just before a closing quiz.
- **image** — see §5 and §10.

## 4. Hard constraints

- **No em dashes (—), en dashes (–) or ellipsis (…)** anywhere in a text field. Use periods,
  commas, colons, parentheses or "and". His own lessons contain zero of these. **Grep the JSON
  before applying.**
- **British / EU spelling**: colour, organisation, summarise, behaviour — and **"Artefact"** (he
  renamed "Outputs and deliverables…" to "Live **Artefacts**").
- **"interface"**, not "surface", for Chat / Cowork / Code / Design (he changed "one more surface"
  → "one more interface").
- **Factual precision.** Do not invent product specifics (exact labels, timings, UI placement). If
  unsure, flag it to the user rather than assert it. Use exact wording: he changed "no code" →
  "no **visible** code".
- **No platform talk** in lesson copy — never desktop vs web vs mobile. Write as-is, implicitly
  desktop, and never qualify with "on desktop".

## 5. Images: screenshots AND concept diagrams

- Images are **not only screenshots.** A structured concept (a flow, a comparison, a
  part-of-whole, an option set) is usually clearer as a **concept diagram** than as prose — write
  the surrounding paragraph light and let the diagram carry it. There is a house-style diagram
  generator (see §10).
- **No fixed count.** One image per lesson is nice when it adds something; never force it.
- **Tell a story with images where there is a progression** — he added a *second* screenshot and a
  before/after narrative ("the version we first landed on … we kept iterating … the final prototype
  before moving to Code").
- **An image can replace explanation** (he swapped a whole "staying in control" paragraph for a
  screenshot), and **can be a real screenshot used as story evidence** (an internal tool's own
  interface), not only a diagram or product screenshot.
- **Mechanics:** only `blob_path` is persisted; an **empty `blob_path` renders a clean placeholder
  frame showing the alt text**, and the editor's "Choose image…" uploads into that same block, so
  you can ship image blocks pre-coded for the user to fill. Never persist a `url`. Captions can be
  bare ("Claude code visual"); do not over-write them. Width is fine-tuned to taste (he set one to
  80%), so do not assume full width.

## 6. Content principles

- **Lead with real, self-referential examples — this is the single strongest device.** "We built
  X with this tool" beats any invented scenario, and he will add length for it. The
  making-of-this-hub is the best example bank:
  - the **learning-path frontend** was prototyped in **Design** (Design L1, "you are looking at one
    right now");
  - an **image generator** for lesson diagrams was built with **Code** (Code L2, with a screenshot);
  - the **authoring Skill** (this house style, as a Skill) is used to write the lessons;
  - the course was built inside a **Project**.
  A recurring device: a heading like **"An example you'll recognise"** → the real story → an image.
- **On tool tracks with no making-of-this-hub story** (the hub was built with Claude, so the Copilot
  and other tool tracks cannot use it), substitute the next best grounding: tie the hands-on to a
  real task the learner has right now, and call back to a prompt or feature from an earlier lesson in
  that same track (2026-07-17).
- **Make time saved / efficiency concrete, sparingly.** Show the gap (a 20-minute read becomes 1),
  the "no re-explaining", the delegate-and-walk-away. Use it where natural, **not more than once
  per module**, never as a formula in every section. His words for Code's value: *"it allows you to
  build hyper specific tools and software that are only useful for you. But this doesn't matter
  since the time you put into it is earned back."*
- **Relate a new tool to a known one.** Code = "Cowork with fewer guardrails, for people who aren't
  afraid to get technical"; Design "takes Cowork's live artefact idea and makes it the whole point".
- **Position tools neutrally and let people decide** ("the call is yours"), rather than steering
  ("you mostly won't need it"). He explicitly removed the "most of the time Cowork is enough" line.
- **Teach by contrast**, with one clear tool-selection moment per lesson woven into prose (not a
  repeated "When to use it" heading).

## 7. Lesson archetypes

- **Teaching lesson** — concept + a real example + one hands-on; optional 3-question quiz.
- **Orientation / "where it fits"** — the first lesson of a tool track ("What X is, where it fits
  and when to use it"). Longer than usual is fine here: what the tool is → the family of interfaces
  (a card group) → the kind of work it is for → when you do NOT need it → where it sits next to the
  other tools in the path → a "to summarise" decision card group → quiz. Name sibling tools honestly
  and say which are taught later and at which level (2026-07-17, built for the Copilot orientation
  lesson mirroring "What Claude is").
- **Tour / overview** — shorter, card- and image-light; often no quiz.
- **Curiosity / play** — one strong hands-on (and maybe a concept image); no quiz.
- **Decision closer** — a neutral comparison + a sort; ends on "the call is yours".

---

## 8. Worked examples — the actual calibration data (before → after)

These are Matthias's real edits to delivered drafts. They teach the taste better than any rule.
"–" = what was delivered, "+" = what he changed it to. Grouped by the lesson it teaches.

### A. Titles: strip to the bare noun phrase
- – "What Cowork is, and how it is different from chat"  → + "What Cowork is"
- – "File access and permission modes, letting Cowork act safely"  → + "File access and permission modes"
- – "Projects and memory, where Cowork keeps its context"  → + "Projects and memory"
- – "Outputs and deliverables, from live artifacts to finished files"  → + "Live Artefacts"
- – "When to use chat, Cowork or Code"  → + "When to use Chat and when Cowork"

### B. Leanness — cut recaps, teases, throat-clearing
- Deleted the recap opener: "In the last lesson you saw the big shift: in Cowork you hand over a
  whole task instead of steering every step."
- Deleted the throat-clearer: "Here is the difference that matters in real life." (went straight to
  "Cowork tends to hand you a finished deliverable…").
- Trimmed a "What you can now do" close by removing its forward-tease; removed a whole meta "anchor"
  callout ("The whole module hangs on one shift…").
- Whole lessons shrank: Projects/memory 16 → 9 blocks; the outputs lesson 13 → 7 blocks.

### C. Card groups → inline bullets (and delete cards that do not earn their place)
- The "Chat Project vs Cowork Project" card group was deleted; the two memory rules became inline
  bullets in a paragraph.
- The permission-mode explanation and the plugin components ("skills / connectors / sub-agents")
  were reformatted from cards/prose into `- ` bullet lists inside a paragraph.

### D. Vocabulary: precise and professional, and warmer
- – "a finished thing"  → + "a finished deliverable"
- – "Let that go."  → + "No worries"
- – "This last lesson is more a nudge than a task."  → + "This last lesson is more to make you feel
  inspired to play around with Design."

### E. Concrete UI how-to over conceptual prose
- – "You point Claude at a folder and he opens, reads, edits and saves those files directly…"
  → + "In the chatbox you will see a folder icon. Choose the folder in which Cowork has to work and
  where all the relevant material lives."
- Added concrete creation steps + an honest limit: "Claude now asks you in which folder this project
  will live… Unfortunatly right now it is not possible to have Projects that are both accesible by
  Chat and Cowork."
- Added the concrete scheduling flow and the real caveats as bullets: "the computer needs to be
  awake" / "the computer needs to have an internet connection".

### F. Bold the key term, and promote the one rule into a callout
- Bolded concept phrases: "**agentic AI**", "**visual Claude**", "**stored in a folder on your
  computer**", "**15+ minutes**", "**multiple sessions running at the same time**".
- Pulled a key line out of a paragraph into a callout, core claim bolded: "**a design system is not
  reinvented by each person**. It is built once, usually by marketing or brand…"
- Added an opinionated, bolded push where he felt strongly: "**If there is one thing you need to do
  for Cowork it's installing plugins, they really are the superpowers for Cowork**."

### G. Real, self-referential examples (the strongest device — worth extra length)
- **Design L1:** – "A quick example, close to home."  → + "A quick example, that you'll immediately
  recognize." Then added a before/after of the learning-path prototype and a *second* image ("The
  final prototype we made before moving to Code").
- **Code L2:** added a whole new "Example you'll recognize" section (grew the lesson 7 → 11 blocks):
  the story of the image-generator tool they built with Code (the very tool making these diagrams),
  with a screenshot, honest self-deprecation ("Does it look pretty or can it be commercialized? No,
  of course not. What it did do is save us a lot of time. Someone worked on it for half a day
  together with Code… while Code was doing the heavy work that person could work on something
  else."), and the bolded takeaway about hyper-specific tools earning their time back.

### H. Efficiency / time-saving, made tangible
- The "keeps working after you step away" point was made concrete + practical: "It is important
  that you don't turn off your computer and turn 'Keep computer awake' on in the settings," plus a
  callout on running "15+ minutes" and "multiple sessions at the same time".
- The delegate-and-walk-away value is reinforced through the "person did other work while Code did
  the heavy lifting" story (§8-G).

### I. Factual precision and corrections
- – "with no code involved"  → + "with no **visible** code involved."
- Corrected the persistence story: Cowork/Code need the **computer awake and online** (do NOT say
  "close your laptop and it keeps working", even though marketing docs imply it).
- "surface" → "interface"; "Artifact" → "Artefact".

### J. try_it_yourself — shape and the ask-first-then-walk-away pattern
- He adds them liberally, including "create your own X" prompts mid-lesson (a design-system-builder
  prompt was added to a Design lesson).
- Ties them to earlier modules: "Remember this prompt from when we used Claude Chat, try it again in
  cowork to see the difference yourself."
- For an autonomous build, the prompt tells Claude to **ask its questions first** so the learner can
  then walk away — and a callout links it to the Cowork permission modes (Manual / Auto / Skip) and
  safety. (This fixed a self-contradiction where "come back in 15 minutes" clashed with "ask me
  anything first".)

### K. whatToNotice = what Claude will DO, not how you feel
- – "Notice how differently people react to something they can click through, compared with a static
  picture of the same idea."
  → + "Claude will ask clarifying questions to deeply understand your idea. Then he'll start
  building."
- Same shape elsewhere: "Look at how Cowork breaks the task into smaller steps, hands these off to
  subagents that can run in parallel and then comes back to you with a final answer."

### L. Relate a new tool to one they already know
- – "Code is for building actual software."  → + "Code is Cowork with less guardrails and tailored
  to people who aren't afraid to get technical."
- – "Where Claude Code is aimed at developers working on a machine…"  → + "…aimed at people who are
  not afraid to get technical."

### M. Neutral positioning — let people decide
- Removed "most of the time Cowork is all you need"; the Code decision lesson now states the
  difference and ends on "the call is yours" / "Which one you reach for is up to you."
- Dropped Code from the Cowork closing entirely, re-teed as "Cowork's twin, Claude Code" coming next.

### N. Never belittle a tool
- Removed the "short leash / holds your hand / training wheels" metaphors for Cowork; reframed as
  "**Cowork is the safer, more guarded version**" and "**Code is that same agent with fewer
  guardrails**". Don't denigrate the tool the audience will actually use most.

### O. Quiz answer balance
- Every quiz was rebalanced so the **correct answer is never the unique longest option**, and the
  correct position was spread across slots (it had been landing on option 2 almost every time).
  Distractors were made plausible rather than strawmen.

---

## 9. Common pitfalls (mistakes that got corrected — avoid these)

These are real misses from earlier drafts, kept as warnings:

1. **Inventing product specifics.** I claimed on-canvas controls adjust "layout and colour"
   (fabricated), called a prototype "clickable" without knowing (fabricated), and asserted "close
   your laptop and it keeps working" from marketing docs (wrong). **If you did not verify it, do not
   assert it — flag it.**
2. **One idea restated four times.** An early Code module was four lessons all saying "Code = more
   power / builds things that run". It was cut to three. Watch for lessons that overlap; consolidate.
3. **Samey hands-on.** Four try-it-yourselfs that were all "build a small web widget", and one that
   did not demonstrate the point its lesson was making. **Prefer one strong, distinctive hands-on**
   over several similar ones.
4. **Belittling the contained tool** (leash / training wheels for Cowork). See §8-N.
5. **Over-repeating a reassurance** ("you never see the code" appeared ~5 times). Say it once.
6. **Steering instead of informing** ("you mostly won't need it"). State the difference, let them
   decide.
7. **Self-contradicting exercises** ("walk away for 15 minutes" + "answer my questions first"). Make
   the flow coherent (ask first, then walk away).
8. **Correct answer is the longest / always option 2.** Balance and vary.
9. **Templated structure** — the same "concept → honest-limit callout → 'When to use it' heading" in
   every lesson reads as a template. Vary how the tool-selection moment is delivered; weave it in.
10. **Over-processing / over-length on first pass.** Write lean from the start; do not make the user
    trim half of it.
11. **Restyling is not just restructuring.** Bringing an already-enriched lesson into house style
    includes cutting word count, not only rearranging blocks. A restyle that keeps every sentence is
    still bloated (2026-07-17).
12. **A hands-on must extend the lesson, not re-drill it.** Make the lesson's own new concept the
    active thing. A `try_it_yourself` that repeats a point a paragraph and a quiz question already
    made is wasted (2026-07-17: a grounding lesson's hands-on re-did "check the citation"; fixed by
    turning it into a Notebooks exercise).
13. **Do not reword precise product terms while trimming.** Leanness edits must keep the exact
    terminology from the source ("user-level index" got softened to "personal index"). Trim
    sentences, not defined terms (2026-07-17).
14. **Disguised throat-clearing.** The openers "Here is where", "This lesson is about" and "Just as
    valuable is" are the same lead-ins §8-B deletes, only warmer. State the thing (2026-07-17).
15. **Never anthropomorphise a non-Claude tool.** Claude is he/him and can be personified warmly;
    Copilot and the rest are "it". "It is happy to" is twee. Keep the warmth in how you address the
    reader, not in a cutesy tool personality (2026-07-17).
16. **Keep inter-lesson call-backs when trimming.** "You met X in [earlier lesson]" is continuity
    (§8-J), not filler; do not cut it for leanness (2026-07-17).
17. **Layout is not voice.** It is easy to reproduce Claude's heading skeleton and miss the warmth,
    reassurance and directness that make it his. Match the register, not just the structure
    (2026-07-17).

## 10. Concept-diagram house style (delaware brand)

There is a tool that generates branded concept diagrams; use them where a diagram beats prose.
- **Style:** a bold dark-navy **title**; a **central coral node** with the key concept; **connected
  boxes/pills** in the palette (coral, teal, green, orange, periwinkle blue), each with an **icon +
  short label + optional sub-label**; red **arrows** or a hub layout; a **dark-navy rounded takeaway
  pill** with a one-line caption; soft pastel blob shapes in the corners. Uses delaware brand colours
  and icons.
- **Layouts:** linear flow (A → B → C), hub-and-spoke (centre + 3–4 around), two-up comparison,
  three-column cards, centre-with-branches.
- **How to spec one** (write this into the image block's `alt`/`caption` so it can be generated and
  uploaded): title + layout + node labels + takeaway line. Example:
  > title "You say it, Claude builds it"; linear flow of 3 nodes: "Type what you want / plain
  > language, no code" → "Claude Code / same agent, ready to make" → "A working thing / built and
  > run, not a document"; takeaway pill "'Code' means it builds, not that you write it".
- **Good fits:** a flow (describe → build → run), a comparison (Chat vs Cowork; Cowork vs Code), a
  part-of-whole (Plugins = skills + connectors + sub-agents; a Project = files + links +
  instructions + memory), an option set (three ways to shape a design; export targets).

## 11. Mechanics (writing to the DB)

- Content lives in `lessons.content_blocks` (JSONB array). Every block is
  `{ "id": "<uuid>", "type": "<type>", ... }`; array order = on-page order. Fresh uuid per block and
  per nested item.
- **Block schemas** (authoritative source: `frontend/src/types/contentBlocks.ts`):
  - `heading` `{level:1|2|3, text}`
  - `paragraph` `{text}` · `callout` `{text}` · `kicker` `{text}`
  - `card_group` `{cards:[{id,title,body}]}`
  - `quiz` `{questions:[{id,q,options[],correct,explanation}]}` — `correct` is a **0-based index**
  - `question` `{prompt}` · `whitespace` `{size:'sm'|'md'|'lg'}`
  - `image` `{blob_path, alt, caption?, width?}` — width is % of column, 25–100
  - `video` `{source:'embed', url}` or `{source:'blob', blob_path}`
  - `interactive` sort `{mode:'sort', prompt, buckets:[{id,label}], items:[{id,text,bucketId,reason}]}`
  - `interactive` predict `{mode:'predict', prompt, options:[{id,label,reason}], correctOptionId}`
  - `interactive` spot_the_flaw `{mode:'spot_the_flaw', prompt, example, candidates:[{id,text,isFlaw,reason}]}`
  - `try_it_yourself` `{task, material, steps:[{id,label,text}], whatToNotice}`
- **Inline markdown** in text fields: `**bold**`, `[label](url)`; paragraph text also renders `- `
  bullets, `1. ` ordered lists and `| … |` tables.
- **Quiz gates completion** ("Mark as complete" needs all answers correct).
- **Assignment**: `user_lessons` (a row = assigned); learners see only assigned lessons. A lesson
  added to (or moved into) a module is **not** assigned automatically. When it's ready, open the
  module in **Admin → Content** and press **Assign to the N learners who have this module**
  (`POST /api/admin/modules/{id}/assign-new-lessons`; project admins get the same button for their
  own project). Structure changes (rename, reorder, move, delete, prerequisites) are on the same
  page; none needs SQL.
- **Workflow**: draft → **dry-run validate** (grep for em/en dash + ellipsis in the JSON; confirm no
  quiz correct answer is the unique longest; confirm sort `bucketId`s resolve to a bucket; confirm
  schema) → **apply** (UPDATE existing rows by `sort_order`; INSERT new; DELETE a removed lesson,
  which cascades its `user_lessons`) → **verify read-back** (block counts, no stray `url` on images,
  no forbidden punctuation, no duplicate ids).
- **Access**: Azure Postgres via `backend/.env` creds (asyncpg, `ssl="require"` passed as a kwarg,
  NOT in the DSN), or the admin API (`PATCH /api/admin/lessons/{id}`, `POST /api/admin/lessons`).
- **`lessons.updated_at` / `updated_by`** (since B5, 2026-10-05) are the editor's conflict check: a
  script that rewrites `content_blocks` should also set `updated_at = now()`, so an editor open on
  the old copy gets the Reload / Overwrite prompt instead of silently overwriting the script's write.
- **Automate the dry-run + read-back checks** (2026-07-17): grep every text field for em/en dash and
  ellipsis, scan for duplicate block/card/question ids, confirm no quiz `correct` is the
  unique-longest option, confirm the `correct` positions vary within a quiz, confirm a
  "Check your understanding" heading immediately precedes every quiz, and warn on any text field with
  more than two bold spans. Back up each row (title + content_blocks) to a file before the UPDATE,
  then run the same validator on the read-back.
- **Concurrency**: the user edits lessons **live in the admin UI**. Do **not** write while he may be
  editing — concurrent saves clobber each other (a quiz rebalance was once lost this way). Treat his
  live edits as authoritative; after he edits, diff the live DB against what you delivered to
  recalibrate (that diff is how most of §8 was learned). Since B5 the editor itself refuses a
  save from an outdated copy and offers Reload / Overwrite; scripts writing straight to the DB
  bypass that, so this rule still binds them.
- Run one-off scripts from `backend/` with `uv run python <script>` (asyncpg is installed there).

## 12. Product facts worth knowing (verify before reuse; Matthias's version wins)

- **Cowork** is the same agentic engine as **Claude Code** with no terminal; **Code is that same
  agent with fewer guardrails** (Cowork is the safer, more guarded one). Claude Code **lives in the
  desktop app next to Chat and Cowork** and is run in plain language.
- Cowork **permission modes**: Manually approve / Automatically approve / Skip all approvals
  (Manual / Auto / Skip). Auto uses more usage because it safety-checks each action. **Deletion
  always needs explicit approval, in every mode.**
- Cowork **Projects** hold files / links / instructions / memory; **files live in a folder on your
  computer**; memory is per-project; chat memory does not carry into Cowork; a Project cannot be
  shared between Chat and Cowork.
- Cowork **scheduled tasks**: created from the "Scheduled" sidebar → "New task" (there is **no
  `/schedule` command**). **The computer must stay awake and online.** (This contradicts Anthropic's
  "runs in the cloud even when closed" docs — use Matthias's version for our content.)
- Cowork **plugins** bundle skills + connectors + sub-agents ("the superpowers for Cowork").
- **Design** is a research preview; flow is describe → canvas → shape by talking; on-brand output
  needs a real design system; exports to PPTX / PDF / Canva / shareable link; "Edit with Claude"
  edits a highlighted section of a Markdown draft; can also generate clickable prototypes; the app
  packages a prototype into a bundle you can hand to Claude Code.
- **Design's three ways to shape** a result: talk to it, nudge the on-canvas controls, annotate the
  canvas.
- Chat = generative, turn by turn, you steer each step. Cowork = agentic, plans and acts, works on
  its own, keeps running while you step away.

## 13. Claude track module IDs (reference)

Track `85d19d82-6175-4bbb-a763-5a251ef47cca`. Modules:
- Claude chat · Get started — `2a6a37fd-c325-40fc-b13b-301922b40a87` (3 lessons, Matthias-written)
- Claude chat · Use it well — `6702e37f-57f5-4964-a07b-0fd85a702b90` (6 lessons, Matthias-written)
- Claude Cowork — `5f328480-648c-4776-b997-6a5ce0f1e8dd`
- Claude Code — `376c929c-627e-461f-bd8d-6568e80772ff`
- Claude use case build — `fc875da2-3627-4025-b262-3734d4473b1c`
- Claude Design — `41049e4d-e67e-4182-99a0-ab22c8b971bc`

---

*This guide was written for the Claude track but covers the whole hub — the taste transfers to
the other tool tracks (Copilot and the rest) and the general tracks alike; the only
track-specific pieces are Claude's he/him pronoun and the making-of-this-hub example bank. The two
chat modules are the ground truth for voice; §8 is the ground truth for taste; everything else keeps
you consistent and out of the known traps.*
