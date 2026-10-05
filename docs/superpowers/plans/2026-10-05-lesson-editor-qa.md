# Lesson editor QA + no silent overwrites + #60 fix (B5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- the lesson editor runs the house-style checks on Save, as a soft gate;
- a save from an outdated copy is refused (409), with Reload or Overwrite;
- the MDX round trip stops deleting quiz, card and question blocks (#60).

**Architecture:**
- **Backend:**
  - a pure `services/lesson_qa.py`, which both the new `POST /api/admin/lessons/{id}/check` and the `check_draft.py` CLI call;
  - a migration adds `lessons.updated_at`/`updated_by`, stamped by every content write;
  - the PATCH takes an optional `expected_updated_at` and raises `LessonChangedError` (409 `lesson_changed`).
- **Frontend:**
  - `blocksToMdx`/`mdxParser` fix, proven by a failing round-trip suite;
  - one hook `useGuardedSave` and one dialog `SaveGate`, shared by the block editor and the MDX "Save as blocks".

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, Postgres; React 18 + TypeScript, openapi-fetch, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-05-lesson-editor-qa-design.md`. Read it first.

**Base:** implement on a branch from `main` **after PR #165 (B4) has merged**. B4 changed `ContentService.update_lesson` (lesson move via `module_id`) and `routers/admin_content.py`, and this plan builds on that code. Migration chain: `b0c1d2e3f4a5` (B4) → the new one here.

## Global Constraints

- Read `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`.
- **One database:** never `uv run poe dev`, never `alembic upgrade`. Integration tests use the remote test DB. Check `Test-NetConnection imaginemore-playground-pg.postgres.database.azure.com -Port 5432`, fall back to CI if it fails, and never run two pytest sessions at once.
- **The test harness never really commits** (savepoints). Force deferred constraints with `SET CONSTRAINTS … IMMEDIATE` when a test depends on them (B4 lesson).
- Router → service → repository; services never call services; FastAPI parameter annotations are runtime imports.
- Every `/api/admin/*` route declares exactly one guard from `core/dependencies/admin_scope.py` and has a `_MATRIX` row in `backend/tests/integration/test_routers/test_authz.py`.
- **Checks never block a save**; `info` findings alone never even open the panel.
- `expected_updated_at` is **optional** in this release (the deployed frontend doesn't send it).
- No `window.confirm`; in-app UI only.
- `backend/scripts/` is linted by the non-required ratcheting `staged` job: don't add findings there.
- Checks before every commit for the side you touched: backend `uv run poe format-check && uv run poe lint-src && uv run poe ty-src` + focused tests; frontend `npm run typecheck && npm run lint` + focused tests. Full suites at the end of Task 5 and in Task 7.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## Review Focus

1. **A paragraph whose line starts with `#`, `>` or a lone `*…*`** is inherently re-parsed as a heading, callout or kicker by MDX. Expect it to stay a documented limitation, not silently "fixed" by mangling text. The removal warning (Task 6) is the user's net. Pinned by `round-trips realistic text in every block type` (Task 1), which deliberately keeps such lines out, plus the doc comment.
2. **A 409 while the findings panel is open, or a second 409 after "Overwrite with mine"** (a third person saved). Expect the conflict panel to show again with the newest name and time, never a silent save. Test in Task 6 (`a second conflict after overwrite shows again`).
3. **`updated_at` precision across the wire:** the PATCH response's `updated_at` string, sent back verbatim, must match. Test in Task 4 (`test_saved_updated_at_round_trips_into_the_next_save`).
4. **A lesson whose `updated_by` user was deleted.** Expect a 409 with `updated_by_name: null` and the editor saying "Someone". Test in Task 4 (`test_conflict_names_nobody_when_the_editor_was_deleted`) and Task 6 (`names "Someone" when the editor is unknown`).
5. **The embedded editor in the Content-AI review pane** (`ContentImprovementPage.tsx`, `embedded`). It has no Save, and must neither call `/check` nor need `updatedAt`. Expect it unchanged. Test in Task 6 (`embedded editor never calls check`).

---

## File structure

| File | Responsibility |
|---|---|
| `frontend/src/lib/blocksToMdx.ts`, `frontend/src/lib/mdxParser.ts` (+ `frontend/src/lib/mdxRoundTrip.test.ts`) | #60 fix |
| Create `backend/src/services/lesson_qa.py` (+ `backend/tests/unit/test_lesson_qa.py`) | the checks |
| Modify `backend/scripts/content_qa/check_draft.py` | thin CLI over `lesson_qa` |
| Create `backend/alembic/versions/c1d2e3f4a5b6_lesson_updated_at.py` | the two columns |
| Modify `backend/src/db/models/learning.py` | `Lesson.updated_at`, `Lesson.updated_by` |
| Modify `backend/src/services/exceptions.py`, `backend/src/main.py` | `LessonChangedError` + 409 body |
| Modify `backend/src/services/content_service.py`, `content_improvement_service.py`, `learning_service.py` | stamping + conflict check |
| Modify `backend/src/schemas/admin_content.py`, `backend/src/schemas/learning.py`, `backend/src/routers/admin_content.py` | wire fields, `/check` |
| Create `frontend/src/lib/lessonSave.ts` (+ `.test.ts`) | pure: removal summary, conflict parsing |
| Create `frontend/src/components/lesson/useGuardedSave.ts`, `frontend/src/components/lesson/SaveGate.tsx` | the save flow + its dialog |
| Modify `frontend/src/components/lesson/LessonEditor.tsx` (+ test), `frontend/src/pages/LessonPage.tsx` (+ test) | wiring |

---

### Task 1: Prove and fix #60 (MDX round trip)

**Files:**
- Create: `frontend/src/lib/mdxRoundTrip.test.ts`
- Modify: `frontend/src/lib/blocksToMdx.ts`, `frontend/src/lib/mdxParser.ts`

**Interfaces:**
- Produces:
  - `blocksToMdx` emits `<Cards data="<base64>" />`, `<Quiz data="<base64>" />` and `<Question data="<base64>" />` (the whole block, via `encodeBlock`);
  - `parseMdxToBlocks` decodes those, still accepts the legacy `data='…json…'` and `` data={`…`} `` forms for Cards/Quiz, and keeps ids from the base64 forms.

- [ ] **Step 1: Write the failing round-trip suite**

```ts
// frontend/src/lib/mdxRoundTrip.test.ts
// #60: quiz/card blocks vanished from unrelated MDX edits. These pin the round
// trip blocksToMdx → parseMdxToBlocks for every block type with realistic text.
import { describe, expect, it } from 'vitest'
import type { ContentBlock } from '../types/contentBlocks'
import { blocksToMdx } from './blocksToMdx'
import { parseMdxToBlocks } from './mdxParser'

// Realistic, nasty inline text. Deliberately NO line starting with #, > or a
// lone *x*: MDX re-reads those as heading/callout/kicker (documented limit).
const T = `Don't "quote" me: a -> b, x < y, \`code\`, café 🙂`

const EVERY_TYPE: ContentBlock[] = [
  { id: 'h', type: 'heading', level: 2, text: T },
  { id: 'p', type: 'paragraph', text: `${T}\nsecond line, it's fine` },
  { id: 'c', type: 'callout', text: `${T}\nand another` },
  { id: 'k', type: 'kicker', text: `It's a kicker -> ok` },
  { id: 'cg', type: 'card_group', cards: [{ id: 'c1', title: T, body: T }] },
  { id: 'q', type: 'quiz', questions: [{ id: 'q1', q: T, options: [T, 'b'], correct: 1, explanation: T }] },
  { id: 'qs', type: 'question', prompt: T },
  { id: 'w', type: 'whitespace', size: 'lg' },
  { id: 'is', type: 'interactive', mode: 'sort', prompt: T, buckets: [{ id: 'b1', label: T }], items: [{ id: 'i1', text: T, bucketId: 'b1', reason: T }] },
  { id: 'tiy', type: 'try_it_yourself', task: T, material: T, steps: [{ id: 's1', label: T, text: T }], whatToNotice: T },
  { id: 'img', type: 'image', blob_path: 'lessons/x.png', alt: T, caption: T },
  { id: 'v', type: 'video', source: 'embed', url: 'https://www.youtube.com/embed/abc' },
] as ContentBlock[]

const withoutIds = (blocks: ContentBlock[]) =>
  JSON.parse(JSON.stringify(blocks, (key, value) => (key === 'id' ? undefined : value)))

describe('MDX round trip (#60)', () => {
  it('round-trips realistic text in every block type', () => {
    expect(withoutIds(parseMdxToBlocks(blocksToMdx(EVERY_TYPE)))).toEqual(withoutIds(EVERY_TYPE))
  })

  it('keeps quiz, card and question ids', () => {
    const out = parseMdxToBlocks(blocksToMdx(EVERY_TYPE))
    expect(out.find(b => b.type === 'quiz')?.id).toBe('q')
    expect(out.find(b => b.type === 'card_group')?.id).toBe('cg')
    expect(out.find(b => b.type === 'question')?.id).toBe('qs')
  })

  it('covers every block type in the union', () => {
    // Fails when a type is added to contentBlocks.ts without round-trip coverage.
    const covered = new Set(EVERY_TYPE.map(b => b.type))
    const all: ContentBlock['type'][] = [
      'heading', 'paragraph', 'callout', 'kicker', 'card_group', 'quiz', 'question',
      'whitespace', 'interactive', 'try_it_yourself', 'image', 'video',
    ]
    expect([...covered].sort()).toEqual([...all].sort())
  })

  it('still reads the legacy single-quoted Cards and Quiz forms', () => {
    const legacy = `<Quiz data='[{"id":"x","q":"Q","options":["a","b"],"correct":0,"explanation":"e"}]' />`
    expect(parseMdxToBlocks(legacy).map(b => b.type)).toEqual(['quiz'])
  })
})
```

Before running: open `frontend/src/types/contentBlocks.ts` and compare every union member and field name against `EVERY_TYPE` (`interactive` has three modes; one is enough for coverage, because all three share the same encoding path). Fix the fixture, not the types. If `ContentBlock['type']` has a member missing from the `all` list, add it to both lists.

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/lib/mdxRoundTrip.test.ts`
Expected: FAIL. `round-trips…` loses the quiz, card_group and question blocks; `keeps … ids` fails. That's the #60 proof. Record the actual diff in the ledger.

- [ ] **Step 3: Fix the encoder**

In `blocksToMdx.ts`, replace three cases and update the header comment:

```ts
        case 'card_group':
          return `<Cards data="${encodeBlock(block)}" />`

        case 'quiz':
          return `<Quiz data="${encodeBlock(block)}" />`
```

```ts
        case 'question':
          return `<Question data="${encodeBlock(block)}" />`
```

Header "Known limitations": delete the `card_group / quiz` raw-JSON bullet and the `question` "dropped" bullet. Add:
- card_group / quiz / question are base64-encoded like interactive (#60: the old raw-JSON-in-single-quotes form was truncated by the first apostrophe);
- a paragraph or callout *line* starting with `#`, `>` or a lone `*…*` re-parses as a heading, callout or kicker. This is inherent to MDX, and the editor warns before a save that removes blocks.

- [ ] **Step 4: Fix the parser**

In `mdxParser.ts`:

```ts
import type {
  CardGroupBlock, ContentBlock, ImageBlock, InteractiveBlock, QuestionBlock, QuizBlock,
  TryItYourselfBlock, VideoBlock,
} from '../types/contentBlocks'
```

Splitter: include `Question`. A base64 payload has no `>`, so `[^>]*?` is safe for the new forms. The legacy JSON forms can contain `>`, so match a quoted attribute value as a unit:

```ts
  const segments = mdx.split(
    /(<(?:Cards|Quiz|Question|Spacer|Interactive|TryItYourself|Image|Video)\s(?:[^>"'`]|"[^"]*"|'[^']*'|\{`[^`]*`\})*?\/>)/g,
  )
```

Before the legacy `cardsMatch`/`quizMatch`, decode the new form:

```ts
    const encoded = seg.match(/^<(Cards|Quiz|Question)\s+data="([^"]*)"/)
    if (encoded) {
      try {
        blocks.push(decodeBlock<CardGroupBlock | QuizBlock | QuestionBlock>(encoded[2]))
      } catch {
        // malformed payload — skip
      }
      continue
    }
```

Keep the legacy `data='…'` / `` data={`…`} `` matches after it, unchanged (they still mint fresh ids via `createCardGroup`/`createQuiz`). Update the doc comment's "Handles" list. If `CardGroupBlock`/`QuizBlock` aren't exported under those names, use the names `contentBlocks.ts` exports.

- [ ] **Step 5: Run to verify it passes, plus the existing parser and editor tests**

Run: `cd frontend && npx vitest run src/lib/mdxRoundTrip.test.ts src/lib src/pages/LessonPage.test.tsx`
Expected: PASS. If an existing `mdxParser`/`blocksToMdx` test asserted the old quote form, update it to the new form and record a ruling.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib
git commit -m "fix(editor): MDX round trip no longer drops quiz, card and question blocks (#60)"
```

---

### Task 2: `lesson_qa` module; `check_draft.py` becomes its CLI

**Files:**
- Create: `backend/src/services/lesson_qa.py`
- Modify: `backend/scripts/content_qa/check_draft.py`
- Test: `backend/tests/unit/test_lesson_qa.py`

**Interfaces:**
- Produces:
  - `check_blocks(blocks: list[Any]) -> tuple[list[str], list[str], list[str]]`: exactly the script's `(fails, warns, expected)` strings;
  - `Finding` (frozen dataclass: `severity: Literal["warning", "info"]`, `block_index: int | None`, `where: str`, `message: str`);
  - `check_lesson(blocks: list[Any]) -> list[Finding]`;
  - `text_fields(obj, path="") -> list[tuple[str, str]]`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_lesson_qa.py
"""The in-app house-style checks (B5) = check_draft.py's checks, one module."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from src.services.lesson_qa import Finding, check_blocks, check_lesson


def _quiz(correct: list[int], options: list[list[str]] | None = None) -> dict:
    opts = options or [["aa", "bb"] for _ in correct]
    return {
        "id": "quiz",
        "type": "quiz",
        "questions": [
            {"id": f"q{i}", "q": "Q?", "options": o, "correct": c, "explanation": "e"}
            for i, (c, o) in enumerate(zip(correct, opts, strict=True))
        ],
    }


HEADING = {"id": "h", "type": "heading", "level": 2, "text": "Check your understanding"}


def test_a_clean_lesson_has_no_findings() -> None:
    blocks = [
        {"id": "p", "type": "paragraph", "text": "Plain **one** text."},
        HEADING,
        _quiz([0, 1]),
    ]
    assert check_lesson(blocks) == []


@pytest.mark.parametrize(("char", "name"), [("—", "em dash"), ("–", "en dash"), ("…", "ellipsis")])
def test_forbidden_punctuation_names_the_block(char: str, name: str) -> None:
    findings = check_lesson([{"id": "p", "type": "paragraph", "text": f"a {char} b"}])
    assert findings == [
        Finding("warning", 0, "block 1 · paragraph", f"{name} in [0].text")
    ]


def test_duplicate_ids() -> None:
    blocks = [{"id": "x", "type": "paragraph", "text": "a"}, {"id": "x", "type": "paragraph", "text": "b"}]
    assert any("duplicate ids" in f.message for f in check_lesson(blocks))


def test_quiz_rules() -> None:
    blocks = [_quiz([0, 0], [["long answer", "b"], ["long answer", "b"]])]
    messages = [f.message for f in check_lesson(blocks)]
    assert any("not preceded by a 'Check your understanding' heading" in m for m in messages)
    assert any("correct position never varies" in m for m in messages)
    assert any("correct is the unique longest option" in m for m in messages)


def test_more_than_two_bold_spans_is_a_warning() -> None:
    blocks = [{"id": "p", "type": "paragraph", "text": "**a** **b** **c**"}]
    assert [f.severity for f in check_lesson(blocks)] == ["warning"]


def test_an_empty_image_blob_path_is_info() -> None:
    blocks = [{"id": "i", "type": "image", "blob_path": "", "alt": "x"}]
    findings = check_lesson(blocks)
    assert findings and all(f.severity == "info" for f in findings)


def test_unresolved_sort_and_predict_references() -> None:
    blocks = [
        {"id": "s", "type": "interactive", "mode": "sort", "prompt": "p",
         "buckets": [{"id": "b1", "label": "B"}],
         "items": [{"id": "i1", "text": "t", "bucketId": "nope", "reason": "r"}]},
        {"id": "pr", "type": "interactive", "mode": "predict", "prompt": "p",
         "options": [{"id": "o1", "label": "L", "reason": "r"}], "correctOptionId": "zz"},
    ]
    messages = [f.message for f in check_lesson(blocks)]
    assert any("unresolved bucketId" in m for m in messages)
    assert any("correctOptionId does not resolve" in m for m in messages)


def test_the_cli_reports_the_same_failures() -> None:
    """Parity: check_draft.py is a thin CLI over check_blocks."""
    path = Path(__file__).resolve().parents[2] / "scripts" / "content_qa" / "check_draft.py"
    spec = importlib.util.spec_from_file_location("check_draft", path)
    assert spec and spec.loader
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    blocks = [{"id": "p", "type": "paragraph", "text": "a — b"}, _quiz([0, 0])]
    assert cli.check({"content_blocks": blocks}) == check_blocks(blocks)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_lesson_qa.py -v`
Expected: FAIL with `ModuleNotFoundError: src.services.lesson_qa`.

- [ ] **Step 3: Write `lesson_qa.py`**

Move the script's constants (`FORBIDDEN`, `BOLD`, `BULLET_LEAD_IN`, `SKIP_KEYS`, `EMPTY_BLOB`) and the functions `text_fields`, `collect_ids`, `bold_count` and `check` into it verbatim. Then:
- rename `check(lesson)` to `check_blocks(blocks)`, taking the blocks list directly;
- type the helpers (`obj: Any`, `blocks: list[Any]`);
- import `check_house_style` and `validate_content_blocks` from `src.services.content_blocks_validation`.

Add:

```python
_BLOCK = re.compile(r"^(?:block)?\[(\d+)\]")


@dataclass(frozen=True)
class Finding:
    """One house-style finding, located for the editor ("block 4 · paragraph")."""

    severity: Literal["warning", "info"]
    block_index: int | None
    where: str
    message: str


def _locate(message: str, blocks: list[Any]) -> tuple[int | None, str]:
    """Messages name a block as `block[3]…` or a text path as `[3].text`."""
    head = message.split(" in ", 1)[-1] if " in [" in message else message
    match = _BLOCK.match(head)
    if match is None:
        return None, "lesson"
    index = int(match.group(1))
    block_type = blocks[index].get("type", "block") if index < len(blocks) else "block"
    return index, f"block {index + 1} · {block_type}"


def check_lesson(blocks: list[Any]) -> list[Finding]:
    """check_blocks, as located findings. The script's fails and warns are
    warnings (never a block on save: most live lessons predate the nested-id
    rule); its EXPECTED bucket (an empty image blob_path) is info."""
    fails, warns, expected = check_blocks(blocks)
    findings = []
    for severity, messages in (("warning", fails + warns), ("info", expected)):
        for message in messages:
            index, where = _locate(message, blocks)
            findings.append(Finding(severity, index, where, message))
    return findings
```

`__all__ = ["Finding", "check_blocks", "check_lesson", "text_fields"]`. The module docstring cites `docs/content/authoring-guide.md` §11 and says `scripts/content_qa/check_draft.py` is its CLI. The parametrized test pins `where` = `block 1 · paragraph` for a paragraph at index 0 (message `em dash in [0].text`). Adjust `_locate` until it holds.

- [ ] **Step 4: Rewire the CLI**

In `check_draft.py`:
- delete the moved constants and functions;
- change the path line to `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # .../backend`;
- import `from src.services.lesson_qa import check_blocks, text_fields  # noqa: E402`;
- keep `to_uuids` and `main` unchanged, with this shim:

```python
def check(lesson) -> tuple[list[str], list[str], list[str]]:
    """The script's historical entry point; the checks live in src/services/lesson_qa.py."""
    return check_blocks(lesson["content_blocks"])
```

Update the module docstring: "The checks live in `src/services/lesson_qa.py`, shared with the in-app Check (B5)."

- [ ] **Step 5: Run the tests and the CLI**

Run: `cd backend && uv run pytest tests/unit/test_lesson_qa.py -v`
Expected: PASS.

Run: `cd backend && echo '[{"sort_order":1,"title":"T","content_blocks":[{"id":"p","type":"paragraph","text":"a — b"}]}]' > /tmp/draft.json && uv run python scripts/content_qa/check_draft.py /tmp/draft.json`
Expected: a `FAIL L1 T` line with `em dash in [0].text`, and exit 1.

Run: `cd backend && uv run ruff check scripts/content_qa/check_draft.py --statistics`, then the same on the `main` version (`git show main:backend/scripts/content_qa/check_draft.py > <scratch>/old_check_draft.py`, then `uv run ruff check <scratch>/old_check_draft.py --statistics`).
Expected: the new file has no more findings than the old one (the `staged` CI job ratchets on this).

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/lesson_qa.py backend/scripts/content_qa/check_draft.py backend/tests/unit/test_lesson_qa.py
git commit -m "feat(content): in-app house-style checks module; check_draft.py is its CLI (B5, #146)"
```

---

### Task 3: Migration and model: `lessons.updated_at`, `lessons.updated_by`

**Files:**
- Create: `backend/alembic/versions/c1d2e3f4a5b6_lesson_updated_at.py`
- Modify: `backend/src/db/models/learning.py` (`Lesson`)
- Test: `backend/tests/integration/test_models/test_lesson_updated_at.py`

**Interfaces:**
- Produces:
  - `Lesson.updated_at: Mapped[datetime]` (NOT NULL, server default `now()`);
  - `Lesson.updated_by: Mapped[uuid.UUID | None]` (FK `users.id` `ON DELETE SET NULL`, indexed);
  - revision `c1d2e3f4a5b6` revising `b0c1d2e3f4a5`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_models/test_lesson_updated_at.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from src.db.models import Lesson, User
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_a_new_lesson_gets_updated_at_and_no_editor(db_session: AsyncSession) -> None:
    module = await create_module(db_session, await create_track(db_session))
    lesson = await create_lesson(db_session, module)
    assert lesson.updated_at is not None
    assert lesson.updated_by is None


async def test_deleting_the_editor_keeps_the_lesson(db_session: AsyncSession) -> None:
    module = await create_module(db_session, await create_track(db_session))
    lesson = await create_lesson(db_session, module)
    editor = await create_user(db_session, email="b5-editor@example.com", role="admin")
    lesson.updated_by = editor.id
    await db_session.commit()

    await db_session.execute(delete(User).where(User.id == editor.id))
    await db_session.commit()

    refreshed = (await db_session.execute(select(Lesson).where(Lesson.id == lesson.id))).scalar_one()
    await db_session.refresh(refreshed)
    assert refreshed.updated_by is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_models/test_lesson_updated_at.py -v -p no:randomly`
Expected: FAIL (`AttributeError: … has no attribute 'updated_at'` or similar).

- [ ] **Step 3: Add the model columns**

In `Lesson`, after `created_at`:

```python
    # B5 (spec 2026-10-05-lesson-editor-qa): the editor's conflict check. Stamped
    # by every content write (admin PATCH, AI-proposal approval), not by a
    # reorder. updated_by is the admin who saved; NULL when unknown or deleted.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
```

Use the imports the file already has (`ForeignKey`, `UUID` from `sqlalchemy.dialects.postgresql`; check the top of the file).

- [ ] **Step 4: Write the migration**

```python
# backend/alembic/versions/c1d2e3f4a5b6_lesson_updated_at.py
"""lessons.updated_at + lessons.updated_by (B5)

Spec: docs/superpowers/specs/2026-10-05-lesson-editor-qa-design.md. The lesson
editor's conflict check: a PATCH carrying an outdated updated_at is refused.

updated_at is added with server default now(), then backfilled to created_at
so existing lessons read as "unchanged since creation". updated_by is NULL for
every existing row (unknown).

Expand-first: the running image never reads or writes these columns, and the
server default fills updated_at on its inserts.

Downgrade drops both.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute("UPDATE lessons SET updated_at = created_at")
    op.add_column(
        "lessons",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_lessons_updated_by_users"),
        "lessons",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_lessons_updated_by"), "lessons", ["updated_by"])


def downgrade() -> None:
    op.drop_index(op.f("ix_lessons_updated_by"), table_name="lessons")
    op.drop_constraint(op.f("fk_lessons_updated_by_users"), "lessons", type_="foreignkey")
    op.drop_column("lessons", "updated_by")
    op.drop_column("lessons", "updated_at")
```

Check `lessons.created_at`'s nullability in the model before relying on the backfill. If it's nullable, use `UPDATE lessons SET updated_at = COALESCE(created_at, now())`. Also match the constraint and index names to the project's naming convention (`grep -n "naming_convention" backend/src/db/base.py`); `alembic check` in CI fails on a mismatch.

- [ ] **Step 5: Run the tests and the integration suite**

Run: `cd backend && uv run pytest tests/integration/test_models/test_lesson_updated_at.py -v -p no:randomly && uv run alembic heads`
Expected: PASS, and `c1d2e3f4a5b6 (head)`.

Run: `cd backend && uv run pytest tests/integration -q -n auto`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/c1d2e3f4a5b6_lesson_updated_at.py backend/src/db/models/learning.py backend/tests/integration/test_models/test_lesson_updated_at.py
git commit -m "feat(content): lessons.updated_at + updated_by (B5, #146)"
```

---

### Task 4: Conflict-safe lesson save + stamping everywhere

**Files:**
- Modify: `backend/src/services/exceptions.py`, `backend/src/main.py`
- Modify: `backend/src/services/content_service.py` (`update_lesson`)
- Modify: `backend/src/services/content_improvement_service.py` (`_apply`)
- Modify: `backend/src/services/learning_service.py` (lesson detail payload)
- Modify: `backend/src/schemas/admin_content.py` (`LessonUpdateRequest`, `LessonOut`), `backend/src/schemas/learning.py` (`LessonDetailResponse`)
- Modify: `backend/src/routers/admin_content.py` (`update_lesson`)
- Test: `backend/tests/unit/test_lesson_conflict.py`, `backend/tests/integration/test_routers/test_lesson_conflict.py`

**Interfaces:**
- Consumes: Task 3 columns.
- Produces:
  - `LessonChangedError(updated_at: datetime, updated_by_name: str | None)` (a `ConflictError`), rendered as 409 `{"error": {"code": "lesson_changed", "message", "updated_at": <iso>, "updated_by_name": <str|null>}}`;
  - `ContentService.update_lesson(lesson_id, values, *, actor_id: uuid.UUID | None = None)`, where `values` may contain `expected_updated_at: datetime`;
  - `LessonUpdateRequest.expected_updated_at: datetime | None`;
  - `LessonOut.updated_at: datetime`;
  - `LessonDetailResponse.updated_at: datetime`.

- [ ] **Step 1: Write the failing unit tests**

```python
# backend/tests/unit/test_lesson_conflict.py
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractContentRepository,
    AbstractProjectAdminRepository,
    AbstractUserRepository,
)
from src.services.content_service import ContentService
from src.services.exceptions import LessonChangedError

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)  # safely in the past: the stamp must be later


def _service(lesson: SimpleNamespace) -> tuple[ContentService, AsyncMock, AsyncMock]:
    content = AsyncMock(spec=AbstractContentRepository)
    content.get_lesson.return_value = lesson
    content.update_lesson.side_effect = lambda le, values: le
    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_id.return_value = SimpleNamespace(first_name="Aaron", last_name="Neuville")
    service = ContentService(
        content,
        assignments=AsyncMock(spec=AbstractAssignmentRepository),
        users=users,
        project_admins=AsyncMock(spec=AbstractProjectAdminRepository),
    )
    return service, content, users


def _lesson(**kw: object) -> SimpleNamespace:
    return SimpleNamespace(**({"id": uuid.uuid4(), "module_id": uuid.uuid4(),
                               "updated_at": T0, "updated_by": uuid.uuid4()} | kw))


async def test_a_stale_expected_updated_at_is_refused_with_who_and_when() -> None:
    lesson = _lesson()
    service, content, _ = _service(lesson)

    with pytest.raises(LessonChangedError) as caught:
        await service.update_lesson(
            lesson.id, {"title": "x", "expected_updated_at": T0 - timedelta(seconds=1)},
            actor_id=uuid.uuid4(),
        )

    assert caught.value.updated_at == T0
    assert caught.value.updated_by_name == "Aaron Neuville"
    content.update_lesson.assert_not_awaited()


async def test_a_fresh_save_stamps_time_and_editor() -> None:
    lesson = _lesson()
    service, content, _ = _service(lesson)
    actor = uuid.uuid4()

    await service.update_lesson(lesson.id, {"title": "x", "expected_updated_at": T0}, actor_id=actor)

    _, values = content.update_lesson.await_args.args
    assert values["title"] == "x"
    assert values["updated_by"] == actor
    assert values["updated_at"] > T0
    assert "expected_updated_at" not in values


async def test_an_omitted_expected_updated_at_still_saves() -> None:
    lesson = _lesson()
    service, content, _ = _service(lesson)
    await service.update_lesson(lesson.id, {"title": "x"}, actor_id=None)
    content.update_lesson.assert_awaited_once()


async def test_conflict_names_nobody_when_the_editor_was_deleted() -> None:
    lesson = _lesson(updated_by=None)
    service, _, _ = _service(lesson)
    with pytest.raises(LessonChangedError) as caught:
        await service.update_lesson(
            lesson.id, {"expected_updated_at": T0 - timedelta(seconds=1)}, actor_id=None
        )
    assert caught.value.updated_by_name is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_lesson_conflict.py -v`
Expected: FAIL with `ImportError: LessonChangedError`.

- [ ] **Step 3: The error and its 409 body**

`exceptions.py`, after `ConflictError` (add it to `__all__` if the module has one):

```python
class LessonChangedError(ConflictError):
    """A lesson save carried an outdated `expected_updated_at` (B5). → 409
    `lesson_changed`, with who changed it and when, so the editor can offer
    Reload or Overwrite."""

    def __init__(self, updated_at: datetime, updated_by_name: str | None) -> None:
        super().__init__("This lesson was changed by someone else while you were editing.")
        self.updated_at = updated_at
        self.updated_by_name = updated_by_name
```

(`from datetime import datetime` at the top, as a runtime import.)

`main.py`: import `LessonChangedError` and register this handler **above** `conflict_handler`:

```python
@app.exception_handler(LessonChangedError)
async def lesson_changed_handler(request: Request, exc: LessonChangedError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "lesson_changed",
                "message": exc.message,
                "updated_at": exc.updated_at.isoformat(),
                "updated_by_name": exc.updated_by_name,
            }
        },
    )
```

Starlette picks the most specific registered class along the exception's MRO, so the order is only for readers.

- [ ] **Step 4: The service**

At the top of `ContentService.update_lesson` (after the `lesson is None` check), replace B4's opening lines up to `if not values: return lesson` with:

```python
        values = dict(values)
        expected = values.pop("expected_updated_at", None)
        if expected is not None and expected != lesson.updated_at:
            editor = (
                await self._users.get_by_id(lesson.updated_by) if lesson.updated_by else None
            )
            name = f"{editor.first_name} {editor.last_name}".strip() if editor else None
            raise LessonChangedError(lesson.updated_at, name or None)
        stamp = {"updated_at": datetime.now(UTC), "updated_by": actor_id}
        module_id = values.pop("module_id", None)
        if module_id is not None and module_id != lesson.module_id:
            if await self._content.get_module(module_id) is None:
                raise NotFoundError("Module")
            lesson = await self._content.move_lesson(lesson, module_id)
        if not values:
            return await self._content.update_lesson(lesson, stamp) if module_id else lesson
```

At its end: `return await self._content.update_lesson(lesson, {**values, **stamp})`.

Change the signature to `async def update_lesson(self, lesson_id, values, *, actor_id: uuid.UUID | None = None) -> Lesson`, and add `from datetime import UTC, datetime` and `LessonChangedError` to the imports. The moved-only branch stamps, as the spec requires ("B4's move" stamps). Reorder (`set_lesson_orders`) is untouched, so it never stamps.

- [ ] **Step 5: Stamp the AI-proposal approval**

In `content_improvement_service.py` `_apply`, the `stage_lesson_update` call becomes:

```python
        await self._content.stage_lesson_update(
            lesson,
            {
                "content_blocks": strip_ephemeral(list(blocks)),
                "updated_at": datetime.now(UTC),
                "updated_by": reviewer_id,
            },
        )
```

Add the datetime import if missing. Extend its existing unit test (`tests/unit/test_content_improvement_service.py`, the approve-path test) to assert the two stamp keys reach `stage_lesson_update`.

- [ ] **Step 6: The wire**

- `LessonUpdateRequest`: `expected_updated_at: datetime | None = None` (`from datetime import datetime`).
- `LessonOut`: `updated_at: datetime`.
- `LessonDetailResponse`: `updated_at: datetime`, and `learning_service.py`'s detail payload adds `"updated_at": lesson.updated_at`.
- Router `update_lesson`:
  - replace `dependencies=[Depends(require_power_admin)]` with a parameter `actor: PowerAdminDep` (import `PowerAdminDep` from `admin_scope`; it's still the one guard);
  - call `content_service.update_lesson(lesson_id, body.model_dump(exclude_unset=True), actor_id=actor.id)`;
  - add `updated_at=lesson.updated_at` to the stamped `LessonOut(...)`.

- [ ] **Step 7: Integration tests**

```python
# backend/tests/integration/test_routers/test_lesson_conflict.py
"""No silent overwrites (B5): PATCH /api/admin/lessons/{id} with expected_updated_at."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def _setup(db_session: AsyncSession):  # noqa: ANN202
    a = await create_user(db_session, email="b5-a@example.com", role="admin", first_name="Ann", last_name="Admin")
    b = await create_user(db_session, email="b5-b@example.com", role="admin", first_name="Bob", last_name="Boss")
    lesson = await create_lesson(db_session, await create_module(db_session, await create_track(db_session)))
    return a, b, lesson


async def test_a_save_from_an_outdated_copy_is_409_with_who_and_when(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, b, lesson = await _setup(db_session)
    base = (await client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(a, test_settings))).json()["updated_at"]

    first = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "Bob's edit", "expected_updated_at": base},
        headers=auth_headers(b, test_settings),
    )
    assert first.status_code == 200

    stale = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "Ann's edit", "expected_updated_at": base},
        headers=auth_headers(a, test_settings),
    )
    assert stale.status_code == 409
    error = stale.json()["error"]
    assert error["code"] == "lesson_changed"
    assert error["updated_by_name"] == "Bob Boss"
    assert error["updated_at"] == first.json()["updated_at"]


async def test_saved_updated_at_round_trips_into_the_next_save(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, _, lesson = await _setup(db_session)
    headers = auth_headers(a, test_settings)
    base = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()["updated_at"]
    one = await client.patch(f"/api/admin/lessons/{lesson.id}", json={"title": "One", "expected_updated_at": base}, headers=headers)
    two = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "Two", "expected_updated_at": one.json()["updated_at"]},
        headers=headers,
    )
    assert two.status_code == 200


async def test_an_omitted_expected_updated_at_still_saves(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, _, lesson = await _setup(db_session)
    response = await client.patch(
        f"/api/admin/lessons/{lesson.id}", json={"title": "Old client"}, headers=auth_headers(a, test_settings)
    )
    assert response.status_code == 200


async def test_a_reorder_does_not_stamp(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, _, lesson = await _setup(db_session)
    headers = auth_headers(a, test_settings)
    before = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()["updated_at"]
    await client.put(
        f"/api/admin/modules/{lesson.module_id}/lessons/order",
        json={"lesson_ids": [str(lesson.id)]},
        headers=headers,
    )
    after = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()["updated_at"]
    assert after == before
```

`GET /api/lessons/{id}` for a power admin bypasses the access gate (`LOCK_BYPASS_ROLES`), so no assignment is needed. If the gate refuses (component locked for a project-less admin), unlock it through `unlock_component` in factories, as other lesson router tests do.

- [ ] **Step 8: Run**

Run: `cd backend && uv run pytest tests/unit/test_lesson_conflict.py tests/unit/test_content_improvement_service.py tests/integration/test_routers/test_lesson_conflict.py tests/integration/test_routers/test_admin_content.py tests/integration/test_routers/test_learning.py -v -p no:randomly`
Expected: PASS.

Run: `cd backend && uv run poe format && uv run poe lint-src && uv run poe ty-src`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(content): refuse lesson saves from an outdated copy (409 lesson_changed) (B5, #146)"
```

---

### Task 5: `POST /api/admin/lessons/{id}/check`

**Files:**
- Modify: `backend/src/schemas/admin_content.py`, `backend/src/services/content_service.py`, `backend/src/routers/admin_content.py`
- Modify: `backend/tests/integration/test_routers/test_authz.py` (`_MATRIX`)
- Test: `backend/tests/integration/test_routers/test_lesson_check.py`

**Interfaces:**
- Consumes: Task 2 `check_lesson`, `Finding`.
- Produces:
  - `LessonCheckRequest{content_blocks: list[dict[str, Any]]}`;
  - `LessonFindingOut{severity: Literal["warning","info"], block_index: int | None, where: str, message: str}`;
  - `LessonCheckResponse{findings: list[LessonFindingOut]}`;
  - `ContentService.check_lesson(lesson_id, blocks) -> list[Finding]` (404 unknown lesson; writes nothing);
  - route `POST /api/admin/lessons/{lesson_id}/check`.

- [ ] **Step 1: Write the failing tests and the matrix row**

```python
# backend/tests/integration/test_routers/test_lesson_check.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_check_returns_located_findings_and_writes_nothing(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b5-check@example.com", role="admin")
    lesson = await create_lesson(db_session, await create_module(db_session, await create_track(db_session)))
    headers = auth_headers(power, test_settings)
    before = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()

    response = await client.post(
        f"/api/admin/lessons/{lesson.id}/check",
        json={"content_blocks": [{"id": "p", "type": "paragraph", "text": "a — b"}]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["findings"] == [
        {"severity": "warning", "block_index": 0, "where": "block 1 · paragraph", "message": "em dash in [0].text"}
    ]
    after = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()
    assert after["content_blocks"] == before["content_blocks"]
    assert after["updated_at"] == before["updated_at"]


async def test_check_on_an_unknown_lesson_is_404(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b5-check404@example.com", role="admin")
    response = await client.post(
        f"/api/admin/lessons/{uuid.uuid4()}/check",
        json={"content_blocks": []},
        headers=auth_headers(power, test_settings),
    )
    assert response.status_code == 404
```

`_MATRIX` row (beside the other lesson rows):

```python
    ("lesson-check", "POST", "/api/admin/lessons/{lesson_id}/check",
     lambda s: f"/api/admin/lessons/{s.lesson.id}/check",
     lambda s: {"content_blocks": []}, "power"),
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_lesson_check.py -v -p no:randomly`
Expected: FAIL (404/405 on the missing route).

- [ ] **Step 3: Implement**

Schemas: add the three models above to `admin_content.py` (`LessonFindingOut` with `model_config = ConfigDict(from_attributes=True)`) and to `__all__`.

Service:

```python
    async def check_lesson(self, lesson_id: uuid.UUID, blocks: list[Any]) -> list[Finding]:
        """The house-style checks on unsaved blocks (B5). Read-only."""
        if await self._content.get_lesson(lesson_id) is None:
            raise NotFoundError("Lesson")
        return check_lesson(blocks)
```

Add `from src.services.lesson_qa import Finding, check_lesson`. That's a pure module, not a service.

Router:

```python
@router.post(
    "/admin/lessons/{lesson_id}/check",
    response_model=LessonCheckResponse,
    dependencies=[Depends(require_power_admin)],
)
async def check_lesson(
    lesson_id: uuid.UUID, body: LessonCheckRequest, content_service: ContentServiceDep
) -> LessonCheckResponse:
    """House-style findings for the editor's unsaved blocks; writes nothing.
    Warnings never block a save (spec 2026-10-05-lesson-editor-qa)."""
    findings = await content_service.check_lesson(lesson_id, body.content_blocks)
    return LessonCheckResponse(findings=[LessonFindingOut.model_validate(f) for f in findings])
```

- [ ] **Step 4: Run, then the full backend suite (checkpoint)**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_lesson_check.py tests/integration/test_routers/test_authz.py -q -p no:randomly`
Expected: PASS.

Run: `cd backend && uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`
Expected: green; coverage ≥ 90%.

- [ ] **Step 5: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(content): POST /api/admin/lessons/{id}/check (B5, #146)"
```

---

### Task 6: The editor's guarded save (checks gate, conflict prompt, removal warning)

**Files:**
- Modify: `frontend/src/api/schema.d.ts` (generated)
- Create: `frontend/src/lib/lessonSave.ts`, `frontend/src/lib/lessonSave.test.ts`
- Create: `frontend/src/components/lesson/useGuardedSave.ts`, `frontend/src/components/lesson/SaveGate.tsx`
- Modify: `frontend/src/components/lesson/LessonEditor.tsx` (+ `LessonEditor.test.tsx`)
- Modify: `frontend/src/pages/LessonPage.tsx` (+ `LessonPage.test.tsx`)

**Interfaces:**
- Consumes: Tasks 4–5 HTTP contract.
- Produces:
  - `lib/lessonSave.ts`:
    - `removalSummary(before: ContentBlock[], after: ContentBlock[]): string | null`, e.g. "This removes 1 quiz and 1 card group.";
    - `parseConflict(error: unknown): { updatedAt: string; updatedByName: string | null } | null`;
    - `type Finding = components['schemas']['LessonFindingOut']`.
  - `useGuardedSave({ lessonId, baseUpdatedAt, onSaved, onReload })` returns `{ gate, save(payload, opts?), check(blocks), saveAnyway(), keepEditing(), overwrite(), reload() }`, where:
    - `payload = { title?: string; content_blocks: ContentBlock[] }` and `opts = { before?: ContentBlock[] }`;
    - `onSaved(data: LessonOut)`;
    - `gate` is `{ kind: 'idle' } | { kind: 'busy' } | { kind: 'findings'; findings: Finding[]; removal: string | null; checkOnly: boolean } | { kind: 'conflict'; updatedAt: string; updatedByName: string | null } | { kind: 'error'; message: string }`.
  - `<SaveGate gate={…} onSaveAnyway onKeepEditing onReload onOverwrite />`, which renders nothing for `idle`/`busy`.
  - `LessonEditor` props gain `updatedAt?: string | null` and `onReload?: () => void`; `EditedLesson` gains `updated_at?: string`.

- [ ] **Step 1: Regenerate the API types**

Run: `cd frontend && npm run gen:api`
Expected: `schema.d.ts` gains `/check`, `LessonFindingOut`, `expected_updated_at`, and `updated_at` on `LessonOut` and `LessonDetailResponse`.

- [ ] **Step 2: Write the failing pure-helper tests**

```ts
// frontend/src/lib/lessonSave.test.ts
import { describe, expect, it } from 'vitest'
import type { ContentBlock } from '../types/contentBlocks'
import { parseConflict, removalSummary } from './lessonSave'

const b = (type: string, id: string) => ({ id, type }) as unknown as ContentBlock

describe('removalSummary', () => {
  it('names what a save would remove', () => {
    const before = [b('quiz', '1'), b('card_group', '2'), b('paragraph', '3')]
    const after = [b('paragraph', '3')]
    expect(removalSummary(before, after)).toBe('This removes 1 quiz and 1 card group.')
  })
  it('is null when nothing is lost (additions and reorders are fine)', () => {
    expect(removalSummary([b('quiz', '1')], [b('paragraph', '9'), b('quiz', '1')])).toBeNull()
  })
  it('counts per type, plural', () => {
    expect(removalSummary([b('paragraph', '1'), b('paragraph', '2')], [])).toBe('This removes 2 paragraphs.')
  })
})

describe('parseConflict', () => {
  it('reads a lesson_changed 409 body', () => {
    expect(parseConflict({ error: { code: 'lesson_changed', message: 'm', updated_at: '2026-10-05T14:32:00+00:00', updated_by_name: 'Aaron Neuville' } }))
      .toEqual({ updatedAt: '2026-10-05T14:32:00+00:00', updatedByName: 'Aaron Neuville' })
  })
  it('ignores any other error', () => {
    expect(parseConflict({ error: { code: 'conflict', message: 'm' } })).toBeNull()
    expect(parseConflict(undefined)).toBeNull()
  })
})
```

Run: `cd frontend && npx vitest run src/lib/lessonSave.test.ts`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `lib/lessonSave.ts`**

```ts
// frontend/src/lib/lessonSave.ts
// Pure helpers for the lesson editor's guarded save (B5, spec 2026-10-05).
import type { components } from '../api/schema'
import { BLOCK_LABELS } from './contentBlocks'
import type { ContentBlock } from '../types/contentBlocks'

export type Finding = components['schemas']['LessonFindingOut']

/** "This removes 1 quiz and 1 card group." when `after` has fewer blocks of
 * some type than `before`; null when nothing is lost. The #60 safety net. */
export function removalSummary(before: ContentBlock[], after: ContentBlock[]): string | null {
  const count = (blocks: ContentBlock[]) =>
    blocks.reduce<Record<string, number>>((acc, block) => ({ ...acc, [block.type]: (acc[block.type] ?? 0) + 1 }), {})
  const was = count(before)
  const now = count(after)
  const lost = Object.entries(was)
    .map(([type, n]) => [type, n - (now[type] ?? 0)] as const)
    .filter(([, n]) => n > 0)
    .map(([type, n]) => {
      const label = (BLOCK_LABELS[type as ContentBlock['type']] ?? type).toLowerCase()
      return `${n} ${label}${n === 1 ? '' : 's'}`
    })
  if (lost.length === 0) return null
  const list = lost.length === 1 ? lost[0] : `${lost.slice(0, -1).join(', ')} and ${lost[lost.length - 1]}`
  return `This removes ${list}.`
}

/** The 409 `lesson_changed` body, or null for any other error. */
export function parseConflict(error: unknown): { updatedAt: string; updatedByName: string | null } | null {
  if (!error || typeof error !== 'object' || !('error' in error)) return null
  const body = (error as { error: Record<string, unknown> }).error
  if (body.code !== 'lesson_changed' || typeof body.updated_at !== 'string') return null
  return { updatedAt: body.updated_at, updatedByName: typeof body.updated_by_name === 'string' ? body.updated_by_name : null }
}
```

Check `BLOCK_LABELS` in `lib/contentBlocks.ts`. If the labels aren't "Quiz", "Card group", "Paragraph", the test strings must follow them: change the test's expected text to match the real labels, and record a ruling.

Run: `cd frontend && npx vitest run src/lib/lessonSave.test.ts`
Expected: PASS.

- [ ] **Step 4: Write the failing editor tests**

At the top of `LessonEditor.test.tsx`, make the client mock carry `POST` (the existing tests then need `/check` to return no findings):

```ts
const clientMock = vi.hoisted(() => ({ PATCH: vi.fn(), POST: vi.fn() }))
```

In the existing `beforeEach`: `clientMock.POST.mockReset(); clientMock.POST.mockResolvedValue({ data: { findings: [] }, error: undefined })`. Pass `updatedAt="2026-10-05T12:00:00+00:00"` to every `<LessonEditor lesson={LESSON} />` render that saves.

New `describe`:

```tsx
describe('LessonEditor guarded save (B5)', () => {
  const BASE = '2026-10-05T12:00:00+00:00'
  beforeEach(() => {
    clientMock.PATCH.mockReset()
    clientMock.POST.mockReset()
    clientMock.POST.mockResolvedValue({ data: { findings: [] }, error: undefined })
    clientMock.PATCH.mockResolvedValue({
      data: { ...LESSON, sort_order: 0, module_id: 'm', updated_at: '2026-10-05T12:05:00+00:00', content_blocks: [{ id: 'p1', type: 'paragraph', text: 'Changed' }] },
      error: undefined,
    })
  })

  function edit() {
    fireEvent.change(screen.getByDisplayValue('Hello world'), { target: { value: 'Changed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  }

  it('saves straight away when the check finds nothing, sending the base updated_at', async () => {
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    expect(await screen.findByText('Saved')).toBeInTheDocument()
    expect(clientMock.PATCH.mock.calls[0][1].body.expected_updated_at).toBe(BASE)
  })

  it('shows findings with Save anyway and Keep editing', async () => {
    clientMock.POST.mockResolvedValue({
      data: { findings: [{ severity: 'warning', block_index: 0, where: 'block 1 · paragraph', message: 'em dash in [0].text' }] },
      error: undefined,
    })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    expect(await screen.findByText('em dash in [0].text')).toBeInTheDocument()
    expect(clientMock.PATCH).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Keep editing' }))
    expect(clientMock.PATCH).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Save anyway' }))
    expect(await screen.findByText('Saved')).toBeInTheDocument()
  })

  it('offers Reload or Overwrite on a 409, naming who and when', async () => {
    const onReload = vi.fn()
    clientMock.PATCH.mockResolvedValueOnce({
      data: undefined,
      error: { error: { code: 'lesson_changed', message: 'm', updated_at: '2026-10-05T14:32:00+00:00', updated_by_name: 'Aaron Neuville' } },
    })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} onReload={onReload} />)
    edit()
    expect(await screen.findByText(/Aaron Neuville changed this lesson/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Overwrite with mine' }))
    expect(await screen.findByText('Saved')).toBeInTheDocument()
    expect(clientMock.PATCH.mock.calls[1][1].body.expected_updated_at).toBe('2026-10-05T14:32:00+00:00')
  })

  it('a second conflict after overwrite shows again', async () => {
    const conflict = (name: string, at: string) => ({ data: undefined, error: { error: { code: 'lesson_changed', message: 'm', updated_at: at, updated_by_name: name } } })
    clientMock.PATCH
      .mockResolvedValueOnce(conflict('Aaron Neuville', '2026-10-05T14:32:00+00:00'))
      .mockResolvedValueOnce(conflict('Bea Third', '2026-10-05T14:40:00+00:00'))
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} />)
    edit()
    fireEvent.click(await screen.findByRole('button', { name: 'Overwrite with mine' }))
    expect(await screen.findByText(/Bea Third changed this lesson/)).toBeInTheDocument()
  })

  it('names "Someone" when the editor is unknown, and Reload calls back', async () => {
    const onReload = vi.fn()
    clientMock.PATCH.mockResolvedValueOnce({
      data: undefined,
      error: { error: { code: 'lesson_changed', message: 'm', updated_at: '2026-10-05T14:32:00+00:00', updated_by_name: null } },
    })
    render(<LessonEditor lesson={LESSON} updatedAt={BASE} onReload={onReload} />)
    edit()
    expect(await screen.findByText(/Someone changed this lesson/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reload their version' }))
    expect(onReload).toHaveBeenCalled()
  })

  it('embedded editor never calls check', () => {
    render(<LessonEditor lesson={LESSON} embedded />)
    fireEvent.change(screen.getByDisplayValue('Hello world'), { target: { value: 'x' } })
    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull()
    expect(clientMock.POST).not.toHaveBeenCalled()
  })
})
```

Run: `cd frontend && npx vitest run src/components/lesson/LessonEditor.test.tsx`
Expected: FAIL (no check call, no panel, no `expected_updated_at`).

- [ ] **Step 5: Implement the hook and the dialog**

```ts
// frontend/src/components/lesson/useGuardedSave.ts
// The lesson editor's save flow (B5): house-style check as a soft gate, then a
// PATCH carrying the base updated_at; a 409 lesson_changed becomes a prompt.
import { useRef, useState } from 'react'
import { client, errorMessage } from '../../api/client'
import type { components } from '../../api/schema'
import { parseConflict, removalSummary, type Finding } from '../../lib/lessonSave'
import type { ContentBlock } from '../../types/contentBlocks'

type LessonOut = components['schemas']['LessonOut']
export interface SavePayload { title?: string; content_blocks: ContentBlock[] }

export type Gate =
  | { kind: 'idle' }
  | { kind: 'busy' }
  | { kind: 'findings'; findings: Finding[]; removal: string | null; checkOnly: boolean }
  | { kind: 'conflict'; updatedAt: string; updatedByName: string | null }
  | { kind: 'error'; message: string }

interface Options {
  lessonId: string
  baseUpdatedAt: string | null | undefined
  onSaved: (data: LessonOut) => void
  onReload?: () => void
}

export function useGuardedSave({ lessonId, baseUpdatedAt, onSaved, onReload }: Options) {
  const [gate, setGate] = useState<Gate>({ kind: 'idle' })
  const pending = useRef<SavePayload | null>(null)

  async function runCheck(blocks: ContentBlock[]): Promise<Finding[] | null> {
    const { data, error } = await client.POST('/api/admin/lessons/{lesson_id}/check', {
      params: { path: { lesson_id: lessonId } },
      body: { content_blocks: blocks as unknown as Record<string, unknown>[] },
    })
    if (!data) {
      setGate({ kind: 'error', message: errorMessage(error, 'The check failed. Please try again.') })
      return null
    }
    return data.findings
  }

  async function patch(payload: SavePayload, expected: string | null | undefined) {
    setGate({ kind: 'busy' })
    const { data, error } = await client.PATCH('/api/admin/lessons/{lesson_id}', {
      params: { path: { lesson_id: lessonId } },
      body: {
        ...payload,
        content_blocks: payload.content_blocks as unknown as Record<string, unknown>[],
        ...(expected ? { expected_updated_at: expected } : {}),
      },
    })
    if (data) {
      pending.current = null
      setGate({ kind: 'idle' })
      onSaved(data)
      return
    }
    const conflict = parseConflict(error)
    setGate(conflict ? { kind: 'conflict', ...conflict } : { kind: 'error', message: errorMessage(error, 'Failed to save.') })
  }

  async function save(payload: SavePayload, opts: { before?: ContentBlock[] } = {}) {
    pending.current = payload
    setGate({ kind: 'busy' })
    const findings = await runCheck(payload.content_blocks)
    if (findings === null) return
    const removal = opts.before ? removalSummary(opts.before, payload.content_blocks) : null
    if (removal || findings.some(f => f.severity === 'warning')) {
      setGate({ kind: 'findings', findings, removal, checkOnly: false })
      return
    }
    await patch(payload, baseUpdatedAt)
  }

  async function check(blocks: ContentBlock[]) {
    setGate({ kind: 'busy' })
    const findings = await runCheck(blocks)
    if (findings !== null) setGate({ kind: 'findings', findings, removal: null, checkOnly: true })
  }

  return {
    gate,
    save,
    check,
    saveAnyway: () => { if (pending.current) void patch(pending.current, baseUpdatedAt) },
    keepEditing: () => { pending.current = null; setGate({ kind: 'idle' }) },
    overwrite: () => {
      if (pending.current && gate.kind === 'conflict') void patch(pending.current, gate.updatedAt)
    },
    reload: () => { pending.current = null; setGate({ kind: 'idle' }); onReload?.() },
  }
}
```

```tsx
// frontend/src/components/lesson/SaveGate.tsx
// The editor's save dialog (B5): findings / removal warning / conflict prompt.
// Inline styles to match LessonEditor (the admin kit's CSS isn't loaded on
// the /learning routes).
import type { Gate } from './useGuardedSave'

interface Props {
  gate: Gate
  onSaveAnyway: () => void
  onKeepEditing: () => void
  onReload: () => void
  onOverwrite: () => void
}

const panel: React.CSSProperties = { margin: '12px 20px', padding: 16, border: '1px solid #E2E2E2', borderRadius: 12, background: '#FFFBEB', fontFamily: 'var(--dlw-font-body)', fontSize: 14 }
const btn: React.CSSProperties = { padding: '7px 16px', borderRadius: 999, border: '1px solid #E2E2E2', background: '#fff', fontWeight: 600, cursor: 'pointer', marginRight: 8 }
const primary: React.CSSProperties = { ...btn, background: '#3BC9BC', border: 'none', color: '#fff' }

function at(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function SaveGate({ gate, onSaveAnyway, onKeepEditing, onReload, onOverwrite }: Props) {
  if (gate.kind === 'idle' || gate.kind === 'busy') return null
  if (gate.kind === 'error') {
    return <div role="alert" style={{ ...panel, background: '#FEF2F2', color: '#C42828' }}>{gate.message}</div>
  }
  if (gate.kind === 'conflict') {
    return (
      <div role="alertdialog" aria-label="This lesson changed" style={panel}>
        <p style={{ marginTop: 0 }}>
          <strong>{gate.updatedByName ?? 'Someone'} changed this lesson</strong> at {at(gate.updatedAt)} while you were editing.
        </p>
        <p>Reload their version (your unsaved edits are discarded), or overwrite it with yours.</p>
        <button type="button" style={btn} onClick={onReload}>Reload their version</button>
        <button type="button" style={primary} onClick={onOverwrite}>Overwrite with mine</button>
      </div>
    )
  }
  const warnings = gate.findings.filter(f => f.severity === 'warning')
  const infos = gate.findings.filter(f => f.severity === 'info')
  return (
    <div role="dialog" aria-label="Check results" style={panel}>
      {gate.removal && <p role="alert" style={{ marginTop: 0, color: '#C42828', fontWeight: 600 }}>{gate.removal}</p>}
      {warnings.length === 0 && !gate.removal && <p style={{ marginTop: 0 }}>No house-style findings.</p>}
      {warnings.length > 0 && (
        <ul style={{ margin: '0 0 12px', paddingLeft: 18 }}>
          {warnings.map((f, i) => <li key={i}><span style={{ color: '#8A8A8A' }}>{f.where}:</span> {f.message}</li>)}
        </ul>
      )}
      {infos.length > 0 && (
        <p style={{ color: '#8A8A8A', fontSize: 13 }}>{infos.length} note{infos.length === 1 ? '' : 's'} (e.g. image placeholders awaiting upload) — fine to save.</p>
      )}
      {gate.checkOnly ? (
        <button type="button" style={btn} onClick={onKeepEditing}>Close</button>
      ) : (
        <>
          <button type="button" style={btn} onClick={onKeepEditing}>Keep editing</button>
          <button type="button" style={primary} onClick={onSaveAnyway}>Save anyway</button>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 6: Wire `LessonEditor`**

- `EditedLesson` gains `updated_at?: string`.
- Props gain `updatedAt?: string | null` and `onReload?: () => void`.
- Replace `save()` and the `saving`/`error` state with the hook:

```tsx
  const guarded = useGuardedSave({
    lessonId: lesson.id,
    baseUpdatedAt: updatedAt,
    onReload,
    onSaved: data => {
      setDirty(false)
      onSave?.({ title: data.title, content_blocks: data.content_blocks as ContentBlock[], updated_at: data.updated_at })
    },
  })
  const saving = guarded.gate.kind === 'busy'
```

- The Save button calls `() => void guarded.save({ title, content_blocks: blocks })`.
- Add a **Check** button beside it (ghost style, `onClick={() => void guarded.check(blocks)}`, enabled whenever not saving).
- Render `<SaveGate gate={guarded.gate} onSaveAnyway={guarded.saveAnyway} onKeepEditing={guarded.keepEditing} onReload={guarded.reload} onOverwrite={guarded.overwrite} />` where the old `error` div was.
- `embedded` instances render neither button, so they never call the hook's functions (the Review Focus 5 test).

- [ ] **Step 7: Wire `LessonPage`**

- Pass `updatedAt={lesson.updated_at}` and `onReload={() => setReloadKey(k => k + 1)}` to `<LessonEditor>`.
- `handleEditorSave` also stores `updated_at` (`setLesson(l => l ? { ...l, title, content_blocks, updated_at: updated.updated_at ?? l.updated_at } : l)`).
- MDX "Save as blocks": replace `saveMdx`'s direct PATCH with a second hook instance:

```tsx
  const mdxSave = useGuardedSave({
    lessonId: lesson?.id ?? '',
    baseUpdatedAt: lesson?.updated_at,
    onReload: () => setReloadKey(k => k + 1),
    onSaved: data => {
      setLesson(l => (l ? { ...l, content_blocks: data.content_blocks, updated_at: data.updated_at } : l))
      setMdxMode(false)
      setMdxText('')
      setEditMode(true)
    },
  })
```

- `saveMdx()` becomes `void mdxSave.save({ content_blocks: parseMdxToBlocks(mdxText) }, { before: blocks })`, with `mdxSaving = mdxSave.gate.kind === 'busy'`.
- Render `<SaveGate …mdxSave… />` in the MDX toolbar area, replacing the `mdxError` display.
- The hook is called unconditionally at the top level of `LessonPage` (rules of hooks), so `lesson?.id ?? ''` is fine: it's never invoked before the lesson loads.

Add a `LessonPage.test.tsx` case, following that file's existing fetch/client mocking. It opens MDX mode on a lesson containing a quiz, replaces the MDX text with a single paragraph, clicks "Save as blocks", and expects "This removes 1 quiz." with **Save anyway** and **Keep editing**, and no PATCH yet.

- [ ] **Step 8: Run**

Run: `cd frontend && npx vitest run src/lib/lessonSave.test.ts src/components/lesson src/pages/LessonPage.test.tsx src/pages/admin2/ContentImprovementPage.test.tsx`
Expected: PASS.

Run: `cd frontend && npm run typecheck && npm run lint`
Expected: clean (only the existing warnings).

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "feat(editor): checks on Save, conflict prompt, MDX removal warning (B5, #146)"
```

---

### Task 7: Docs, full checks, review, PR

**Files:**
- Modify: `docs/content/CLAUDE.md`, `docs/content/authoring-guide.md` §11, `docs/content/review-process-technical-notes.md`, `docs/feature-index.md`, `CLAUDE.md` (code head line)

- [ ] **Step 1: Docs**

- **`docs/content/CLAUDE.md`:** where it names `check_draft.py` as the gate, add: "In the website the same checks run on **Save** (and the editor's **Check** button) via `src/services/lesson_qa.py`; `check_draft.py` is the CLI over that module for drafts written outside the editor."
- **Authoring guide §11:**
  - delete the "**`lessons` has no `updated_at` column**" bullet;
  - append to the Concurrency bullet: "Since B5 the editor refuses a save from an outdated copy and offers Reload / Overwrite. Scripts writing straight to the DB bypass that, so the rule above still binds them."
- **`review-process-technical-notes.md`:** at the #60 entry, add the cause (single-quoted JSON truncated at the first apostrophe; the splitter stopping at `>`; `question` never serialised), the fix, and the round-trip suite's path.
- **`docs/feature-index.md`:** add "**Lesson editor QA + conflict protection** (#146, B5): checks on Save, Reload/Overwrite on a stale save, MDX round-trip fix (#60); `2026-10-05-lesson-editor-qa-design.md`; `services/lesson_qa.py`, `components/lesson/useGuardedSave.ts`."
- **`CLAUDE.md`** "Current state": code head becomes `c1d2e3f4a5b6`.

- [ ] **Step 2: Full checks**

Run: `cd backend && uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`
Run: `cd frontend && npm run typecheck && npm run lint && npm test && npm run build`
Expected: all green; docs-drift passes.

- [ ] **Step 3: Commit, one strong-model review, PR**

```bash
git add docs CLAUDE.md
git commit -m "docs: in-app checks, conflict protection, #60 cause (B5, #146)"
```

Dispatch one reviewer (most capable model) over the branch diff, with the spec, this plan and the Review Focus above. Fix real findings, each with a test that fails first. Then:

```bash
git push -u origin feat/lesson-editor-qa
gh pr create --base main --title "feat(editor): lesson QA checks, no silent overwrites, #60 fix — B5" --body "Closes #146
Closes #60
…"
```

The PR body:
- covers what changed, the migration (`c1d2e3f4a5b6`, expand-first) and tests;
- notes that `expected_updated_at` becomes required in a follow-up;
- ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
