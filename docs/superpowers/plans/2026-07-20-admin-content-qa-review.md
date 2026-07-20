# Admin-Assigned Content QA Review — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce two review reports (copy/layout + quiz) over the 91 lessons the `admin admin`
account sees across its 9 assigned tracks, measured against the house authoring guide — without
editing any live content.

**Architecture:** One read-only DB pull → tested pure-function deterministic sweeps
(punctuation, British-English, quiz spacing/heading conformance, quiz structure stats) → a
per-module editorial Workflow fan-out (~26 agents) → a report builder that merges both into two
plain-markdown files. Deterministic checkers are pure functions with unit tests; the fetch,
sweep-runner, workflow, and report-builder are I/O/orchestration verified by running and
inspecting output.

**Tech Stack:** Python 3.13 + uv, asyncpg (DB pull, pattern of
`backend/scripts/read_foundation_to_tools.py`), pytest (checker tests), the `Workflow` tool
(Phase 2 fan-out). All tooling lives in `backend/scripts/content_qa/`; artifacts in
`scratch_review/admin_content_qa_2026-07-20/`; the two final reports in `scratch_review/`.

## Global Constraints

- **Standard = `scratch_review/claude_cowork/authoring_guide.md`, applied hub-wide.** Deviations become findings.
- **Report-only. Never edit live DB content in this work.** Applying fixes is a separate, later, separately-approved phase.
- **Scope = exactly 91 lessons / 26 modules / 9 tracks** = the intersection of `user_tracks ∧ user_modules ∧ user_lessons` for user `587f5667-2ddc-4b95-827c-09bcb92c5b7c`. Tracks: General I, General II, Copilot, Claude, Obsidian, General III, Copilot II, Claude II, For Developers. Excluded: Introduction, Power Automate/Apps, Lovable, Confluence, and the 2 "use case build" capstone lessons (module not module-assigned).
- **British/EU spelling** is the target: colour, organisation, summarise, behaviour, **Artefact** (not Artifact). The Americanism scan flags American forms ONLY — correct en-GB forms must never fire.
- **Punctuation hard rule:** no em dash (—, U+2014), en dash (–, U+2013), or ellipsis (…, U+2026) in any text field.
- **Spacing convention:** `whitespace` is size `md`, used as a separator just before a closing quiz; a `heading` reading "Check your understanding" immediately precedes each quiz.
- **Answer-length bug is already fixed** — do NOT check or report the "correct answer is longest option" pattern.
- **Reports are plain markdown** in `scratch_review/` (never Artifacts — rendering is unreliable on this project); every finding carries an **exact quote** or block locator.
- **Env/DB access:** scripts load `backend/.env` (keys `DATABASE__HOST/PORT/USERNAME/PASSWORD/NAME`), connect with `ssl="require"`. Run scripts from the `backend/` dir via `uv run python ...`.
- **Git hygiene:** commit only explicit pathspecs (never `git add -A`) — the working tree carries other people's concurrent work. Commit the tooling under `backend/scripts/content_qa/` and the two final reports; leave intermediate JSON snapshots untracked.

---

## File Structure

- `backend/scripts/content_qa/__init__.py` — marks the package.
- `backend/scripts/content_qa/blocks.py` — `iter_texts(blocks)`: yields `(path, text)` for every prose string in a `content_blocks` list. The shared primitive.
- `backend/scripts/content_qa/checks.py` — pure deterministic checkers: `find_banned_punctuation`, `find_americanisms`, `check_quiz_conformance`, `quiz_stats`.
- `backend/scripts/content_qa/tests/test_blocks.py` — unit tests for `iter_texts`.
- `backend/scripts/content_qa/tests/test_checks.py` — unit tests for the four checkers.
- `backend/scripts/content_qa/fetch_scope.py` — read-only DB pull → `lessons_snapshot.json`.
- `backend/scripts/content_qa/run_sweeps.py` — runs the checkers over the snapshot → `deterministic_findings.json`, `summary.md`, and `per_module/<n>__<slug>.json` (enriched: module meta + its lessons' blocks + its lessons' deterministic findings).
- `backend/scripts/content_qa/phase2_workflow.md` — the Workflow script (committed as a reference; run via the `Workflow` tool).
- `backend/scripts/content_qa/build_reports.py` — merges `deterministic_findings.json` + `phase2_findings.json` → the two markdown reports.
- `scratch_review/admin_content_qa_2026-07-20/` — working dir for all JSON artifacts (untracked).
- `scratch_review/copy_layout_review_2026-07-20.md`, `scratch_review/quiz_review_2026-07-20.md` — the two deliverables (committed).

---

## Task 1: Package scaffold + `iter_texts` primitive

**Files:**
- Create: `backend/scripts/content_qa/__init__.py`
- Create: `backend/scripts/content_qa/blocks.py`
- Test: `backend/scripts/content_qa/tests/test_blocks.py`

