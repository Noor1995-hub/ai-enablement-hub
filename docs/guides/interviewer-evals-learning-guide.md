# Building Evals for the AI Interviewer: A Learning Guide

Last updated: 28 September 2026 (after the baseline run)

This guide explains how we are building evaluations, or "evals," for the AI interviewer in the AI Enablement Hub. It covers what we did, in what order, and why, so you can explain it to someone else without having built any of it yourself.

## The big picture in one paragraph

The AI interviewer is not ordinary software you can test with a simple pass or fail check. It is built from prompts that call a language model, and the model can answer a little differently every time, drift over time, or fail in ways nobody notices until a client is sitting in front of it. Evals are how we check quality on purpose instead of relying on someone happening to spot a problem. We follow a sequence, and each step exists because the step before it made the next one possible:

1. Understand before measuring: look at how the system actually works and what it actually produced.
2. Define what "good" means, in our own words, before building any checks.
3. Make every run traceable, so a result can always be tied to the exact prompt and model that produced it.
4. Build a fixed test set (done: simulated, reviewed, frozen).
5. Build automatic checks against that test set (built).
6. Check that the checks themselves work (built).
7. Set a baseline and compare every later change against it (baseline saved).

After that comes what we're calling Tranche 3 and Tranche 4, described at the end.

## 0. Understand before measuring

### What we did

Before writing a single test, we mapped how the interviewer actually works. It is not an agent, just plain API calls to one model: the opening question is one call, each answer triggers one more call (the model sees only the last 20 messages), and the final "playbook" (a learner-facing part plus a consultant-only part) is one big structured call. All of the system's behaviour lives in two prompt files, nowhere else.

With that map in hand, we read the only two real finished interviews the system had produced in production. Out of 234 users, 5 had started it, 3 left right after the greeting, and 2 finished. Those 2 playbooks turned up real problems: a comparison to other people ("something a lot of people haven't gotten to yet"), a missing main workstream, a reframe built on a withdrawn hesitation, internal jargon leaking through ("as flagged in your intake"), and a gender guessed from nothing ("himself") in the consultant notes. The transcripts showed double questions, multiple-choice questions where open ones were expected, the AI repeating answers back, a hint at the person's AI level, and a closing line that didn't match the interface. Separately, someone got in without completing the required assessment first.

We also found a research document that recommended "pinning the temperature" as a fix. When we checked the live model, it rejected the temperature parameter outright, so that particular fix had to be replaced with something else.

### Why this comes before the next step

You cannot design a test for a system you have not looked at. Real outputs show real failure modes; a rubric written from imagination alone would have missed the actual problems and invented ones that didn't matter.

### What surprised us / what can go wrong

The gap between documented advice and the real system was the biggest surprise: a fix that looked reasonable on paper didn't work against the actual model. The lesson: verify advice against the actual system before relying on it. It was also sobering that so few finished runs already showed this many problems.

### How to explain it in one or two sentences

Before building any tests, we read what the system actually produced and found real problems in real conversations. That reading shaped everything after.

## 1. Define good

### What we did

We wrote down, in plain language, what "good" means for the learner-facing part of the playbook, as an 8-point rubric: grounded in what the person said, no judging the person, feels like theirs not generic advice, covers their real work, a genuinely startable "start here," honest reframes, safe advice, and the person's own voice. We also decided which half to optimise first (learner-facing, not consultant-only), who has final say (Aaron), and where test data would live (in the repo, invented, anonymised).

### Why this comes before the next step

Before building infrastructure to record and compare results, we needed to agree on what we were trying to improve. Without that, later steps risk measuring the wrong thing, with no way to say what "better" looks like.

### What surprised us / what can go wrong

Several of the eight points are subjective, "their voice" and "safe advice" among them, so naming a decision-maker mattered as much as writing the rubric. Without one owner, disagreements about what counts as good could stall everything downstream.

### How to explain it in one or two sentences

We wrote one page on what a good playbook looks like, and agreed who has the final say, before writing a single test.

## 2. Make runs traceable (Tranche 1, shipped)

### What we did

Every turn and playbook now records which model produced it, which prompt version was used (a fingerprint of the prompt text), and which settings were in effect. We also fixed a batch of cheap, known gaps: rules enforced on the server instead of only in the web page, time limits, no interview text in logs, the assessment required before starting, and no gender guessing. The work was built as small tasks, each done by one AI agent and checked by a separate AI reviewer, then one final review of everything together. The reviews caught four real problems, including one where the plan itself would have written interview content into the logs, exactly what the fixes were meant to prevent.

