# General I & II — Editorial Style & Structure Guide (draft v1)

Distilled from the per-lesson comments in `lesson_review_template.md` for General I and
General II. This is the lens to apply during the edit pass, not a copy-edit itself — review
and adjust before we start point 4 (the actual lesson-by-lesson edits).

**This file is specific to General I/II.** For the generalized, reusable checklist to apply
when reviewing any other track (tool tracks included), see `content-review-lens.md` (same
folder) — this file is what you get from applying that lens to General I/II specifically.

## Parking lot (logged, not in scope for this pass)

- **Quiz bug — CONFIRMED, hub-wide:** checked against the baseline snapshot
  (`db/baseline/data/lessons.json`, no live DB needed): of 282 quiz questions across all 9
  tracks, 87% have the correct answer as the (unique) longest option. Per track it ranges
  80%–100% (General II: 12/12 = 100%; General I: 51/57 = 89%). This is a systemic authoring
  pattern, not a General-track-specific issue — fix once, hub-wide (rebalance/shuffle answer
  lengths), not per-lesson. Live-DB re-check still needed before applying any fix (recent
  content edits since the baseline snapshot could differ slightly), but the pattern itself is
  established. Revisit once DB access is back.
- **General II open question ("What to delegate and what to keep"):** the second decision
  question may not be the right criterion — data sensitivity/confidentiality was raised as a
  stronger candidate. This is a content-judgment call, not a wording fix — needs a decision
  before it's touched.

## 1. Voice & tone

- Neutral, professional, matter-of-fact. Cut dramatic/alarmist framing ("that failure sits
  entirely on your side of the screen", "the error you spot is cheap", "hunting for
  mistakes").
- Cut rhetorical "AI-sounding" sentences — short punchy fragments used as transitions or
  conclusions ("Chat is the doorway, not the whole house.", "The move in one line: it just
  moved the constraint..."). Replace with a plain, direct statement of the same point.
- Safety/risk content should inform, not scare. Several lessons currently read as "don't
  trust AI" rather than "here's how to use it well and where the sharp edges are." Reword
  toward capability-plus-guardrail rather than warning-plus-fear — the current wording risks
  undermining the point of the learning path.

## 2. The "if you manage no one..." aside

Don't call out the individual-contributor case as a separate, explicit clause every time.
Fold the point into phrasing that works for both audiences without naming the split —
write it once, inclusively, rather than branching the sentence.

## 3. Repetition across lessons

- Several core ideas (fluency ≠ accuracy / hallucination, review-before-you-trust,
  delegation calibration, the manager/IC split above) are restated near-verbatim across
  consecutive lessons rather than referenced.
- Rule of thumb: each idea gets one full explanation, in whichever lesson is best placed for
  it; everywhere else, reference it briefly ("as covered in [lesson]") instead of re-teaching
  it.
- This needs a pass that reads General I + II as one continuous sequence rather than
  lesson-by-lesson, to decide where each idea's "home" is.

## 4. Opening cards

Not a blanket rule — some opening cards carry a genuinely useful message, others are filler.

- **Useful ones:** don't use a full Card block as the lesson opener — represent it more
  lightly instead (e.g. an italic kicker/subtitle line directly under the lesson title).
  This may need a small frontend/content-block change if nothing lightweight like that
  exists yet — flag as a separate follow-up from the content edit pass itself.
- **Filler ones:** cut entirely.

## 5. Worked examples

- Provide copyable prompt/context blocks for "try it yourself" exercises instead of asking
  learners to write their own from scratch (flagged in G1 "Working iteratively" and G2 "Work
  through a real recurring task").
- Where a lesson needs example tasks to choose from (the G2 apply-it lesson), list a small
  concrete set rather than leaving it fully open-ended.
