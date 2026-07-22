# Hub Content Review Lens

Distilled from the General I + II review (2026-07). This is the reusable checklist — apply it
to any track (tool tracks included), not just General.
`general-i-ii-style-guide.md` (same folder) is the
specific working doc that resulted from applying this lens to General I/II; this file is the
lens itself.

---

## 1. Tone & voice — recurring AI-authoring tells

Watch for these specific patterns, not just "does this sound bad":

- **Rhetorical fragment sentences** used as a transition or conclusion — short, punchy,
  slightly poetic, and disconnected from the plain statement they're dressing up. ("Chat is
  the doorway, not the whole house." / "Push the assembly down.") Fix: say the same thing
  plainly. If the fragment can be deleted without losing information, it should be.
- **Dramatic/alarmist framing on risk content**, especially in safety-adjacent material — it
  reads as "don't use AI" rather than "here's how to use it well." ("The error you spot is
  cheap" / "hunting for mistakes" / "before you blame your own wording.") Fix: neutral,
  matter-of-fact wording; capability-plus-guardrail, not warning-plus-fear. A safety lesson
  that scares people off the tool has failed at its actual job.
- **Absolutist claims stated as universal fact** where the real picture is "true of the raw
  case, but often mitigated in practice" (see §3 below for the specific factual version of
  this).
- **Casual-verging-on-unprofessional phrasing** in a lesson meant to read as a professional
  resource ("amateur wording," talking *at* the learner rather than explaining *to* them).

## 2. Structural patterns

- **Opening cards/callouts** — not automatically wrong, but check two things separately:
  (a) does the opening actually add something, or could the lesson start with its first real
  section with nothing lost (if the latter, cut it); (b) even when it adds something, is a
  full boxed callout/card the right weight for it, or would a lighter treatment (a kicker line
  under the title) serve better? These are two different questions — don't conflate "keep vs.
  cut" with "how it's presented."
- **Audience-branching asides** ("if you manage people... if you manage no one...") — don't
  name the split explicitly every time it comes up. Write the point once, inclusively, so it
  works for both audiences without the aside. This applies to any explicit branching aside,
  not just this specific one — the general rule is: if two audiences need the same point,
  find the phrasing that serves both rather than writing two clauses.
- **Repetition across lessons** — the same idea (a concept, a caveat, a worked example)
  restated near-verbatim in multiple lessons rather than referenced. For each repeated idea,
  decide which lesson is its canonical "home" (usually the most complete/structured
  treatment) and trim the others to a brief cross-reference. Don't decide this lesson-by-lesson
  in isolation — read the sequence as one continuous arc first, since the right "home" often
  isn't obvious from a single lesson.
- **Module-level bridging** — check whether each lesson in a sequence explicitly connects to
  what came immediately before it (not just "is topically related," but references the
  specific frame/shift the prior lesson established). A module can have three lessons that are
  individually fine and still not "fit together" if one of them launches into a fresh analogy
  with zero connection to what preceded it, while its siblings do bridge. Fix is usually one
  sentence at the top of the disconnected lesson, not a rewrite.
- **Running-example consistency** — if a lesson (or a sequence of lessons) commits to one
  worked example, check it stays the *same* example throughout, including in any interactive
  exercises. Watch specifically for: (a) the example silently shifting mid-lesson (e.g. a
  "plain-language rewrite" example later called "the translation case" — a different thing);
  (b) an interactive/sort exercise using a different, unrelated example than the lesson's own
  narrative; (c) an example that's more complicated than the point it's illustrating —
  simpler is usually better.
- **Worked examples / try-it-yourself exercises** should give the learner something copyable
  (a ready material blurb, a ready prompt) rather than asking them to invent their own from a
  description. Also check the exercise's scenario actually matches the lesson's own running
  example — a generic unrelated scenario in the exercise undercuts a carefully built example
  above it.