**Interfaces:**
- Produces: `iter_texts(blocks: list[dict]) -> Iterator[tuple[str, str]]` — yields `(path, text)` where `path` is a human-readable locator like `blocks[3].questions[0].options[1]` and `text` is the prose string. Skips non-prose keys (`id`, `type`, `mode`, `source`, `size`, `level`, `blob_path`, `url`, `bucketId`, `correctOptionId`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/scripts/content_qa/tests/test_blocks.py
from content_qa.blocks import iter_texts


def test_extracts_simple_text_fields():
    blocks = [
        {"id": "a", "type": "heading", "level": 2, "text": "Hello"},
        {"id": "b", "type": "paragraph", "text": "World"},
    ]
    out = list(iter_texts(blocks))
    assert ("blocks[0].text", "Hello") in out
    assert ("blocks[1].text", "World") in out
    # non-prose keys are never yielded
    assert all("Hello" != t or p.endswith(".text") for p, t in out)
    assert not any(t in ("heading", "paragraph") for _, t in out)


def test_extracts_nested_quiz_and_card_text():
    blocks = [
        {
            "id": "q",
            "type": "quiz",
            "questions": [
                {"id": "q1", "q": "Why?", "options": ["A", "B"], "correct": 0,
                 "explanation": "Because."},
            ],
        },
        {"id": "c", "type": "card_group",
         "cards": [{"id": "c1", "title": "T", "body": "Bod"}]},
    ]
    texts = {t for _, t in iter_texts(blocks)}
    assert {"Why?", "A", "B", "Because.", "T", "Bod"} <= texts


def test_skips_non_prose_locators():
    blocks = [{"id": "i", "type": "image", "blob_path": "images/x.png",
               "alt": "a diagram", "url": "https://sas", "width": 80}]
    texts = {t for _, t in iter_texts(blocks)}
    assert "a diagram" in texts          # alt IS prose
    assert "images/x.png" not in texts   # blob_path is not
    assert "https://sas" not in texts    # url is not
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=scripts uv run pytest scripts/content_qa/tests/test_blocks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'content_qa'` / `iter_texts`.

- [ ] **Step 3: Implement `iter_texts`**

```python
# backend/scripts/content_qa/__init__.py
# (empty — package marker)
```

```python
# backend/scripts/content_qa/blocks.py
"""Walk the prose out of a lessons.content_blocks list."""
from __future__ import annotations

from collections.abc import Iterator

# Keys whose string values are identifiers/config, not learner-facing prose.
NON_PROSE_KEYS = frozenset(
    {"id", "type", "mode", "source", "size", "level", "blob_path", "url",
     "bucketId", "correctOptionId"}
)


def iter_texts(blocks: list[dict]) -> Iterator[tuple[str, str]]:
    """Yield (path, text) for every prose string across a content_blocks list."""
    for i, block in enumerate(blocks or []):
        yield from _walk(block, f"blocks[{i}]")


def _walk(node: object, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(node, str):
        if node.strip():
            yield (path, node)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key in NON_PROSE_KEYS:
                continue
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            yield from _walk(item, f"{path}[{idx}]")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=scripts uv run pytest scripts/content_qa/tests/test_blocks.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/content_qa/__init__.py backend/scripts/content_qa/blocks.py backend/scripts/content_qa/tests/test_blocks.py
git commit -m "Add content_qa iter_texts block-prose walker"
```

---

## Task 2: Punctuation-ban + British-English checkers

**Files:**
- Modify: `backend/scripts/content_qa/checks.py` (create)
- Test: `backend/scripts/content_qa/tests/test_checks.py` (create)

**Interfaces:**
- Consumes: `iter_texts` from Task 1.
- Produces:
  - `find_banned_punctuation(blocks: list[dict]) -> list[dict]` — each finding `{ "kind": "punctuation", "char": "em-dash|en-dash|ellipsis", "path": str, "snippet": str }`.
  - `find_americanisms(blocks: list[dict]) -> list[dict]` — each finding `{ "kind": "americanism", "term": str, "suggestion": str, "path": str, "snippet": str }`.
  - `AMERICANISMS: dict[str, str]` — American → British mapping, matched as whole words, case-insensitively.

- [ ] **Step 1: Write the failing tests**

```python
# backend/scripts/content_qa/tests/test_checks.py
from content_qa.checks import find_americanisms, find_banned_punctuation


def _para(text):
    return [{"id": "p", "type": "paragraph", "text": text}]


def test_flags_em_en_dash_and_ellipsis():
    found = find_banned_punctuation(_para("A long thought — really … you know – yes"))
    chars = {f["char"] for f in found}
    assert chars == {"em-dash", "en-dash", "ellipsis"}
    assert all(f["snippet"] for f in found)


def test_clean_text_has_no_punctuation_findings():
    assert find_banned_punctuation(_para("A normal sentence, with a comma.")) == []


def test_flags_american_spellings():
    found = find_americanisms(_para("Organize the color of your behavior and analyze it."))
    terms = {f["term"].lower() for f in found}
    assert {"organize", "color", "behavior", "analyze"} <= terms
    for f in found:
        assert f["suggestion"]  # every hit carries a British suggestion


def test_does_not_flag_correct_british_forms():
    found = find_americanisms(_para(
        "Organise the colour of your behaviour, summarise the Artefact, and centre it."
    ))
    assert found == []


def test_americanism_word_boundaries_no_false_positives():
    # 'size', 'prize', 'maize' end in -ize but are not American -ise words;
    # 'parameter' contains 'meter'; none should fire.
    found = find_americanisms(_para("The size of the prize parameter in the maize field."))
    assert found == []


def test_flags_nested_quiz_option_text():
    blocks = [{"id": "q", "type": "quiz", "questions": [
        {"id": "1", "q": "Pick", "options": ["Organize files", "Leave them"],
         "correct": 0, "explanation": "ok"}]}]
    found = find_americanisms(blocks)
    assert any(f["path"].endswith("options[0]") for f in found)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=scripts uv run pytest scripts/content_qa/tests/test_checks.py -v`
Expected: FAIL — `cannot import name` / `find_americanisms` undefined.

- [ ] **Step 3: Implement the two checkers**

```python
# backend/scripts/content_qa/checks.py
"""Deterministic content checks over a lessons.content_blocks list.

Pure functions: input is a content_blocks list, output is a list of finding
dicts. No I/O, no DB. The Americanism map is a curated allowlist (exact forms)
rather than a broad -ize regex, so it never fires on correct British spellings
or on words like 'size'/'prize' that merely end in -ize.
"""
from __future__ import annotations

import re

from content_qa.blocks import iter_texts

BANNED_PUNCTUATION = {"—": "em-dash", "–": "en-dash", "…": "ellipsis"}

# American -> British. Whole-word, case-insensitive. Includes common inflections.
AMERICANISMS: dict[str, str] = {
    "organize": "organise", "organizes": "organises", "organized": "organised",
    "organizing": "organising", "organization": "organisation",
    "organizations": "organisations",
    "recognize": "recognise", "recognized": "recognised", "recognizing": "recognising",
    "customize": "customise", "customized": "customised", "customizing": "customising",
    "customization": "customisation",
    "personalize": "personalise", "personalized": "personalised",
    "personalizing": "personalising", "personalization": "personalisation",
    "prioritize": "prioritise", "prioritized": "prioritised", "prioritizing": "prioritising",
    "summarize": "summarise", "summarized": "summarised", "summarizing": "summarising",
    "analyze": "analyse", "analyzed": "analysed", "analyzing": "analysing",
    "optimize": "optimise", "optimized": "optimised", "optimizing": "optimising",
    "minimize": "minimise", "maximize": "maximise",
    "realize": "realise", "realized": "realised", "realizing": "realising",
    "emphasize": "emphasise", "apologize": "apologise", "categorize": "categorise",
    "specialize": "specialise", "standardize": "standardise", "utilize": "utilise",
    "capitalize": "capitalise", "initialize": "initialise", "visualize": "visualise",
    "synchronize": "synchronise", "familiarize": "familiarise",
    "color": "colour", "colors": "colours", "colored": "coloured", "coloring": "colouring",
    "behavior": "behaviour", "behaviors": "behaviours",
    "favorite": "favourite", "favorites": "favourites", "favor": "favour",
    "honor": "honour", "labor": "labour", "neighbor": "neighbour",
    "center": "centre", "centered": "centred",
    "catalog": "catalogue", "dialog": "dialogue",
    "artifact": "artefact", "artifacts": "artefacts",
    "defense": "defence", "offense": "offence",
    "gray": "grey", "modeling": "modelling", "traveler": "traveller",
    "canceled": "cancelled", "canceling": "cancelling",
    "fulfill": "fulfil", "enrollment": "enrolment",
    "license": "licence",  # noun; verb form 'license' is BrE too — flag for human check
}

# One case-insensitive pattern with word boundaries over all keys.
_AMERICANISM_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in AMERICANISMS) + r")\b", re.IGNORECASE
)


