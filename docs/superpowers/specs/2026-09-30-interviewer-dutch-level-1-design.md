# Interviewer in Dutch, level 1 (#83)

Date: 2026-09-30. Decisions by Aaron the same day: level 1 now, level 2 logged as #137; Flemish Dutch with the formal "u"; 4 Dutch eval personas.

## Goal

A learner can have the AI interview and get their playbook in Dutch, measured by the eval, without English getting worse.

## Scope

**In:** the two interviewer prompts (`backend/prompts/interview.md`, `interview_playbook.md`) and the eval (`backend/evals/interviewer/`: word lists, checks, 4 Dutch cases).

**Out:**
- Level 2 (#137): a per-project language setting, a fully Dutch opener chosen by setting, and Dutch page headings.
- Any change to `interview_context.py`, `interview_service.py`, `core/dependencies/interview.py` or `routers/chat.py`. Matthias restructures those in phase D (D9/D10); level 1 needs no code there.
- The Playbook page headings stay English, so a Dutch playbook shows under English headings.

## Behaviour

1. **Interview language.** The interviewer answers in the language of the person's latest message. If a message mixes languages, it uses the language most of the message is in.
2. **Dutch means Flemish Dutch with "u".** Belgian vocabulary and phrasing, formal "u" / "uw", and the same warm, direct colleague tone as the English prompt.
3. **Opener.** The opener is in the language of the assessment's own free-text answers in the briefing: Dutch if those are in Dutch, otherwise English. The assessment form itself is English-only, so those two answers are the only language signal there is. (Aaron, 2026-09-30: the first version added a Dutch invitation line to English openers; in the eval it flipped 10 of 13 English personas into Dutch, so it was dropped.) The opener asks only its correction question.
2b. **Flemish, not Netherlands Dutch or translated English:** "klopt dat ongeveer?", "dat is logisch", and no English jargon inside Dutch sentences. The briefing's department is a team, never the company's name.
4. **Playbook language.** The playbook is written in the language most of the person's own interview answers are in, with "u" when it addresses them. JSON keys and fixed enum values stay as they are.
5. **Everything else stays language-neutral.** The hard stop, the ready marker and the one-question rule don't depend on language.

## Eval changes

- **Word lists (`vocabulary.py`).** Dutch lists are added to each English list, and every check scans for both languages:
  - no judging: "volwassenheid", "maturiteit", "uw niveau", "uw score", "de meeste mensen", "vergeleken met anderen", "sceptisch", "terughoudend", "defensief", "weinig informatie", ...
  - internal words: "uw intake", "intakeformulier", "inputkwaliteit", "maturiteitsniveau", ...
  - pronouns: "hij", "hem", "haar", "hijzelf", "haarzelf". Known limit: "zij", "ze" and "zijn" are left out, because they also mean "they" and "to be / are" and would flag almost every Dutch text. A guessed "zijn" (his) is therefore missed.
- **Chat checks.** Dutch self-answer openers ("ja", "nee", "eerlijk gezegd", "ik", "meestal", ...) and acceptance phrases ("klinkt goed", "laten we dat doen", "doe maar", "ga uw gang").
- **Language checks.** A deterministic function-word count, with no model call, decides Dutch or English:
  - `chat_language_match` (rate): the share of interviewer turns that are in the language of the learner's previous turn.
  - `playbook_language` (hard, Dutch cases only): the shared box is in Dutch.
- **4 Dutch cases**, all invented people:
  - 2 management, 1 operational, 1 adversarial injection;
  - production, construction, utilities and services;
  - at least one with Dutch assessment free text (Dutch opener expected) and one with English free text but Dutch answers (the switch).

  They are simulated with `simulate --case`, reviewed and approved by Aaron like the English ones, and added to the frozen set.

## Measurement

- **Chat:** `simulate --variant v7 --reps 2 --hard-stop` over all cases, then `chat-report`, reading every cut and every language mismatch by hand.
- **Playbook:** `run --variant v7 --reps 3`, then `compare` against the baseline for the English cases.

Targets:
- Dutch cases: interview and playbook in Dutch, and every hard rule as good as the English cases.
- English cases: no regression beyond the noise margin.
- The existing `plant-manager-dutch` case (mostly English with Dutch slips) must stay sensible and must not flip-flop into Dutch on every slip. If it does, the language rule gets tuned.

## Update 2026-10-01: the learner picks the language

Aaron: "If we don't prompt them, or inform them that they can do that, then they won't." Guessing from the assessment's typed answers is replaced by an explicit choice. It folds in #138 and the Dutch-headings part of #137 (the per-project default stays open in #137).

- **Welcome screen:** an English / Nederlands toggle at the top. Picking one switches the page at once.
- **Saved and sent:** the choice goes with `POST /api/interview/opener {"language": "en"|"nl"}` and is stored in `conversations.language`, a new nullable column (additive migration `f9c9852f6362`; NULL = English).
- **Prompts:** one fixed line, `<interview_language>xx</interview_language>`, is added to the opener, to every chat turn (with the briefing) and to the playbook prompt. The interviewer uses that language from its first turn, and follows the learner only if they write a whole message in the other language.
- **Frontend text:** every learner-facing text on the interview screens and the playbook page comes from `frontend/src/lib/interviewStrings.ts`, in English and Flemish Dutch. The admin panel's playbook view keeps English headings.
- **Playbook ceiling:** the playbook's output limit goes from 8192 to 12288 tokens. Dutch playbooks run about 15% longer, and long Dutch interviews hit the old limit twice.
- **Eval:** each case carries `language`. The four Dutch cases pick `nl`; `chat_language_match` expects the opener in the chosen language.