- **Section ordering: payoff vs. build-up** — check whether a lesson's actual actionable
  takeaway (the "so what do I do" section) is buried at the end after a long context-setting
  build-up, or whether a reassuring/scoping statement (e.g. "most work is still fine, only X
  is off-limits") comes only after several sections of caution have already been read. Both
  are fixable by moving the section earlier or folding it into the section that sets up the
  need for it, rather than leaving it as a late addendum.
- **Conflated decision layers** — watch for a lesson that mixes two genuinely different kinds
  of question under one heading: e.g. "is this data allowed near AI at all" (a yes/no safety
  gate) versus "given it's allowed, should I delegate this specific task" (a judgment call).
  These deserve separate treatment (the gate checked first, briefly, then the judgment
  questions) rather than being folded into the same list as if they were the same kind of
  question.
- **"What comes next" / "how this fits together" claims** — any content that describes the
  shape of what follows (a set of categories, a module structure, a sequencing promise) should
  be checked against what actually follows. It's easy for this kind of framing to drift out of
  sync with the real curriculum structure over time (e.g. previewing 3 tool categories when
  the actual tracks are organized by product, each mixing all 3 categories internally).

## 3. Factual-accuracy traps specific to AI-education content

- **Model-limitation claims stated as permanent absolutes.** The two confirmed cases this
  round: "the model knows nothing past its training cutoff" (true of the raw model; false or
  incomplete once search/connectors/retrieval are in play) and "AI is bad at arithmetic" (true
  of raw next-token prediction; substantially mitigated when a tool reaches for a code
  interpreter/calculator). The general pattern: **any claim about what a model can't do should
  be checked for whether it's true of the underlying model only, or genuinely true of the
  tools people actually use** — and if the tool-augmented case matters, say so, framed as "the
  risk is knowing whether your tool is grounded/augmented here, not assuming it never is."
- **Point-in-time product/vendor status claims** ("Tool X supports MCP directly, Tool Y still
  routes through its own connector system") age out fast and are hard to keep current in
  evergreen lesson content. Prefer teaching the underlying pattern/recognition skill and
  pointing to the tool-specific track for current status, rather than embedding a competitive
  snapshot that will need re-verifying every few months.
- When resolving a factual question during review, **write out the reasoning and flag it for
  a second pair of eyes** rather than treating your own correction as automatically right —
  the two verified fixes this round
  (`general_i_ii_review/general_tracks_factual_flags.md`) were confirmed by
  Aaron before being applied anywhere.

## 4. Data-driven checks (don't just read — check when you can)

- **Quiz answer-length bias.** Confirmed this round: 87% of 282 quiz questions across all 9
  tracks have the correct answer as the (unique) longest option — a real, systemic authoring
  pattern, not a one-off. This was found by a two-minute script against the JSON, not by
  reading. **Any new batch of generated quiz content should get this same automated check**
  before it ships, rather than relying on a human noticing the pattern lesson-by-lesson.
- More generally: if a suspicion applies "throughout" or "almost every lesson," it's usually
  cheap to actually verify quantitatively against the underlying data rather than trusting the
  qualitative impression — and quantitative confirmation is far more persuasive when deciding
  whether something is worth a systemic fix.

## 5. Process for running a review efficiently

- **Categorize every review note into one of four buckets**, since each needs different
  handling:
  1. *Wording/tone fix* — low risk, just do it directly.
  2. *Structural move* (reorder a section, move content between lessons/modules, cut a whole
     section) — needs the human reviewer's confirmation before drafting, since it changes
     scope, not just phrasing.
  3. *Factual claim* — needs independent verification before it's applied anywhere, flagged
     explicitly as "please verify."
  4. *Cross-lesson dedup* — needs the full sequence read as one arc, not decided lesson by
     lesson in isolation; defer until you've read enough of the sequence to know where an
     idea's canonical home actually is.
- **Draft → confirm → apply, never blind-edit live content.** Produce before/after text in a
  plain review file first (not an Artifact — rendering has been unreliable on this project),
  get it confirmed, only then touch the database. This was true for both the original content
  review and this rewrite pass.
- **Baseline/snapshot data can be stale.** `db/baseline/data/*.json` is a frozen export, not a
  live mirror — fine for drafting against when live DB access isn't available, but always
  re-verify against live content before an actual write, since content edited since the
  snapshot won't be reflected.
- **When a review note is ambiguous** (references "the card" or "this section" without an
  exact quote, or a count that doesn't match the actual content), don't guess and silently
  apply a change — flag it explicitly and ask. Several notes this round turned out to reference
  different content than what a literal reading suggested (a miscounted card, a note meant for
  a different section entirely). For the *reviewer* writing notes: quoting the exact phrase
  you're reacting to makes the note far more actionable than describing its location.
- **A finding phrased as "I wonder if..." or "not sure..." is a discussion prompt, not an
  instruction.** Present it back as an option with reasoning, don't silently resolve it in
  either direction.

## 6. What takes a lesson from "under review" to "ready to ship" (from the Copilot track review, 2026-07-16/17)

These are content-readiness checks specifically, on top of §1–§4 above. Process/tooling
notes from the same review round (fetch-fresh discipline, the admin editor's block-loss bug,
deploy safety) are kept separately in
`review_process_technical_notes.md` — this section stays scoped to the lesson content itself.

- **After any content trim, explicitly re-check every quiz question and interactive exercise
  against what's left.** A cut section can quietly orphan an assessment item that depended on
  it — this isn't hypothetical, it happened for real this round (a quiz question testing a
  section that had just been removed), and was only caught by re-reading the quiz against the
  post-trim content rather than assuming the trim was safe.
- **"You already met this in the general track" (or any cross-track claim) is checkable, not
  assumable.** One lesson asserted a concept ("grounding") had been taught in General I/II; a
  direct search of that track's actual content found only two passing uses of the adjective,
  never the concept as a named idea. Don't trust a cross-track claim's phrasing — check the
  actual target track's content before treating the claim as accurate.
- **When a whole lesson feels weak or redundant, resist "just delete it."** Break it into its
  individual sections first and classify each one: genuinely restates another lesson
  near-verbatim (cut or reduce to a cross-reference) vs. carries the lesson's own actual thesis
  (keep, even if adjacent sections are cuttable) vs. narrow-audience content that's real but
  over-weighted (downgrade to a lighter callout rather than a full section). A lesson can lose
  half its sections and still justify existing, if what's left is genuinely load-bearing —
  including for the sake of interactive exercises built specifically around that lesson's
  unique content, which a wholesale deletion would orphan.
- **External reference material (a slide deck, a training doc) needs active filtering, not
  wholesale import.** Most of what a reviewer supplies is usually scoped to a different
  product/track (this round: a leadership deck's Claude Cowork material and second-brain
  workflow weren't relevant to the Copilot track) or already covered. Pull only the specific,
  non-redundant, in-scope material, and correct anything the source gets wrong against facts
  already verified in the hub, rather than reintroducing a stale claim (this round: the source
  called a now-GA feature a "Frontier preview" — corrected, not reintroduced).
- **A missing feature/capability area entirely is often the highest-value finding** — bigger
  than any wording nit. Comparing lesson content against the reviewer's own product knowledge
  (or a reference source) surfaced an entire capability — Cowork's Skills/Plugins system —
  missing across all three lessons in its module. Worth actively scanning for "does this track
  ever mention X at all," not just reading line-by-line for prose quality.