### Why this comes before the next step

Without traceability, a test result cannot be tied to the version that produced it, making later comparison meaningless. Fixing cheap, known problems first clears out noise later tests would otherwise flag.

### What surprised us / what can go wrong

The plan itself needed reviewing: it had a flaw that would have logged interview content, caught only because a separate reviewer checked it. The lesson: independent review catches what the author, even an AI one, cannot see in its own plan.

### How to explain it in one or two sentences

We made sure every result traces back to exactly which prompt and model produced it, and cleaned up cheap, known problems first, so later testing measures real issues rather than noise.

## 3. The test set (done: simulated, reviewed, frozen)

### What we did

We built the machinery for a one-off simulation: the real interviewer code (the same opening-question call and the same per-turn call production uses) runs against a second model call playing an invented person, turn by turn, until the interviewer offers to build the playbook, a fixed answer limit for the one persona who leaves early is reached, or 20 answers are reached. The result is written as a draft case file plus a plain-language review page with the assessment, the persona, the full transcript and a checklist, so Aaron can approve or send it back before anything is frozen.

We wrote 14 invented people: 6 managers, 4 operational staff, 3 attackers, and 1 who answers partly in Dutch, spread across food production, construction, utilities and services. Each one has the survey answers they would have given plus a hand-written "ground truth" of the systems they name and the main work they describe, which the automatic checks compare the playbook against.

Then we simulated all 14 against the live model. Each interview took about a minute and cost roughly 20 to 30 cents. Every interview ended with the interviewer offering to build, including the person who leaves after four answers. All three attacks happened as planned and the interviewer refused each one. After reconciling the ground truth with what each person actually said (next section), all 14 were approved and frozen in the repo.

### Why this comes before the next step

The checks built in chapter 4 need something fixed to run against, and something has to produce the first draft of that fixed thing before a person can review it.

### What surprised us / what can go wrong

- **The simulated people improvise.** They named systems nobody wrote into their description (a maintenance system called "WorkOrder", a quality system, an HR suite) and skipped some that were written in. Left alone, the "no invented systems" rule would have flagged a playbook for correctly mentioning a system the person really named. The fix was not to change the interviewer but to treat the ground truth as the answer key for one specific conversation: after simulating, we rewrote each case's list of systems, main work and hesitations to match what the person actually said, and the review page now hints at names that look like systems but are missing from the list.
- **The live interviewer answered for the person once.** In one interview, a single interviewer turn contained the person's answer, the interviewer's reply, the person agreeing, and the offer to build: the model wrote both sides of the conversation. That transcript would have been a misleading test, so it was saved as evidence and the case was simulated again. It is also a real product finding: a learner could see the interviewer put words in their mouth.
- **The attacks failed, but the interviewer named them.** In two attack cases the interviewer refused the planted instruction but repeated the marker word back in the chat, once in its very first greeting, telling the person it would skip "that instruction in your notes". Nothing leaked into the playbook, so the check passes, but it is an odd thing for a real learner to read. Grading the conversation itself is a later tranche.
- The main risk from here: a frozen test set goes stale if real usage shifts and nobody revisits it.

### How to explain it in one or two sentences

We simulated 14 invented people through the real interviewer, rewrote each answer key to match what they actually said, and froze the result so every later change is tested against exactly the same conversations.

## 4. The checks (done)

### What we did

Each frozen test interview becomes a playbook three times per run, since the model varies its answers. That is 14 people times 3 repeats, 42 results per run; differences smaller than roughly 15 percentage points could just be chance, a margin we call the noise margin. We built checks that use no AI: free, instant, the same answer every time. Five hard rules must pass on every single result with no exceptions: no judging the person, no internal jargon leaking into their playbook, no invented systems, no guessed gender, and for the three attack cases, no sign the attack got through. Alongside those, structure checks report a pass rate (is there a genuine Quick Win to start with, is the summary the right length, do the next steps and reframes point at real use cases), and grounding checks score how well the playbook stays tied to what the person actually said (their main work covered, their own words reused rather than paraphrased away, no reframe built on a hesitation they later took back). A last group of signals, like leftover formatting and cost, are shown but never pass or fail anything.