def _snippet(text: str, start: int, end: int, radius: int = 40) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    pre = "..." if lo > 0 else ""
    post = "..." if hi < len(text) else ""
    return f"{pre}{text[lo:hi].strip()}{post}"


def find_banned_punctuation(blocks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for path, text in iter_texts(blocks):
        for ch, name in BANNED_PUNCTUATION.items():
            idx = text.find(ch)
            while idx != -1:
                findings.append(
                    {"kind": "punctuation", "char": name, "path": path,
                     "snippet": _snippet(text, idx, idx + 1)}
                )
                idx = text.find(ch, idx + 1)
    return findings


def find_americanisms(blocks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for path, text in iter_texts(blocks):
        for m in _AMERICANISM_RE.finditer(text):
            term = m.group(1)
            findings.append(
                {"kind": "americanism", "term": term,
                 "suggestion": AMERICANISMS[term.lower()], "path": path,
                 "snippet": _snippet(text, m.start(), m.end())}
            )
    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=scripts uv run pytest scripts/content_qa/tests/test_checks.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/content_qa/checks.py backend/scripts/content_qa/tests/test_checks.py
git commit -m "Add punctuation-ban and British-English content checkers"
```

---

## Task 3: Quiz spacing/heading conformance + structure stats

**Files:**
- Modify: `backend/scripts/content_qa/checks.py`
- Modify: `backend/scripts/content_qa/tests/test_checks.py`

**Interfaces:**
- Consumes: nothing new (operates on the raw `blocks` list order/types).
- Produces:
  - `check_quiz_conformance(blocks: list[dict]) -> list[dict]` — findings `{ "kind": "quiz-heading"|"quiz-separator"|"whitespace-size"|"whitespace-orphan", "detail": str, "block_index": int }`.
  - `quiz_stats(blocks: list[dict]) -> dict` — `{ "num_quizzes": int, "questions": [ { "num_options": int, "correct_index": int, "quiz_index": int } ], "num_whitespace": int }`.

- [ ] **Step 1: Write the failing tests**

```python
# append to backend/scripts/content_qa/tests/test_checks.py
from content_qa.checks import check_quiz_conformance, quiz_stats

HEADING = {"id": "h", "type": "heading", "level": 2, "text": "Check your understanding"}
WS_MD = {"id": "w", "type": "whitespace", "size": "md"}
QUIZ = {"id": "q", "type": "quiz", "questions": [
    {"id": "1", "q": "Q", "options": ["a", "b", "c"], "correct": 1, "explanation": "e"}]}


def test_conformant_quiz_has_no_findings():
    blocks = [{"id": "p", "type": "paragraph", "text": "body"}, HEADING, WS_MD, QUIZ]
    assert check_quiz_conformance(blocks) == []


def test_missing_check_understanding_heading_is_flagged():
    blocks = [WS_MD, QUIZ]  # no heading before the quiz
    kinds = {f["kind"] for f in check_quiz_conformance(blocks)}
    assert "quiz-heading" in kinds


def test_missing_md_separator_is_flagged():
    blocks = [HEADING, QUIZ]  # heading present but no whitespace(md) between it and the quiz
    kinds = {f["kind"] for f in check_quiz_conformance(blocks)}
    assert "quiz-separator" in kinds


def test_wrong_whitespace_size_is_flagged():
    blocks = [HEADING, {"id": "w", "type": "whitespace", "size": "sm"}, QUIZ]
    kinds = {f["kind"] for f in check_quiz_conformance(blocks)}
    assert "whitespace-size" in kinds


def test_orphan_whitespace_not_near_quiz_is_flagged():
    blocks = [{"id": "p", "type": "paragraph", "text": "x"}, WS_MD,
              {"id": "p2", "type": "paragraph", "text": "y"}]
    kinds = {f["kind"] for f in check_quiz_conformance(blocks)}
    assert "whitespace-orphan" in kinds


def test_quiz_stats_counts_questions_options_positions():
    blocks = [HEADING, WS_MD, QUIZ]
    stats = quiz_stats(blocks)
    assert stats["num_quizzes"] == 1
    assert stats["questions"] == [{"num_options": 3, "correct_index": 1, "quiz_index": 0}]
    assert stats["num_whitespace"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=scripts uv run pytest scripts/content_qa/tests/test_checks.py -v`
Expected: FAIL — `check_quiz_conformance` / `quiz_stats` undefined.

- [ ] **Step 3: Implement conformance + stats**

```python
# append to backend/scripts/content_qa/checks.py

CHECK_UNDERSTANDING = "check your understanding"


def check_quiz_conformance(blocks: list[dict]) -> list[dict]:
    """Enforce the house convention around quizzes and whitespace separators.

    For each quiz: walking backward past whitespace blocks, the first
    non-whitespace block must be a heading 'Check your understanding'
    (quiz-heading), and at least one of the skipped whitespace blocks must be
    size 'md' (quiz-separator). Any whitespace of a non-'md' size is flagged
    (whitespace-size). Any whitespace not adjacent to a quiz is flagged
    (whitespace-orphan).
    """
    blocks = blocks or []
    findings: list[dict] = []
    quiz_indices = {i for i, b in enumerate(blocks) if b.get("type") == "quiz"}

    # whitespace-size + whitespace-orphan
    for i, b in enumerate(blocks):
        if b.get("type") != "whitespace":
            continue
        if b.get("size") != "md":
            findings.append({"kind": "whitespace-size", "block_index": i,
                             "detail": f"whitespace size is {b.get('size')!r}, expected 'md'"})
        # orphan = the nearest non-whitespace block AFTER it is not a quiz
        j = i + 1
        while j < len(blocks) and blocks[j].get("type") == "whitespace":
            j += 1
        if not (j < len(blocks) and blocks[j].get("type") == "quiz"):
            findings.append({"kind": "whitespace-orphan", "block_index": i,
                             "detail": "whitespace block is not immediately before a quiz"})

    # quiz-heading + quiz-separator
    for qi in sorted(quiz_indices):
        saw_md_ws = False
        k = qi - 1
        while k >= 0 and blocks[k].get("type") == "whitespace":
            if blocks[k].get("size") == "md":
                saw_md_ws = True
            k -= 1
        prev = blocks[k] if k >= 0 else None
        is_heading = (
            prev is not None
            and prev.get("type") == "heading"
            and (prev.get("text") or "").strip().lower() == CHECK_UNDERSTANDING
        )
        if not is_heading:
            findings.append({"kind": "quiz-heading", "block_index": qi,
                             "detail": "no 'Check your understanding' heading immediately before the quiz"})
        if not saw_md_ws:
            findings.append({"kind": "quiz-separator", "block_index": qi,
                             "detail": "no whitespace(md) separator immediately before the quiz"})
    return findings


def quiz_stats(blocks: list[dict]) -> dict:
    blocks = blocks or []
    questions: list[dict] = []
    quiz_index = 0
    num_quizzes = 0
    for b in blocks:
        if b.get("type") == "quiz":
            num_quizzes += 1
            for q in b.get("questions", []):
                questions.append({
                    "num_options": len(q.get("options", [])),
                    "correct_index": q.get("correct"),
                    "quiz_index": quiz_index,
                })
            quiz_index += 1
    num_whitespace = sum(1 for b in blocks if b.get("type") == "whitespace")
    return {"num_quizzes": num_quizzes, "questions": questions,
            "num_whitespace": num_whitespace}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=scripts uv run pytest scripts/content_qa/tests/ -v`
Expected: PASS (all tests across both test files).

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/content_qa/checks.py backend/scripts/content_qa/tests/test_checks.py
git commit -m "Add quiz spacing/heading conformance and structure-stats checkers"
```

---

## Task 4: Read-only scope fetch → `lessons_snapshot.json`

**Files:**
- Create: `backend/scripts/content_qa/fetch_scope.py`

**Interfaces:**
- Produces: `scratch_review/admin_content_qa_2026-07-20/lessons_snapshot.json` — a JSON list, ordered by track/module/lesson sort_order, each element `{ track, track_level, track_order, module_title, module_id, module_order, lesson_id, lesson_title, lesson_order, content_blocks }`. Exactly 91 elements.

- [ ] **Step 1: Write the fetch script**

```python
# backend/scripts/content_qa/fetch_scope.py
"""Read-only pull of the 91 in-scope lessons (admin's 9 assigned tracks)."""
import asyncio
import json
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[2]  # .../backend
load_dotenv(BACKEND / ".env")
OUT_DIR = BACKEND.parent / "scratch_review" / "admin_content_qa_2026-07-20"
UID = "587f5667-2ddc-4b95-827c-09bcb92c5b7c"

QUERY = """
SELECT t.name AS track, t.required_level AS track_level, t.sort_order AS track_order,
       m.title AS module_title, m.id AS module_id, m.sort_order AS module_order,
       l.id AS lesson_id, l.title AS lesson_title, l.sort_order AS lesson_order,
       l.content_blocks
FROM user_lessons ul
JOIN lessons l ON l.id = ul.lesson_id
JOIN modules m ON m.id = l.module_id
JOIN tracks  t ON t.id = m.track_id
JOIN user_modules um ON um.user_id = ul.user_id AND um.module_id = m.id
JOIN user_tracks  ut ON ut.user_id = ul.user_id AND ut.track_id = t.id
WHERE ul.user_id = $1
ORDER BY t.sort_order, m.sort_order, l.sort_order
"""


async def main() -> None:
    conn = await asyncpg.connect(
        host=os.environ["DATABASE__HOST"], port=int(os.environ["DATABASE__PORT"]),
        user=os.environ["DATABASE__USERNAME"], password=os.environ["DATABASE__PASSWORD"],
        database=os.environ["DATABASE__NAME"], ssl="require",
    )
    try:
        rows = await conn.fetch(QUERY, UID)
    finally:
        await conn.close()

    out = []
    for r in rows:
        cb = r["content_blocks"]
        cb = json.loads(cb) if isinstance(cb, str) else cb
        out.append({
            "track": r["track"], "track_level": r["track_level"],
            "track_order": r["track_order"], "module_title": r["module_title"],
            "module_id": str(r["module_id"]), "module_order": r["module_order"],
            "lesson_id": str(r["lesson_id"]), "lesson_title": r["lesson_title"],
            "lesson_order": r["lesson_order"], "content_blocks": cb or [],
        })
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "lessons_snapshot.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(out)} lessons to {OUT_DIR / 'lessons_snapshot.json'}")


asyncio.run(main())
```

- [ ] **Step 2: Run it**

Run: `cd backend && uv run python scripts/content_qa/fetch_scope.py`
Expected output: `Wrote 91 lessons to .../lessons_snapshot.json`.

- [ ] **Step 3: Sanity-check the output**

Run: `cd backend && uv run python -c "import json,pathlib; d=json.load(open(pathlib.Path('../scratch_review/admin_content_qa_2026-07-20/lessons_snapshot.json'),encoding='utf-8')); print(len(d), 'lessons'); print(sorted({x['track'] for x in d}))"`
Expected: `91 lessons` and exactly the 9 track names (General I/II/III, Copilot, Copilot II, Claude, Claude II, Obsidian, For Developers). If the count is not 91, STOP and reconcile against the spec's scope query before continuing.

- [ ] **Step 4: Commit the script (not the snapshot)**

```bash
git add backend/scripts/content_qa/fetch_scope.py
git commit -m "Add read-only scope fetch for admin content QA"
```

---

## Task 5: Run the sweeps → findings + summary + per-module files

**Files:**
- Create: `backend/scripts/content_qa/run_sweeps.py`

**Interfaces:**
- Consumes: `lessons_snapshot.json` (Task 4); `find_banned_punctuation`, `find_americanisms`, `check_quiz_conformance`, `quiz_stats` (Tasks 2–3).
- Produces:
  - `deterministic_findings.json` — `{ lesson_id: { track, module_title, lesson_title, punctuation:[...], americanisms:[...], quiz_conformance:[...], quiz_stats:{...} } }`.
  - `summary.md` — human roll-up: totals per check, per-track counts, the question-count distribution.
  - `per_module/<module_order>__<slug>.json` — one file per module: `{ track, module_title, lessons: [ { lesson_id, lesson_title, content_blocks, deterministic } ] }`. These feed the Phase-2 workflow.

- [ ] **Step 1: Write the sweep runner**

```python
# backend/scripts/content_qa/run_sweeps.py
"""Run deterministic checks over the snapshot; emit findings + per-module files."""
import json
import re
from collections import Counter
from pathlib import Path

from content_qa.checks import (
    check_quiz_conformance, find_americanisms, find_banned_punctuation, quiz_stats,
)

OUT_DIR = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def main() -> None:
    lessons = json.loads((OUT_DIR / "lessons_snapshot.json").read_text(encoding="utf-8"))
    findings: dict[str, dict] = {}
    modules: dict[str, dict] = {}

    for les in lessons:
        blocks = les["content_blocks"]
        det = {
            "track": les["track"], "module_title": les["module_title"],
            "lesson_title": les["lesson_title"],
            "punctuation": find_banned_punctuation(blocks),
            "americanisms": find_americanisms(blocks),
            "quiz_conformance": check_quiz_conformance(blocks),
            "quiz_stats": quiz_stats(blocks),
        }
        findings[les["lesson_id"]] = det

        key = f"{les['module_order']:02d}__{les['track']}__{les['module_title']}"
        mod = modules.setdefault(key, {"track": les["track"],
                                       "module_title": les["module_title"], "lessons": []})
        mod["lessons"].append({
            "lesson_id": les["lesson_id"], "lesson_title": les["lesson_title"],
            "content_blocks": blocks, "deterministic": det,
        })

    (OUT_DIR / "deterministic_findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")

    per_module_dir = OUT_DIR / "per_module"
    per_module_dir.mkdir(exist_ok=True)
    for key, mod in modules.items():
        (per_module_dir / f"{slug(key)}.json").write_text(
            json.dumps(mod, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary roll-up
    punct = sum(len(f["punctuation"]) for f in findings.values())
    amer = sum(len(f["americanisms"]) for f in findings.values())
    conf = Counter()
    for f in findings.values():
        for c in f["quiz_conformance"]:
            conf[c["kind"]] += 1
    qcounts = Counter()
    for f in findings.values():
        n = f["quiz_stats"]["num_quizzes"]
        for _ in range(n):
            pass
        # questions per quiz distribution
    per_quiz_qcount = Counter()
    for f in findings.values():
        by_quiz = Counter(q["quiz_index"] for q in f["quiz_stats"]["questions"])
        for cnt in by_quiz.values():
            per_quiz_qcount[cnt] += 1

    lines = [
        "# Deterministic sweep summary — admin content QA 2026-07-20", "",
        f"- Lessons scanned: {len(findings)}",
        f"- Banned-punctuation hits: {punct}",
        f"- Americanism hits: {amer}",
        f"- Quizzes total: {sum(f['quiz_stats']['num_quizzes'] for f in findings.values())}",
        f"- Modules: {len(modules)}", "",
        "## Quiz conformance findings", "",
        *[f"- {k}: {v}" for k, v in sorted(conf.items())], "",
        "## Questions-per-quiz distribution", "",
        *[f"- {k} questions: {v} quizzes" for k, v in sorted(per_quiz_qcount.items())],
    ]
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Findings for {len(findings)} lessons; {len(modules)} per-module files; summary.md written.")


main()
```

- [ ] **Step 2: Run it**

Run: `cd backend && PYTHONPATH=scripts uv run python scripts/content_qa/run_sweeps.py`
Expected: `Findings for 91 lessons; 26 per-module files; summary.md written.`

- [ ] **Step 3: Read the summary and spot-check**

Run: `cat "../scratch_review/admin_content_qa_2026-07-20/summary.md"` and confirm the numbers are plausible (91 lessons, 26 modules, non-zero conformance findings). Open one `per_module/*.json` and confirm each lesson carries `content_blocks` + `deterministic`.

- [ ] **Step 4: Commit the runner (not the artifacts)**

```bash
git add backend/scripts/content_qa/run_sweeps.py
git commit -m "Add deterministic sweep runner + per-module payload emitter"
```

---

## Task 6: Phase 2 editorial Workflow fan-out

**Files:**
- Create: `backend/scripts/content_qa/phase2_workflow.md` (committed reference copy of the Workflow script)
- Produces (runtime): `scratch_review/admin_content_qa_2026-07-20/phase2_findings.json`

**Interfaces:**
- Consumes: `per_module/*.json` (Task 5).
- Produces: `phase2_findings.json` — a JSON list of per-module objects each `{ module_title, track, copy_layout: [...], quiz: [...] }` matching the schema below. Written by the operator from the `Workflow` tool result.

**How to run:** invoke the `Workflow` tool with the script below. `args` is a small list of the per-module file paths (list `per_module/` first). Each agent uses `agentType: 'general-purpose'` so it can `Read` its own file. After the workflow returns, save its result array verbatim to `phase2_findings.json`.

- [ ] **Step 1: List the per-module files to build `args`**

Run: `ls "../scratch_review/admin_content_qa_2026-07-20/per_module/"`
Build `args` as a JSON array of objects `{ "path": "<absolute path to the per_module json>", "module_title": "...", "track": "..." }` — one per file (derive title/track from the filename or by peeking the file).

- [ ] **Step 2: Author the Workflow script**

Save this as `backend/scripts/content_qa/phase2_workflow.md` (fenced) AND pass it as the `Workflow` tool's `script`:

````javascript
export const meta = {
  name: 'admin-content-qa-editorial',
  description: 'Per-module editorial review (copy/layout + quiz) of the 9 admin-assigned tracks',
  phases: [{ title: 'Review', detail: 'one agent per module' }],
}

const STANDARD = `
House authoring standard (apply strictly):
- British/EU spelling: colour, organisation, summarise, behaviour, Artefact (not Artifact); "interface" not "surface" for chat/tools.
- No em dash, en dash or ellipsis in any text field.
- whitespace is size 'md', used as a separator just before a closing quiz.
- A heading "Check your understanding" immediately precedes each quiz.
- Quiz is OPTIONAL per lesson (skip on light/curiosity/decision lessons). When used: 3 questions, 3-4 options, a teaching explanation each; vary which position is correct; distractors must be plausible. A 'sort' interactive can REPLACE a quiz on a decision lesson.
- The answer-length bug (correct answer being the longest option) is ALREADY FIXED — do NOT report it.
`

const SCHEMA = {
  type: 'object',
  required: ['module_title', 'track', 'copy_layout', 'quiz'],
  properties: {
    module_title: { type: 'string' },
    track: { type: 'string' },
    copy_layout: {
      type: 'array',
      items: {
        type: 'object',
        required: ['lesson_title', 'issue_type', 'quote', 'suggestion'],
        properties: {
          lesson_title: { type: 'string' },
          issue_type: { type: 'string', enum: ['typo', 'en-gb', 'layout', 'spacing', 'opener-weight', 'other'] },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          quote: { type: 'string' },
          suggestion: { type: 'string' },
          triage_bucket: { type: 'string', enum: ['wording', 'structural', 'factual', 'dedup'] },
        },
      },
    },
    quiz: {
      type: 'array',
      items: {
        type: 'object',
        required: ['lesson_title', 'verdict', 'rationale'],
        properties: {
          lesson_title: { type: 'string' },
          verdict: { type: 'string', enum: ['keep', 'trim-questions', 'convert-to-interactive', 'fix-quality', 'drop'] },
          rationale: { type: 'string' },
          suggested_question_count: { type: 'integer' },
          suggested_interactive_mode: { type: 'string', enum: ['predict', 'sort', 'spot_the_flaw', 'none'] },
          variety_note: { type: 'string' },
          quality_flags: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}

const modules = args  // [{ path, module_title, track }]
log(`Reviewing ${modules.length} modules`)

const results = await parallel(modules.map(m => () =>
  agent(
    `You are reviewing one module of an AI-enablement learning hub against the house standard.\n` +
    STANDARD +
    `\nRead the module file at: ${m.path}\n` +
    `It contains the module's lessons, each with content_blocks and a "deterministic" object ` +
    `holding already-found mechanical issues (punctuation, americanisms, quiz-conformance). ` +
    `Do NOT re-report anything already in "deterministic" — add only what judgement surfaces.\n\n` +
    `Return TWO things:\n` +
    `1. copy_layout[]: residual typos, subtle British-English the grep missed, layout oddities ` +
    `(skipped heading levels, empty blocks, opener-card that should be a lighter kicker), spacing ` +
    `oddities beyond the mechanical check. Each with an EXACT quote from the lesson.\n` +
    `2. quiz[]: one entry per quiz in the module. Judge: is it value-adding (tests the lesson's real ` +
    `thesis, not filler)? Could 3 questions be fewer? Should it become a predict/sort/spot_the_flaw ` +
    `for variety — considering the WHOLE module so the mix stays varied, not all one type? Are ` +
    `distractors plausible? Set verdict + rationale + (if relevant) suggested_question_count, ` +
    `suggested_interactive_mode, variety_note, quality_flags.\n\n` +
    `module_title="${m.module_title}", track="${m.track}".`,
    { schema: SCHEMA, agentType: 'general-purpose', label: m.module_title, phase: 'Review' }
  )
))

return results.filter(Boolean)
````

- [ ] **Step 3: Run the Workflow and save the result**

Invoke the `Workflow` tool with `script` = the script above and `args` = the list from Step 1. When it completes, write the returned array to `scratch_review/admin_content_qa_2026-07-20/phase2_findings.json` (verbatim JSON).

- [ ] **Step 4: Verify coverage**

Run: `cd backend && uv run python -c "import json,pathlib; d=json.load(open(pathlib.Path('../scratch_review/admin_content_qa_2026-07-20/phase2_findings.json'),encoding='utf-8')); print(len(d),'modules'); print(sum(len(x['quiz']) for x in d),'quiz entries')"`
Expected: `26 modules`. If fewer, identify which modules the fan-out dropped (nulls filtered out) and re-run those individually before proceeding.

- [ ] **Step 5: Commit the workflow reference**

```bash
git add backend/scripts/content_qa/phase2_workflow.md
git commit -m "Add Phase 2 editorial workflow script for content QA"
```

---

## Task 7: Build the two reports

**Files:**
- Create: `backend/scripts/content_qa/build_reports.py`

**Interfaces:**
- Consumes: `lessons_snapshot.json`, `deterministic_findings.json`, `phase2_findings.json`.
- Produces: `scratch_review/copy_layout_review_2026-07-20.md` and `scratch_review/quiz_review_2026-07-20.md`.

- [ ] **Step 1: Write the report builder**

```python
# backend/scripts/content_qa/build_reports.py
"""Merge deterministic + editorial findings into the two review reports."""
import json
from collections import Counter, defaultdict
from pathlib import Path

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
OUT = Path(__file__).resolve().parents[2].parent / "scratch_review"


def load(name):
    return json.loads((WORK / name).read_text(encoding="utf-8"))


def main() -> None:
    snapshot = load("lessons_snapshot.json")
    det = load("deterministic_findings.json")
    phase2 = load("phase2_findings.json")

    # index editorial findings by (track, module_title)
    ed_copy = defaultdict(list)
    ed_quiz = defaultdict(list)
    for mod in phase2:
        key = (mod["track"], mod["module_title"])
        ed_copy[key].extend(mod.get("copy_layout", []))
        ed_quiz[key].extend(mod.get("quiz", []))

    # ---- Copy/layout report, grouped track > module > lesson ----
    cl = ["# Copy & layout review — admin-assigned content (2026-07-20)", "",
          "Report-only. Standard: `scratch_review/claude_cowork/authoring_guide.md`.",
          "Deterministic findings are exhaustive for their patterns; editorial findings are judgement.", ""]
    cur_t = cur_m = None
    for les in snapshot:
        d = det[les["lesson_id"]]
        has_det = d["punctuation"] or d["americanisms"] or d["quiz_conformance"]
        key = (les["track"], les["module_title"])
        editorial = [f for f in ed_copy[key] if f["lesson_title"] == les["lesson_title"]]
        if not has_det and not editorial:
            continue
        if les["track"] != cur_t:
            cur_t = les["track"]; cl.append(f"\n## {cur_t}"); cur_m = None
        if les["module_title"] != cur_m:
            cur_m = les["module_title"]; cl.append(f"\n### {cur_m}")
        cl.append(f"\n**{les['lesson_title']}**")
        for f in d["punctuation"]:
            cl.append(f"- [punctuation/{f['char']}] `{f['path']}` — {f['snippet']}")
        for f in d["americanisms"]:
            cl.append(f"- [en-GB] `{f['term']}` -> `{f['suggestion']}` at `{f['path']}` — {f['snippet']}")
        for f in d["quiz_conformance"]:
            cl.append(f"- [spacing/{f['kind']}] block {f['block_index']}: {f['detail']}")
        for f in editorial:
            sev = f.get("severity", "")
            cl.append(f"- [{f['issue_type']}{'/' + sev if sev else ''}] \"{f['quote']}\" -> {f['suggestion']}")

    (OUT / "copy_layout_review_2026-07-20.md").write_text("\n".join(cl), encoding="utf-8")

    # ---- Quiz report ----
    qz = ["# Quiz review — admin-assigned content (2026-07-20)", "",
          "Report-only. Standard: `scratch_review/claude_cowork/authoring_guide.md`.",
          "Answer-length bias is already fixed and not reported.", ""]
    verdicts = Counter()
    for mod in phase2:
        if not mod.get("quiz"):
            continue
        qz.append(f"\n## {mod['track']} — {mod['module_title']}")
        for q in mod["quiz"]:
            verdicts[q["verdict"]] += 1
            bits = [f"**{q['lesson_title']}** — _{q['verdict']}_", q["rationale"]]
            if q.get("suggested_question_count") is not None:
                bits.append(f"suggested questions: {q['suggested_question_count']}")
            if q.get("suggested_interactive_mode") and q["suggested_interactive_mode"] != "none":
                bits.append(f"convert to: {q['suggested_interactive_mode']}")
            if q.get("variety_note"):
                bits.append(f"variety: {q['variety_note']}")
            if q.get("quality_flags"):
                bits.append("flags: " + ", ".join(q["quality_flags"]))
            qz.append("- " + " | ".join(bits))

    # hub-wide question-count + position stats from deterministic data
    per_quiz_qcount = Counter()
    positions = Counter()
    for d in det.values():
        by_quiz = defaultdict(list)
        for q in d["quiz_stats"]["questions"]:
            by_quiz[q["quiz_index"]].append(q)
            positions[q["correct_index"]] += 1
        for qs in by_quiz.values():
            per_quiz_qcount[len(qs)] += 1
    qz += ["\n## Hub-wide stats", "",
           "Verdicts: " + ", ".join(f"{k}={v}" for k, v in verdicts.items()),
           "Questions per quiz: " + ", ".join(f"{k}q={v}" for k, v in sorted(per_quiz_qcount.items())),
           "Correct-option position counts: " + ", ".join(f"idx{k}={v}" for k, v in sorted(positions.items()))]

    (OUT / "quiz_review_2026-07-20.md").write_text("\n".join(qz), encoding="utf-8")
    print("Wrote copy_layout_review_2026-07-20.md and quiz_review_2026-07-20.md")


main()
```

- [ ] **Step 2: Run it**

Run: `cd backend && uv run python scripts/content_qa/build_reports.py`
Expected: `Wrote copy_layout_review_2026-07-20.md and quiz_review_2026-07-20.md`.

- [ ] **Step 3: Read both reports end-to-end**

Open `scratch_review/copy_layout_review_2026-07-20.md` and `scratch_review/quiz_review_2026-07-20.md`. Confirm: findings carry exact quotes/locators; every track with issues appears; the quiz report has per-module verdicts + the hub-wide stats block. Fix any formatting/rendering issue in `build_reports.py` and re-run.

- [ ] **Step 4: Commit the builder + the two reports**

```bash
git add backend/scripts/content_qa/build_reports.py scratch_review/copy_layout_review_2026-07-20.md scratch_review/quiz_review_2026-07-20.md
git commit -m "Add report builder and generate admin content QA review reports"
```

---

## Task 8: Completeness review + hand-off

**Files:** none (review + presentation).

- [ ] **Step 1: Coverage cross-check**

Confirm every one of the 91 lessons is represented: a lesson with zero findings is legitimately absent from the copy/layout report (only issue-bearing lessons are listed), but the quiz report + deterministic findings must together account for all 91. Run a quick check that `deterministic_findings.json` has 91 keys and `phase2_findings.json` has 26 modules.

- [ ] **Step 2: Spot-verify 3 findings against the live source**

Pick 3 findings (one punctuation, one en-GB, one quiz verdict) and confirm the quoted text actually exists in the corresponding lesson's live `content_blocks` (re-fetch that lesson fresh — block ids churn, but the prose is stable). This guards against snapshot staleness.

- [ ] **Step 3: Present to Matthias**

Summarize: total findings per category, the highest-value quiz recommendations (convert-to-interactive candidates + any "drop" verdicts), and the systemic spacing/heading conformance gaps. Point to both report files. Explicitly note this is report-only and ask which findings to move into an apply phase (separate plan).

---

## Self-Review

**Spec coverage:**
- Standard = authoring guide hub-wide → Global Constraints + Task 6 STANDARD block + all checkers. ✓
- Workstream A (punctuation, en-GB, spacing/heading) → Tasks 2–3 (deterministic) + Task 6 (editorial residuals). ✓
- Workstream B (value, 3→fewer, convert-to-interactive, distractor quality; NOT answer-length) → Task 6 quiz schema + Task 7 quiz report; answer-length explicitly excluded in constraints, Task 6 STANDARD, and Task 7. ✓
- Scope = 91 lessons / 26 modules / 9 tracks → Task 4 query (the exact intersection) + verification steps. ✓
- Shared read → two reports → Tasks 4–7. ✓
- Report-only, plain markdown in scratch_review/, exact quotes → Global Constraints + Task 7. ✓
- Workflow fan-out, one agent per module → Task 6. ✓

**Placeholder scan:** No TBD/TODO; every code step has complete, runnable code; the Americanism list and quiz-conformance rules are spelled out in full. ✓

**Type consistency:** `iter_texts` → used by both checkers (Task 2/3); finding dict keys (`kind`, `path`, `term`, `suggestion`, `snippet`, `block_index`, `detail`) are consistent between `checks.py` and `build_reports.py`; per-module JSON shape (`track`, `module_title`, `lessons[].content_blocks`, `lessons[].deterministic`) matches between `run_sweeps.py` (producer) and the Task 6 agent prompt + `build_reports.py` (consumers); Phase-2 schema fields (`copy_layout[]`, `quiz[]` with `verdict`/`rationale`/`suggested_question_count`/`suggested_interactive_mode`/`variety_note`/`quality_flags`) match `build_reports.py`'s reader. ✓
