# AI Interviewer — decisions & follow-ups (office verification session, 2026-07-29)

Captured during the DB-gated verification of `feature/ai-interviewer`. The no-DB build
(11 tasks, reviewed, pushed @ `4c8c630`) verified live against the real backend + Sonnet 5.

## Decisions made & implemented this session

### Model-signalled "Build my playbook" (replaces the fixed message-count gate)
The interviewer decides when it has gathered enough and offers to build; the button appears
on that signal. Learner stays in control (signal → reveal → they click), matching the prompt's
existing "guided soft-finish" §.

- **Elaborate offer:** when it offers to build, the interviewer previews what the playbook
  delivers (where-you-are-today read, tailored use-cases with before→after + effort, next
  moves, one thing to try today) — in its own words, not a canned list.
- **Signal:** a hidden `[[READY_TO_BUILD]]` marker on the offer turn's last line. Stripped from
  the learner's live chat (never seen), and from the generation + admin transcripts. Emitted
  only when offering to build.
- **Fallback floor:** if the model never signals, the manual build unlocks after **6 exchanges**
  (`FALLBACK_MIN_ANSWERS`) — no premature builds, no stuck learners.
- Files: `backend/prompts/interview.md`, `frontend/src/pages/Interview.tsx`,
  `backend/src/services/interview_service.py` (+ 2 unit tests).

### Admin interview AI-surface toggle (blocker fix)
The admin panel intentionally never exposed the `interview` AI-surface toggle, but the backend
gates `/api/interview/*` on it → the surface was un-enablable. Interview now rides a third
"AI enabled" toggle on its component row (mirrors Assessment). File: `frontend/src/pages/admin2/ProjectsPage.tsx`.

### Admin "Reset interview" button
The `DELETE /api/admin/interviews/{user_id}` endpoint existed but had no UI. Added a "Reset
interview" button to the admin card (`InterviewCard.tsx` + `useResetInterview` in `admin2/api.ts`),
with a confirm — deletes the conversation + playbook so the learner can retake. Files: our own.

### Chat auto-scroll + meta-question handling (live-test feedback)
- `Interview.tsx`: the chat now pins to the latest turn as messages arrive/stream (was: user had
  to scroll manually after every turn).
- `interview.md`: the interviewer now treats a user's readiness/meta-question ("do you need more?",
  "is that enough?", "can we build it?") as a **readiness check, not an answer** — it weighs its
  checklist and either makes the build offer (marker) or names what would still sharpen the playbook.
  (Prompt is `load_prompt`-cached + uvicorn only watches `.py`, so a backend restart is needed for
  prompt-only edits to go live.)

### Chat input UX + building copy (live-test feedback, round 2)
- Input is now an auto-growing `<textarea>` (was single-line `<input>`): **Enter sends, Shift+Enter
  inserts a newline**, and it grows vertically with the answer (capped ~140px, then scrolls) so
  learners can reread before sending.
- **422 on very large input fixed:** server caps content at 4000 chars; added `maxLength={4000}`
  client guard so it can't be exceeded (was a raw 422). (Nicety not done: a char counter / paste-
  truncation warning — backlog if wanted.)
- Building screen now says generation "usually takes a minute or two — keep this tab open." NOTE:
  generation is a single synchronous request, so true "leave and come back later" is NOT safe yet
  (aborting the request mid-build may not persist). Making it background/resumable is a backlog item.

### AppNav responsive title
Long titles ("AI Opportunity Interview") overflowed the fixed 64px bar on narrow screens.
Title now shrinks (clamp) and wraps to two centered lines on very narrow screens — no truncation.
File: `frontend/src/components/AppNav.tsx`.

## Firewall audit — PASSED (live, real Sonnet playbook, 2026-07-29)
`GET /api/interview/me` returns `shared` only — zero `internal` fields; no score / maturity
label / input-quality tier / "how much you shared" characterisation in the free-text; the
8192-token generation returned complete (not truncated). Two-box firewall proven end-to-end
at the content level. Minor watch-note (not a breach): the `where_you_are_today` phrase
"a strong foundation few people have built yet" is a mild motivational comparison — keep an
eye on this class of phrasing in the prompt; it discloses no score/band and no other user's data.

## Backlog (deferred — revisit once everything is live)

1. **Playbook export / polished standalone artifact.** So learners aren't forced back into the
   hub to view their playbook. This is the plan's already-deferred "Option-C standalone HTML
   artifact." Lean v1 candidate: a "Download / Save-as-PDF" button + a print stylesheet. Heavier
   option: server-rendered branded PDF. Firewall-safe (only renders `shared`).
2. **Admin "assessment complete" indicator.** The admin user-detail Assessment card should clearly
   surface whether the survey is `complete` (currently hard to tell).
3. **Playbook `where_you_are_today` formatting.** The opening paragraph reads as a wall of text —
   break it up for readability. v1 acceptable as-is.
4. **Interviewer topic-jumping.** It can bounce between two threads the learner raised rather than
   taking one to a concrete episode before switching. Prompt-tuning (the checklist + ladder-limit
   rules already exist); tune carefully to avoid over-constraining. Subjective — needs live iteration.