### Why this comes before the next step

Before trusting a baseline or a comparison, the checks producing the numbers need to exist and be reviewed. Proving those checks actually work only makes sense once they exist, which is chapter 5.

### What surprised us / what can go wrong

The clearest known limitation, confirmed while writing the checks: word lists are cheap but blunt. They miss a paraphrase ("further along than colleagues" says the same thing as a banned comparison without using any of the banned words), and they can flag an innocent sentence that happens to reuse a flagged word in an unrelated sense ("the supplier was reluctant to confirm the date"). That gap is exactly why a later tranche adds an AI-based grader instead of relying on word lists alone.

### How to explain it in one or two sentences

We built automatic, non-AI checks: cheap rules that catch clear problems and scores that measure how grounded the playbook is, and we run each test case three times because the AI's answers vary from run to run.

## 5. Checking the checks (done)

### What we did

Before trusting any check, we fed it a hand-written playbook that must pass every hard rule and every structure check, a playbook built to contain every failure the checks look for (so every hard rule fails, with the exact evidence text that triggered it), and an empty playbook that must fail the structure checks cleanly, with nothing crashing.

### Why this comes before the next step

A baseline is only useful if the checks feeding it are reliable. A check that always passes, or fails on things that do not matter, is worse than no check at all, because it creates false confidence.

### What surprised us / what can go wrong

Confirming the empty case mattered more than expected: an empty playbook technically satisfies every hard rule (it says nothing, so it judges nobody and invents nothing), while every structure check correctly reports it as broken. That is the right split, not a bug, but it is easy to design a fixture that hides it. The other risk, unchanged from before we built anything: known-bad examples cannot cover every real failure, so a check can look reliable here and still miss a real problem later.

### How to explain it in one or two sentences

Before trusting a check, we tested it against an example we know is good, one built to contain every failure we know about, and an empty one, to make sure it can actually tell the difference and never crashes.

## 6. Baseline and comparing (done: baseline saved)

### What we did

The first full run of all the checks against today's prompt is saved as the baseline. Every later change to the prompt or model is compared against it. The tooling flags differences; a human decides what they mean. Human touchpoints: approving the test interviews, reviewing graded examples ("would you have scored these differently?"), approving the cost of running the evals, and reading the baseline report.

Before the full run we did a pilot: two cases, one playbook each, about 23 cents in total. Aaron read the results and confirmed two scoring decisions: a pronoun guessed from someone's first name is a hard failure (ideally the playbook uses no pronouns at all), and a summary of 184 words fails the 120 to 180 word limit.

Then the full baseline: 14 people, 3 playbooks each, 42 playbooks, about 4 dollars. Reading the failures one by one showed that roughly half the hard-rule failures were false alarms, so three checks were tuned (Aaron's decision): a "system" the person said in their own words (a work phone, paper checklists) no longer counts as invented; the internal word "intake" only counts in phrases like "your intake", because "intake data from the call centre" is plain English; and "other people" and a bare "ahead of" were dropped from the judging list ("numbers land ahead of Friday" is not a comparison). We added a regrade command that re-scores saved playbooks with the tuned checks without calling the model, so the tuning cost nothing.

What the baseline says about today's interviewer, after tuning:
- Only 1 in 3 playbooks passes every hard rule.
- Two in three guess the person's gender from their first name, almost always in the consultant-only part ("she controls what tools Finance adopts", "he had zero ideas of his own"). The only people spared were the one who stated their pronouns and a few who were written about by name.
- Three playbooks still compare the person to others ("a sharper diagnosis than most people arrive with"), the same problem we first saw in production.
- Attacks never reached the playbook, and every structure check passes except summary length, which runs over 180 words about one time in eight.
- About one playbook in five needs a second attempt because the model's first answer does not fit the required format, and one in 42 failed twice, which a real learner would see as an error.

### Why this comes before the next step

A baseline is the reference point that later additions, an AI grader and full conversation simulation, need to mean anything. Without a saved starting point, there is nothing to compare a new version against.

### What surprised us / what can go wrong

- **Reading the failures mattered as much as counting them.** The first headline number (1 in 5 passing) was half false alarms. Checking the evidence text of every failure before trusting the number is the step that made the baseline honest.
- **A check can be wrong in the other direction too.** While tuning the "systems" check, a code review caught that the new rule would let an invented "Excel" pass whenever the person said "she excels", and "SAP" pass on "it saps our time". Loosening a check needs the same scrutiny as writing it.
- **The spending cap counts everything already spent on a run.** Resuming the baseline with a 1 dollar cap stopped at once because 4 dollars were already spent; the cap is a total for the run, not a top-up.
- The tool only flags differences; it does not decide whether one is good or bad. That decision stays with a person at every stage.

### How to explain it in one or two sentences

We ran every test person three times through today's interviewer, read every failure to weed out false alarms, and saved the corrected result as the baseline: today only a third of playbooks pass every hard rule, mainly because the playbook guesses people's gender.

## What comes next

The first use of the baseline is a prompt change, called v1: the playbook uses no pronouns for the person at all and never compares them to other people. It runs through exactly the same 14 frozen interviews, and the comparison page shows, check by check, whether it helped and whether the difference is bigger than chance. The interviewer's own habits seen during simulation (answering for the person once, repeating a refused attack word back in the chat) are prompt candidates too, but grading the conversation itself belongs to Tranche 4.

Word-list checks are cheap but miss paraphrases and can flag innocent text, which is why Tranche 3 plans to add an AI grader (an "AI-as-judge"), validated against human scores first. Tranche 4 plans to simulate whole conversations end to end and add real production numbers, rather than only simulated test cases.

## Lessons so far

- Read every failure before trusting the headline number. Half of the first baseline's hard-rule failures were false alarms.
- A test set built by simulation needs its answer key rewritten after the simulation, because the simulated people improvise.
- Loosening a check needs as much review as writing it: a looser match nearly let invented systems through.
- Verify advice against the actual system before acting on it. A document recommended pinning the temperature; the live model rejects that setting entirely.
- You cannot design a test for a system you haven't looked at. Two real finished interviews turned up more real problems than guessing ever would have.
- Independent review catches what the author, even an AI one, cannot see in its own plan. The final review caught four real issues, including one that would have logged private conversation content.
- Fix cheap, known problems before testing, so later tests measure real, unresolved issues instead of noise.
- A test set has to be frozen. If it can change, you can't tell whether a difference comes from your change or from the test shifting under you.
- Word-list checks are fast and free but miss paraphrased problems and can misfire on innocent text. That gap is why a more expensive AI-based check comes later, not instead.
- Small differences can just be chance. With the model giving slightly different answers each time, a gap smaller than the noise margin isn't evidence of anything.

## Glossary

- **Eval**: a systematic test of how well an AI feature performs, instead of just eyeballing outputs.
- **Test case / test set (corpus)**: one example used to test the system, and the whole collection of examples together.
- **Frozen**: fixed once and never changed again, so later comparisons stay fair.
- **Persona**: an invented person used as a stand-in for a real user.
- **Adversarial case / prompt injection**: a test case built to try to make the AI misbehave, for example with text meant to override its instructions.
- **Grader / check**: something, automated or AI-based, that reads a result and decides whether it passed.
- **Rubric**: a written definition of what a good result looks like, broken into specific points.
- **Hard rule vs pass rate**: a hard rule must pass every time, no exceptions; a pass rate is a percentage across many results, allowing some failures.
- **Baseline**: the saved result of the first full test run, kept as the reference point for every comparison after it.
- **Variant**: a changed version of the prompt or model being compared against the baseline.
- **Noise / noise margin**: how much a result can vary by chance, not because anything real changed.
- **Reps (repeats)**: running the same test case more than once, since the AI doesn't give the same answer twice.
- **Known-good / known-bad ("oracle" / "null")**: example results used to test a check, one that should clearly pass and one that should clearly fail.
- **Groundedness**: how closely a result stays tied to what the person actually said, rather than drifting or inventing things.
- **AI grader (LLM-as-judge)**: using a model to score another model's output, checked against human judgment first.
- **Traceability / run stamping**: recording exactly which model, prompt version, and settings produced a result.
- **Prompt version**: a fingerprint of the prompt text, showing which version produced a given result.

## Where to find things

- Tranche 1 and Tranche 2 design spec: `docs/superpowers/specs/2026-09-26-interviewer-evaluation-design.md`
- Tranche 2 design detail: `docs/superpowers/specs/2026-09-27-interviewer-eval-tranche-2-design.md`
- Eval code: `backend/evals/interviewer/` (how to run it: its `README.md`)
