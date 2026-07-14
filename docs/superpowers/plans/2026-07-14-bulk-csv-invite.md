# Bulk CSV Invite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin upload a CSV (first name, last name, email) in the project view, preview a validated result, confirm, and have the valid users created and emailed an invite link.

**Architecture:** A pure CSV parser + preview builder (no DB), two thin `AdminUserService` methods (batched existence check + bulk create), and one admin endpoint `POST /api/admin/invites/bulk` with a `dry_run` flag. The endpoint reuses the existing single-invite plumbing (`TokenService.issue_action_token`, `EmailService.send_invite_email`, `_email_the_link`). The frontend adds a hand-typed multipart client helper (mirroring `api/upload.ts`) and a `BulkInviteModal` opened from `ProjectDetailView`.

**Tech Stack:** FastAPI (Python 3.13, uv), SQLAlchemy async, Pydantic v2, React 18 + TypeScript (Vite), `openapi-fetch` (bypassed for this multipart call, per the `upload.ts` precedent).

**Reference spec:** `docs/superpowers/specs/2026-07-14-bulk-csv-invite-design.md`

## Global Constraints

- Backend layering is MANDATORY (`python-be-architecture.md`): router → service → repository → model. **Services never call other services**; token minting + emailing stay in the router (exactly as `create_invite` does). Routers stay try/except-free — domain errors propagate to `main.py` handlers.
- Backend checks after changes (run inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test`. Coverage must stay ≥ 80%.
- Integration tests run against the real `ai-enablement-hub-test` PostgreSQL DB (not SQLite). `test_settings` pins `email=None`, `storage=None`.
- **FastAPI signature gotcha:** any type used in a router/DI *parameter* annotation must be a runtime import (not under `TYPE_CHECKING`).
- Frontend checks after changes (run inside `frontend/`): `npm run typecheck && npm run lint && npm run build`. There is no frontend unit-test runner — frontend tasks verify via those three commands + a manual browser check.
- Error shape is `{"error": {code, message}}`; status→code map: 400 `bad_request`, 403 `forbidden`, 404 `not_found`, 409 `conflict`, 413 `payload_too_large`, 422 `validation_error`, 429 `rate_limited`.
- Feature decisions (from the spec, locked): preview→confirm via one `dry_run` endpoint; ≤50 rows typical → synchronous; **skip all existing emails**; named headers `first_name,last_name,email` (case-insensitive, any order, extra columns ignored); auto-detect `,`/`;` + strip UTF-8 BOM; **row cap 200, file cap 1 MiB**; the uploaded file is never persisted; audit log = summary counts only (no PII).

---

## Before you start (pre-flight, not a task)

The working tree is on branch `feature/lesson-feedback` with **unrelated** uncommitted work (a lesson-feedback backend feature). Per the user's decision, do not commit onto that branch. Create a dedicated branch first; the lesson-feedback changes remain uncommitted in the tree and are not yours to touch:

```bash
git checkout -b feature/bulk-csv-invite
```

All `git add` steps below stage only the specific files each task creates/modifies — never `git add -A`.

---

## File Structure

**Backend (create)**
- `backend/src/services/invite_csv.py` — pure CSV parser + preview builder + size/row constants. One responsibility: turn bytes into categorized rows.

**Backend (modify)**
- `backend/src/services/exceptions.py` — add `InvalidCsvError(DomainError)`.
- `backend/src/schemas/admin_users.py` — add `BulkInviteRow`, `BulkInviteSummary`, `BulkInviteReport`.
- `backend/src/repositories/base.py` — add abstract `AbstractUserRepository.emails_in`.
- `backend/src/repositories/user_repository.py` — implement `emails_in`.
- `backend/src/services/admin_user_service.py` — add `existing_emails`, `ensure_project`, `create_invited_users`.
- `backend/src/routers/admin_users.py` — add `POST /api/admin/invites/bulk`.

**Backend (tests, create)**
- `backend/tests/unit/test_invite_csv.py` — parser + preview builder.
- `backend/tests/integration/test_routers/test_admin_bulk_invite.py` — service methods + endpoint.

**Frontend (create)**
- `frontend/src/api/bulkInvite.ts` — hand-typed multipart helper.
- `frontend/src/pages/admin/BulkInviteModal.tsx` — the upload/preview/confirm/result UI.

**Frontend (modify)**
- `frontend/src/pages/admin/ProjectDetailView.tsx` — "Bulk invite (CSV)" button + modal mount.

> **Frontend typing note (deviation from the spec's "run `gen:api`"):** this endpoint is multipart, and the repo already established (`api/upload.ts`) that multipart calls are hand-typed rather than routed through `openapi-fetch`/`schema.d.ts`. We follow that precedent, so `npm run gen:api` is **not required** for this feature (the endpoint still appears in OpenAPI/`/docs` via its `response_model`). Regenerating is harmless but needs a running backend + shared DB, so it is optional.

---

### Task 1: CSV parser + preview builder (pure)

**Files:**
- Create: `backend/src/services/invite_csv.py`
- Modify: `backend/src/services/exceptions.py`
- Test: `backend/tests/unit/test_invite_csv.py`

**Interfaces:**
- Consumes: `DomainError` (from `src.services.exceptions`).
- Produces:
  - `class InvalidCsvError(DomainError)` — whole-file failure → 400.
  - `MAX_INVITE_CSV_BYTES: int = 1_048_576`, `MAX_INVITE_ROWS: int = 200`.
  - `@dataclass ParsedRow(row_number: int, first_name: str, last_name: str, email: str, error: str | None)`.
  - `@dataclass PreviewRow(row_number: int, first_name: str, last_name: str, email: str, status: str, detail: str | None)` — `status ∈ {"valid","duplicate","invalid","created","email_failed"}`.
  - `parse_invite_csv(raw: bytes) -> list[ParsedRow]` (raises `InvalidCsvError`).
  - `build_preview(parsed: list[ParsedRow], existing_emails: set[str]) -> list[PreviewRow]`.

- [ ] **Step 1: Add the exception**

In `backend/src/services/exceptions.py`, add to `__all__` (keep it alphabetical): `"InvalidCsvError",`. Then add the class after `InvalidRequestError`:

```python
class InvalidCsvError(DomainError):
    """The uploaded CSV cannot be processed as a whole (bad encoding, empty,
    missing a required column, or too many rows). → 400"""
```

- [ ] **Step 2: Write the failing parser tests**

Create `backend/tests/unit/test_invite_csv.py`:

```python
from __future__ import annotations

import pytest

from src.services.exceptions import InvalidCsvError
from src.services.invite_csv import (
    MAX_INVITE_ROWS,
    build_preview,
    parse_invite_csv,
)


def _b(text: str) -> bytes:
    return text.encode("utf-8")


class TestParse:
    def test_comma_happy_path_normalizes_email(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\nJan,Peeters,Jan.Peeters@Acme.be\n"))
        assert len(rows) == 1
        r = rows[0]
        assert (r.first_name, r.last_name, r.email, r.error) == (
            "Jan", "Peeters", "jan.peeters@acme.be", None,
        )
        assert r.row_number == 2  # header is line 1

    def test_semicolon_delimiter(self) -> None:
        rows = parse_invite_csv(_b("first_name;last_name;email\nSofie;Maes;sofie@acme.be\n"))
        assert rows[0].error is None
        assert rows[0].email == "sofie@acme.be"

    def test_utf8_bom_is_stripped(self) -> None:
        raw = "﻿first_name,last_name,email\nAn,Van,an@acme.be\n".encode("utf-8")
        rows = parse_invite_csv(raw)
        assert rows[0].first_name == "An"
        assert rows[0].error is None

    def test_headers_reordered_and_extra_columns_ignored(self) -> None:
        rows = parse_invite_csv(_b("email,department,last_name,first_name\na@b.co,Sales,Doe,Jane\n"))
        assert (rows[0].first_name, rows[0].last_name, rows[0].email) == ("Jane", "Doe", "a@b.co")

    def test_crlf_and_quoted_name_with_comma(self) -> None:
        rows = parse_invite_csv(b'first_name,last_name,email\r\n"De, Jan",Peeters,jan@acme.be\r\n')
        assert rows[0].first_name == "De, Jan"
        assert rows[0].error is None

    def test_blank_name_is_invalid(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\n,Peeters,jan@acme.be\n"))
        assert rows[0].error == "missing first or last name"

    def test_malformed_email_is_invalid(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\nJan,Peeters,not-an-email\n"))
        assert rows[0].error == "malformed email"

    def test_in_file_duplicate_flagged_case_insensitively(self) -> None:
        rows = parse_invite_csv(
            _b("first_name,last_name,email\nA,B,dup@acme.be\nC,D,DUP@acme.be\n")
        )
        assert rows[0].error is None
        assert rows[1].error == "duplicate in file"

    def test_fully_blank_rows_skipped(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\nJan,Peeters,jan@acme.be\n,,\n"))
        assert len(rows) == 1

    def test_missing_required_column_raises(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(_b("first_name,email\nJan,jan@acme.be\n"))

    def test_empty_file_raises(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(b"")

    def test_header_only_raises(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(_b("first_name,last_name,email\n"))

    def test_too_many_rows_raises(self) -> None:
        body = "first_name,last_name,email\n" + "".join(
            f"F{i},L{i},user{i}@acme.be\n" for i in range(MAX_INVITE_ROWS + 1)
        )
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(_b(body))

    def test_undecodable_bytes_raise(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(b"first_name,last_name,email\n\xff\xfe not utf8\n")

    def test_xlsx_workbook_gives_a_friendly_error(self) -> None:
        # An .xlsx is a ZIP archive (PK magic); the message must guide, not confuse.
        with pytest.raises(InvalidCsvError, match="Excel workbook"):
            parse_invite_csv(b"PK\x03\x04 fake xlsx bytes")


class TestBuildPreview:
    def test_categorizes_invalid_duplicate_valid(self) -> None:
        parsed = parse_invite_csv(
            _b(
                "first_name,last_name,email\n"
                "Jan,Peeters,jan@acme.be\n"
                "Sofie,Maes,sofie@acme.be\n"
                ",Bad,bad@acme.be\n"
            )
        )
        preview = build_preview(parsed, existing_emails={"sofie@acme.be"})
        by_email = {p.email: p.status for p in preview}
        assert by_email["jan@acme.be"] == "valid"
        assert by_email["sofie@acme.be"] == "duplicate"
        assert by_email["bad@acme.be"] == "invalid"
        dup = next(p for p in preview if p.email == "sofie@acme.be")
        assert dup.detail == "already registered"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run (inside `backend/`): `uv run pytest tests/unit/test_invite_csv.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.services.invite_csv'`.

- [ ] **Step 4: Implement the parser + preview builder**

Create `backend/src/services/invite_csv.py`:

```python
"""Pure invite-CSV parsing + preview categorization — no DB, no I/O.

Handles the messy real files admins produce: UTF-8 BOM (Excel), ';' vs ','
delimiters (Excel in EU locales), header order, extra columns, blank rows.
Whole-file problems raise InvalidCsvError (→ 400); per-row problems are marked
on the row so the admin sees exactly which line failed and why.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from src.services.exceptions import InvalidCsvError

__all__ = [
    "MAX_INVITE_CSV_BYTES",
    "MAX_INVITE_ROWS",
    "ParsedRow",
    "PreviewRow",
    "build_preview",
    "parse_invite_csv",
]

MAX_INVITE_CSV_BYTES = 1_048_576  # 1 MiB
MAX_INVITE_ROWS = 200

_REQUIRED_COLUMNS = ("first_name", "last_name", "email")
# Syntactic sanity check only (the DB has no format constraint): one '@', a dot
# in the domain, no spaces. Deliberately lenient — it catches typos, not RFC edge cases.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class ParsedRow:
    row_number: int  # 1-based line in the file (header = line 1)
    first_name: str
    last_name: str
    email: str  # stripped + lowercased when syntactically valid
    error: str | None  # None = a clean candidate


@dataclass
class PreviewRow:
    row_number: int
    first_name: str
    last_name: str
    email: str
    status: str  # valid | duplicate | invalid | created | email_failed
    detail: str | None


def parse_invite_csv(raw: bytes) -> list[ParsedRow]:
    # Friendly nudge for the #1 Excel footgun: a saved .xlsx (ZIP/OOXML) or .xls
    # (OLE) instead of a CSV. Caught before decode so the admin gets guidance,
    # not "not valid UTF-8".
    if raw[:4] in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0"):
        raise InvalidCsvError(
            "This looks like an Excel workbook (.xlsx/.xls). In Excel, use "
            "File → Save As → CSV, then upload the .csv file."
        )
    try:
        text = raw.decode("utf-8-sig")  # utf-8-sig transparently drops a BOM
    except UnicodeDecodeError as exc:
        raise InvalidCsvError("The file is not valid UTF-8 text.") from exc

    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise InvalidCsvError("The CSV file is empty.")

    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, [])
    index = {name.strip().lower(): i for i, name in enumerate(header)}
    missing = [c for c in _REQUIRED_COLUMNS if c not in index]
    if missing:
        raise InvalidCsvError(f"CSV is missing required column(s): {', '.join(missing)}")

    fi, li, ei = index["first_name"], index["last_name"], index["email"]
    rows: list[ParsedRow] = []
    seen: set[str] = set()
    line_number = 1  # header consumed above
    for record in reader:
        line_number += 1
        cells = [c.strip() for c in record]
        if not any(cells):
            continue  # blank line (e.g. trailing newline)
        first = cells[fi] if fi < len(cells) else ""
        last = cells[li] if li < len(cells) else ""
        email = (cells[ei] if ei < len(cells) else "").lower()

        error: str | None = None
        if not first or not last:
            error = "missing first or last name"
        elif not _EMAIL_RE.match(email):
            error = "malformed email"
        elif email in seen:
            error = "duplicate in file"
        else:
            seen.add(email)

        rows.append(ParsedRow(line_number, first, last, email, error))
        if len(rows) > MAX_INVITE_ROWS:
            raise InvalidCsvError(
                f"The CSV has more than {MAX_INVITE_ROWS} rows — split it into smaller files."
            )

    if not rows:
        raise InvalidCsvError("The CSV has a header but no data rows.")
    return rows


def build_preview(parsed: list[ParsedRow], existing_emails: set[str]) -> list[PreviewRow]:
    """Parser errors → 'invalid'; emails already in the system → 'duplicate';
    everything else → 'valid'. Pure — the router creates nothing here."""
    preview: list[PreviewRow] = []
    for r in parsed:
        if r.error is not None:
            preview.append(
                PreviewRow(r.row_number, r.first_name, r.last_name, r.email, "invalid", r.error)
            )
        elif r.email in existing_emails:
            preview.append(
                PreviewRow(
                    r.row_number, r.first_name, r.last_name, r.email, "duplicate",
                    "already registered",
                )
            )
        else:
            preview.append(
                PreviewRow(r.row_number, r.first_name, r.last_name, r.email, "valid", None)
            )
    return preview
```

- [ ] **Step 5: Run the tests to verify they pass**

Run (inside `backend/`): `uv run pytest tests/unit/test_invite_csv.py -v`
Expected: PASS (all cases).

- [ ] **Step 6: Format, lint, commit**

```bash
cd backend && uv run poe format && uv run poe lint && cd ..
git add "AI ENABLEMENT HUB REBUILD/backend/src/services/invite_csv.py" \
        "AI ENABLEMENT HUB REBUILD/backend/src/services/exceptions.py" \
        "AI ENABLEMENT HUB REBUILD/backend/tests/unit/test_invite_csv.py"
git commit -m "feat: invite CSV parser + preview builder"
```

---

### Task 2: Repository + service methods

**Files:**
- Modify: `backend/src/repositories/base.py` (add abstract `emails_in`)
- Modify: `backend/src/repositories/user_repository.py` (implement `emails_in`)
- Modify: `backend/src/services/admin_user_service.py` (add 3 methods)
- Test: `backend/tests/integration/test_routers/test_admin_bulk_invite.py` (new file, `TestBulkInviteService` class)

**Interfaces:**
- Consumes: `AbstractUserRepository`, `select`, `User` (already imported in those files); `OrgRepository.get_project`, `UserRepository.get_by_email`/`create` (existing).
- Produces:
  - `AbstractUserRepository.emails_in(emails: list[str]) -> set[str]` + impl.
  - `AdminUserService.existing_emails(emails: list[str]) -> set[str]`.
  - `AdminUserService.ensure_project(project_id: uuid.UUID) -> None` (raises `NotFoundError`).
  - `AdminUserService.create_invited_users(project_id: uuid.UUID, rows: list[tuple[str, str, str]]) -> list[User]` — rows are `(first_name, last_name, email)`, already normalized; returns created users in input order, skipping emails that already exist.

- [ ] **Step 1: Write the failing service tests**

Create `backend/tests/integration/test_routers/test_admin_bulk_invite.py`:

```python
"""Bulk invite: the AdminUserService helpers (this file's TestBulkInviteService)
and the POST /api/admin/invites/bulk endpoint (added in a later task). The
service is wired to the test session directly, mirroring conftest's
token_service fixture."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.user_repository import UserRepository
from src.services.admin_user_service import AdminUserService
from src.services.exceptions import NotFoundError
from tests.fixtures.factories import create_company, create_project, create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
def admin_user_service(db_session: AsyncSession) -> AdminUserService:
    return AdminUserService(
        UserRepository(db_session),
        OrgRepository(db_session),
        AssignmentRepository(db_session),
        ContentRepository(db_session),
        SurveyRepository(db_session),
    )


class TestBulkInviteService:
    async def test_existing_emails_returns_only_known(
        self, db_session: AsyncSession, admin_user_service: AdminUserService
    ) -> None:
        await create_user(db_session, email="known@acme.be")
        result = await admin_user_service.existing_emails(["known@acme.be", "new@acme.be"])
        assert result == {"known@acme.be"}

    async def test_existing_emails_empty_input(
        self, admin_user_service: AdminUserService
    ) -> None:
        assert await admin_user_service.existing_emails([]) == set()

    async def test_ensure_project_unknown_raises(
        self, admin_user_service: AdminUserService
    ) -> None:
        with pytest.raises(NotFoundError):
            await admin_user_service.ensure_project(uuid.uuid4())

    async def test_create_invited_users_creates_and_binds_project(
        self, db_session: AsyncSession, admin_user_service: AdminUserService
    ) -> None:
        company = await create_company(db_session, "Bulk Co")
        project = await create_project(db_session, company, "Bulk Project")
        created = await admin_user_service.create_invited_users(
            project.id,
            [("Jan", "Peeters", "jan@acme.be"), ("Sofie", "Maes", "sofie@acme.be")],
        )
        assert {u.email for u in created} == {"jan@acme.be", "sofie@acme.be"}
        assert all(u.project_id == project.id for u in created)
        assert all(u.company_id == company.id for u in created)
        assert all(u.role == "user" and u.password_set is False for u in created)

    async def test_create_invited_users_skips_now_existing(
        self, db_session: AsyncSession, admin_user_service: AdminUserService
    ) -> None:
        company = await create_company(db_session, "Bulk Co2")
        project = await create_project(db_session, company, "Bulk Project2")
        await create_user(db_session, email="taken@acme.be")
        created = await admin_user_service.create_invited_users(
            project.id,
            [("Taken", "User", "taken@acme.be"), ("Fresh", "User", "fresh@acme.be")],
        )
        assert {u.email for u in created} == {"fresh@acme.be"}

    async def test_create_invited_users_unknown_project_raises(
        self, admin_user_service: AdminUserService
    ) -> None:
        with pytest.raises(NotFoundError):
            await admin_user_service.create_invited_users(
                uuid.uuid4(), [("A", "B", "a@b.co")]
            )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (inside `backend/`): `uv run pytest tests/integration/test_routers/test_admin_bulk_invite.py -v`
Expected: FAIL — `AttributeError: 'AdminUserService' object has no attribute 'existing_emails'`.

- [ ] **Step 3: Add the abstract repository method**

In `backend/src/repositories/base.py`, inside `AbstractUserRepository` (after `get_by_email`), add:

```python
    @abstractmethod
    async def emails_in(self, emails: list[str]) -> set[str]:
        """Which of the given (normalized) emails already have a user row
        (bulk-invite dedup)."""
```

- [ ] **Step 4: Implement it**

In `backend/src/repositories/user_repository.py`, add after `get_by_email`:

```python
    async def emails_in(self, emails: list[str]) -> set[str]:
        if not emails:
            return set()
        result = await self._session.execute(select(User.email).where(User.email.in_(emails)))
        return set(result.scalars().all())
```

- [ ] **Step 5: Add the service methods**

In `backend/src/services/admin_user_service.py`, add these methods to `AdminUserService` (place them right after `invite`). `uuid`, `User`, `NotFoundError` are already imported/available in that module:

```python
    async def existing_emails(self, emails: list[str]) -> set[str]:
        """Subset of the given (normalized) emails that already have a user row."""
        return await self._users.emails_in(emails)

    async def ensure_project(self, project_id: uuid.UUID) -> None:
        """Raise NotFoundError if the project does not exist (bulk-invite preflight)."""
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")

    async def create_invited_users(
        self, project_id: uuid.UUID, rows: list[tuple[str, str, str]]
    ) -> list[User]:
        """Create one invited user per (first_name, last_name, email) row, all
        bound to the project (404 if unknown). Emails already taken — e.g.
        created between the admin's preview and confirm — are skipped. Returns
        the users actually created, in input order; the router mints each one an
        invite token (services never call services)."""
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        created: list[User] = []
        for first_name, last_name, email in rows:
            if await self._users.get_by_email(email) is not None:
                continue
            created.append(
                await self._users.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    company_id=project.company_id,
                    project_id=project.id,
                )
            )
        return created
```

- [ ] **Step 6: Run the tests to verify they pass**

Run (inside `backend/`): `uv run pytest tests/integration/test_routers/test_admin_bulk_invite.py -v`
Expected: PASS (6 tests in `TestBulkInviteService`).

- [ ] **Step 7: Format, lint, commit**

```bash
cd backend && uv run poe format && uv run poe lint && cd ..
git add "AI ENABLEMENT HUB REBUILD/backend/src/repositories/base.py" \
        "AI ENABLEMENT HUB REBUILD/backend/src/repositories/user_repository.py" \
        "AI ENABLEMENT HUB REBUILD/backend/src/services/admin_user_service.py" \
        "AI ENABLEMENT HUB REBUILD/backend/tests/integration/test_routers/test_admin_bulk_invite.py"
git commit -m "feat: bulk-invite service + repository methods"
```

---

### Task 3: Bulk invite endpoint

**Files:**
- Modify: `backend/src/schemas/admin_users.py` (3 schemas)
- Modify: `backend/src/routers/admin_users.py` (endpoint + logger + imports)
- Test: `backend/tests/integration/test_routers/test_admin_bulk_invite.py` (add endpoint classes)

**Interfaces:**
- Consumes: `parse_invite_csv`, `build_preview`, `MAX_INVITE_CSV_BYTES` (Task 1); `AdminUserService.existing_emails`/`ensure_project`/`create_invited_users` (Task 2); existing `_invite_link`, `_email_the_link`, `_RATE_LIMITED`, `TokenService.issue_action_token`, `require_admin`.
- Produces: `POST /api/admin/invites/bulk` returning `BulkInviteReport`; schemas `BulkInviteRow`, `BulkInviteSummary`, `BulkInviteReport`.

- [ ] **Step 1: Add the response schemas**

In `backend/src/schemas/admin_users.py`, add to `__all__`: `"BulkInviteReport"`, `"BulkInviteRow"`, `"BulkInviteSummary"` (keep alphabetical). Then add near `LinkResponse`:

```python
class BulkInviteRow(BaseModel):
    row_number: int
    first_name: str
    last_name: str
    email: str
    # preview: valid | duplicate | invalid ; commit turns each "valid" into
    # "created" or "email_failed".
    status: Literal["valid", "duplicate", "invalid", "created", "email_failed"]
    detail: str | None = None


class BulkInviteSummary(BaseModel):
    total_rows: int
    valid: int
    duplicates: int
    invalid: int
    created: int  # 0 on dry_run
    email_failed: int  # 0 on dry_run


class BulkInviteReport(BaseModel):
    dry_run: bool
    project_id: uuid.UUID
    summary: BulkInviteSummary
    rows: list[BulkInviteRow]
```

- [ ] **Step 2: Write the failing endpoint tests**

Append to `backend/tests/integration/test_routers/test_admin_bulk_invite.py`. First extend the imports at the top of the file:

```python
from collections.abc import AsyncGenerator, Awaitable, Callable

from httpx import ASGITransport, AsyncClient

from src.core.dependencies.database import get_session
from src.core.dependencies.email import get_email_service
from src.core.dependencies.settings import get_settings
from src.main import app
from src.services.email_service import EmailSender, EmailService
from tests.fixtures.auth import auth_headers
from tests.fixtures.email import TEST_EMAIL, RaisingSender, RecordingSender
```

Then append these fixtures + test classes:

```python
_CSV = (
    "first_name,last_name,email\n"
    "Jan,Peeters,jan@acme.be\n"
    "Sofie,Maes,sofie@acme.be\n"
    ",Bad,bad@acme.be\n"  # invalid: missing first name
)


def _extract_invite_token(text: str) -> str:
    assert "/invite/" in text
    return text.rsplit("/invite/", 1)[1].split()[0].strip()


@pytest_asyncio.fixture
async def make_email_client(
    db_session: AsyncSession, test_settings,
) -> AsyncGenerator[Callable[[EmailSender], Awaitable[AsyncClient]]]:
    """conftest's client + a REAL EmailService whose outbound leg is a stub."""
    clients: list[AsyncClient] = []

    async def _make(sender: EmailSender) -> AsyncClient:
        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        service = EmailService(
            sender,
            sender_address=TEST_EMAIL.sender_address,
            app_url=test_settings.app.url,
            entra_enabled=False,
            invite_ttl_days=test_settings.auth.invite_ttl_days,
            reset_ttl_days=test_settings.auth.reset_ttl_days,
        )
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_email_service] = lambda: service
        c = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        clients.append(c)
        return c

    try:
        yield _make
    finally:
        app.dependency_overrides.clear()
        for c in clients:
            await c.aclose()


@pytest_asyncio.fixture
async def project(db_session: AsyncSession):
    company = await create_company(db_session, "Bulk Endpoint Co")
    return await create_project(db_session, company, "Bulk Endpoint Project")


@pytest_asyncio.fixture
async def headers(db_session: AsyncSession, test_settings) -> dict[str, str]:
    admin = await create_user(db_session, email="bulk-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


async def _upload(client, csv_text, project_id, *, dry_run, headers):
    return await client.post(
        "/api/admin/invites/bulk",
        files={"file": ("roster.csv", csv_text.encode("utf-8"), "text/csv")},
        data={"project_id": str(project_id), "dry_run": str(dry_run).lower()},
        headers=headers,
    )


class TestBulkInviteEndpoint:
    async def test_dry_run_previews_and_creates_nothing(
        self, make_email_client, project, headers, db_session,
    ) -> None:
        await create_user(db_session, email="sofie@acme.be")  # seeded duplicate
        sender = RecordingSender()
        client = await make_email_client(sender)
        resp = await _upload(client, _CSV, project.id, dry_run=True, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        s = data["summary"]
        assert (s["valid"], s["duplicates"], s["invalid"], s["created"]) == (1, 1, 1, 0)
        assert sender.messages == []
        listing = await client.get(f"/api/admin/users?project_id={project.id}", headers=headers)
        assert listing.json()["users"] == []  # nothing created in this project

    async def test_commit_creates_and_emails_valid_rows(
        self, make_email_client, project, headers, db_session,
    ) -> None:
        await create_user(db_session, email="sofie@acme.be")  # duplicate → skipped
        sender = RecordingSender()
        client = await make_email_client(sender)
        resp = await _upload(client, _CSV, project.id, dry_run=False, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert (s["created"], s["duplicates"], s["invalid"], s["email_failed"]) == (1, 1, 1, 0)
        [message] = sender.messages
        assert message["recipients"] == {"to": [{"address": "jan@acme.be"}]}
        # The emailed invite link is redeemable.
        info = await client.get(
            f"/api/auth/invite/{_extract_invite_token(message['content']['plainText'])}"
        )
        assert info.status_code == 200
        assert info.json()["purpose"] == "invite"
        # The created user now shows up in the project listing.
        listing = await client.get(f"/api/admin/users?project_id={project.id}", headers=headers)
        assert [u["email"] for u in listing.json()["users"]] == ["jan@acme.be"]

    async def test_failed_email_marks_row_but_still_creates_user(
        self, make_email_client, project, headers,
    ) -> None:
        client = await make_email_client(RaisingSender())
        csv_text = "first_name,last_name,email\nOnly,One,only@acme.be\n"
        resp = await _upload(client, csv_text, project.id, dry_run=False, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["email_failed"] == 1
        assert data["summary"]["created"] == 0
        row = next(r for r in data["rows"] if r["email"] == "only@acme.be")
        assert row["status"] == "email_failed"
        listing = await client.get(f"/api/admin/users?project_id={project.id}", headers=headers)
        assert [u["email"] for u in listing.json()["users"]] == ["only@acme.be"]

    async def test_email_disabled_still_creates_users(
        self, client: AsyncClient, project, headers,
    ) -> None:
        """Default conftest client has email=None (disabled): commit still
        creates the users and reports them as created."""
        csv_text = "first_name,last_name,email\nNo,Mail,nomail@acme.be\n"
        resp = await _upload(client, csv_text, project.id, dry_run=False, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["summary"]["created"] == 1

    async def test_oversize_file_is_413(self, client: AsyncClient, project, headers) -> None:
        big = "first_name,last_name,email\n" + ("x" * 1_048_600) + "\n"
        resp = await _upload(client, big, project.id, dry_run=True, headers=headers)
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "payload_too_large"

    async def test_too_many_rows_is_400(self, client: AsyncClient, project, headers) -> None:
        body = "first_name,last_name,email\n" + "".join(
            f"F{i},L{i},user{i}@acme.be\n" for i in range(201)
        )
        resp = await _upload(client, body, project.id, dry_run=True, headers=headers)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "bad_request"

    async def test_missing_column_is_400(self, client: AsyncClient, project, headers) -> None:
        resp = await _upload(
            client, "first_name,email\nJan,jan@acme.be\n", project.id, dry_run=True, headers=headers
        )
        assert resp.status_code == 400

    async def test_unknown_project_is_404(self, client: AsyncClient, headers) -> None:
        resp = await _upload(client, _CSV, uuid.uuid4(), dry_run=True, headers=headers)
        assert resp.status_code == 404

    async def test_requires_authentication(self, client: AsyncClient, project) -> None:
        resp = await _upload(client, _CSV, project.id, dry_run=True, headers={})
        assert resp.status_code == 401

    async def test_requires_admin(
        self, client: AsyncClient, project, db_session, test_settings,
    ) -> None:
        member = await create_user(db_session, email="bulk-member@example.com", role="user")
        resp = await _upload(
            client, _CSV, project.id, dry_run=True, headers=auth_headers(member, test_settings)
        )
        assert resp.status_code == 403
```

- [ ] **Step 3: Run the tests to verify they fail**

Run (inside `backend/`): `uv run pytest tests/integration/test_routers/test_admin_bulk_invite.py::TestBulkInviteEndpoint -v`
Expected: FAIL — 404/405 (route not defined) on every case.

- [ ] **Step 4: Implement the endpoint**

In `backend/src/routers/admin_users.py`:

(a) Add `import logging` at the top (with the other stdlib imports) and, after the `router = APIRouter(...)` line, add:

```python
logger = logging.getLogger(__name__)
```

(b) Extend the `fastapi` import to include the multipart helpers:

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
```

(c) Add these imports (runtime, not under TYPE_CHECKING — FastAPI inspects the annotations):

```python
from src.db.models import User
from src.schemas.admin_users import (
    BulkInviteReport,
    BulkInviteRow,
    BulkInviteSummary,
    # ...keep the existing names in this import block...
)
from src.services.exceptions import PayloadTooLargeError
from src.services.invite_csv import MAX_INVITE_CSV_BYTES, build_preview, parse_invite_csv
```

(d) Add the handler after `create_invite`:

```python
@router.post("/invites/bulk", response_model=BulkInviteReport)
async def create_bulk_invites(
    admin: Annotated[User, Depends(require_admin)],
    admin_user_service: AdminUserServiceDep,
    token_service: TokenServiceDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    email_service: EmailServiceDep,
    file: Annotated[UploadFile, File()],
    project_id: Annotated[uuid.UUID, Form()],
    dry_run: Annotated[bool, Form()] = False,
) -> BulkInviteReport:
    """Bulk-invite from a CSV (first_name,last_name,email). dry_run=true parses,
    validates and dedups against existing users, creating nothing — the admin's
    preview. dry_run=false additionally creates the valid users, mints their
    invite tokens and emails the links. Existing emails are skipped; a failed
    email leaves the user created (recover via the per-user reset link). The
    uploaded file is never persisted."""
    if file.size is not None and file.size > MAX_INVITE_CSV_BYTES:
        raise PayloadTooLargeError(MAX_INVITE_CSV_BYTES)
    raw = await file.read()
    if len(raw) > MAX_INVITE_CSV_BYTES:
        raise PayloadTooLargeError(MAX_INVITE_CSV_BYTES)

    await admin_user_service.ensure_project(project_id)  # 404 early, even on dry_run
    parsed = parse_invite_csv(raw)  # InvalidCsvError → 400
    existing = await admin_user_service.existing_emails([r.email for r in parsed if r.error is None])
    preview = build_preview(parsed, existing)

    if not dry_run:
        if limiter.is_limited(f"bulk_invite:{admin.id}"):
            raise _RATE_LIMITED
        valid_rows = [p for p in preview if p.status == "valid"]
        created = await admin_user_service.create_invited_users(
            project_id, [(p.first_name, p.last_name, p.email) for p in valid_rows]
        )
        created_by_email = {u.email: u for u in created}
        for p in valid_rows:
            user = created_by_email.get(p.email)
            if user is None:  # raced: created concurrently between preview and commit
                p.status, p.detail = "duplicate", "already registered"
                continue
            raw_token = await token_service.issue_action_token(user, "invite")
            link = _invite_link(settings, raw_token)
            email_status = await _email_the_link(
                email_service, purpose="invite", to=user.email,
                first_name=user.first_name, link=link,
            )
            if email_status == "failed":
                p.status, p.detail = "email_failed", "user created — email could not be sent"
            else:
                p.status, p.detail = "created", None
        logger.info(
            "bulk invite: admin=%s project=%s created=%d duplicates=%d invalid=%d email_failed=%d",
            admin.id, project_id,
            sum(p.status == "created" for p in preview),
            sum(p.status == "duplicate" for p in preview),
            sum(p.status == "invalid" for p in preview),
            sum(p.status == "email_failed" for p in preview),
        )

    summary = BulkInviteSummary(
        total_rows=len(preview),
        valid=sum(p.status == "valid" for p in preview),
        duplicates=sum(p.status == "duplicate" for p in preview),
        invalid=sum(p.status == "invalid" for p in preview),
        created=sum(p.status == "created" for p in preview),
        email_failed=sum(p.status == "email_failed" for p in preview),
    )
    return BulkInviteReport(
        dry_run=dry_run,
        project_id=project_id,
        summary=summary,
        rows=[BulkInviteRow(**vars(p)) for p in preview],
    )
```

- [ ] **Step 5: Run the endpoint tests to verify they pass**

Run (inside `backend/`): `uv run pytest tests/integration/test_routers/test_admin_bulk_invite.py -v`
Expected: PASS (service class + all `TestBulkInviteEndpoint` cases).

- [ ] **Step 6: Run the full backend suite (nothing regressed)**

Run (inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test`
Expected: all green, coverage ≥ 80%.

- [ ] **Step 7: Commit**

```bash
git add "AI ENABLEMENT HUB REBUILD/backend/src/schemas/admin_users.py" \
        "AI ENABLEMENT HUB REBUILD/backend/src/routers/admin_users.py" \
        "AI ENABLEMENT HUB REBUILD/backend/tests/integration/test_routers/test_admin_bulk_invite.py"
git commit -m "feat: POST /api/admin/invites/bulk endpoint"
```

---

### Task 4: Frontend multipart client helper

**Files:**
- Create: `frontend/src/api/bulkInvite.ts`

**Interfaces:**
- Consumes: `errorMessage`, `refreshAccessToken` (`api/client.ts`); `getAccessToken` (`api/tokens.ts`).
- Produces: `bulkInvite(file, projectId, dryRun) -> Promise<BulkInviteReport>`; types `BulkInviteRow`, `BulkInviteSummary`, `BulkInviteReport`; `class BulkInviteError`.

- [ ] **Step 1: Write the helper** (mirrors `api/upload.ts`'s auth + single-flight-refresh pattern; plain `fetch` since no upload-progress is needed)

Create `frontend/src/api/bulkInvite.ts`:

```ts
// Hand-typed multipart client for POST /api/admin/invites/bulk, mirroring
// api/upload.ts: attach the Bearer token, and on a 401 await the shared
// single-flight refresh and retry once. gen:api is skipped for multipart (same
// reasoning as upload.ts), so the response types are hand-kept in sync with the
// backend BulkInviteReport (schemas/admin_users.py).

import { errorMessage, refreshAccessToken } from './client'
import { getAccessToken } from './tokens'

export type BulkInviteStatus = 'valid' | 'duplicate' | 'invalid' | 'created' | 'email_failed'

export interface BulkInviteRow {
  row_number: number
  first_name: string
  last_name: string
  email: string
  status: BulkInviteStatus
  detail: string | null
}

export interface BulkInviteSummary {
  total_rows: number
  valid: number
  duplicates: number
  invalid: number
  created: number
  email_failed: number
}

export interface BulkInviteReport {
  dry_run: boolean
  project_id: string
  summary: BulkInviteSummary
  rows: BulkInviteRow[]
}

export class BulkInviteError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'BulkInviteError'
    this.status = status
  }
}

const ENDPOINT = '/api/admin/invites/bulk'

function send(file: File, projectId: string, dryRun: boolean, token: string | null): Promise<Response> {
  const form = new FormData()
  form.append('file', file)
  form.append('project_id', projectId)
  form.append('dry_run', String(dryRun))
  return fetch(ENDPOINT, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  })
}

export async function bulkInvite(
  file: File,
  projectId: string,
  dryRun: boolean,
): Promise<BulkInviteReport> {
  let res = await send(file, projectId, dryRun, getAccessToken())
  if (res.status === 401) {
    const access = await refreshAccessToken()
    if (!access) throw new BulkInviteError(401, 'Your session has expired. Please sign in again.')
    res = await send(file, projectId, dryRun, access)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    throw new BulkInviteError(res.status, errorMessage(body, 'Bulk invite failed. Please try again.'))
  }
  return body as BulkInviteReport
}
```

- [ ] **Step 2: Verify it compiles/lints**

Run (inside `frontend/`): `npm run typecheck && npm run lint`
Expected: clean (no errors).

- [ ] **Step 3: Commit**

```bash
git add "AI ENABLEMENT HUB REBUILD/frontend/src/api/bulkInvite.ts"
git commit -m "feat: bulk-invite frontend API helper"
```

---

### Task 5: Bulk invite modal + project-view wiring

**Files:**
- Create: `frontend/src/pages/admin/BulkInviteModal.tsx`
- Modify: `frontend/src/pages/admin/ProjectDetailView.tsx`

**Interfaces:**
- Consumes: `bulkInvite`, `BulkInviteError`, `BulkInviteReport`, `BulkInviteRow` (Task 4); `s` styles (`adminStyles.ts`); `onProjectRefresh` (existing `ProjectDetailView` handler prop).
- Produces: default-exported `BulkInviteModal` component.

- [ ] **Step 1: Write the modal**

Create `frontend/src/pages/admin/BulkInviteModal.tsx`:

```tsx
import { useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { bulkInvite, BulkInviteError, type BulkInviteReport, type BulkInviteRow } from '../../api/bulkInvite'
import { s } from './adminStyles'

interface Props {
  projectId: string
  projectName: string
  onClose: () => void
  onCommitted: () => void
}

type Phase = 'idle' | 'previewing' | 'preview' | 'committing' | 'done'

const STATUS_LABEL: Record<BulkInviteRow['status'], string> = {
  valid: 'will invite',
  duplicate: 'skip — exists',
  invalid: 'skip — invalid',
  created: 'invited',
  email_failed: 'created, email failed',
}

function badgeFor(status: BulkInviteRow['status']): CSSProperties {
  if (status === 'valid' || status === 'created') return s.badgeActive
  if (status === 'invalid' || status === 'email_failed') return { background: '#FFF0EF', color: '#C42828' }
  return s.badgeInvited // duplicate
}

function downloadTemplate() {
  const blob = new Blob(['first_name,last_name,email\n'], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'invite-template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function BulkInviteModal({ projectId, projectName, onClose, onCommitted }: Props) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [report, setReport] = useState<BulkInviteReport | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const fileRef = useRef<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function onPick(file: File) {
    fileRef.current = file
    setFileError(null)
    setPhase('previewing')
    try {
      const r = await bulkInvite(file, projectId, true)
      setReport(r)
      setPhase('preview')
    } catch (e) {
      setFileError(e instanceof BulkInviteError ? e.message : 'Could not read that file.')
      setPhase('idle')
    }
  }

  async function onConfirm() {
    if (!fileRef.current) return
    setPhase('committing')
    try {
      const r = await bulkInvite(fileRef.current, projectId, false)
      setReport(r)
      setPhase('done')
      onCommitted()
    } catch (e) {
      setFileError(e instanceof BulkInviteError ? e.message : 'Something went wrong sending invites.')
      setPhase('preview')
    }
  }

  const sum = report?.summary
  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <div style={s.tableHeader}>
          <p style={s.tableTitle}>Bulk invite to {projectName}</p>
          <button type="button" style={s.panelClose} onClick={onClose}>×</button>
        </div>

        <div style={{ padding: '20px 24px' }}>
          {(phase === 'idle' || phase === 'previewing') && (
            <>
              <p style={hint}>
                Download the template, fill it in (you can edit it in Excel — just use
                <b> File → Save As → CSV</b> when done), then upload it here. Columns:
                <b> first_name</b>, <b>last_name</b>, <b>email</b>. People already in the system
                are skipped automatically.
              </p>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14 }}>
                <button
                  type="button"
                  style={{ ...s.submitBtn, fontSize: 13, ...(phase === 'previewing' ? s.submitBtnDisabled : {}) }}
                  disabled={phase === 'previewing'}
                  onClick={() => inputRef.current?.click()}
                >
                  {phase === 'previewing' ? 'reading…' : 'choose CSV file'}
                </button>
                <button type="button" style={ghost} onClick={downloadTemplate}>↓ download template</button>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,text/csv"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) onPick(f)
                  e.target.value = ''
                }}
              />
              {fileError && <p style={errText}>{fileError}</p>}
            </>
          )}

          {(phase === 'preview' || phase === 'committing') && sum && report && (
            <>
              <p style={hint}>
                <b>{sum.valid}</b> will be invited · <b>{sum.duplicates}</b> already registered ·{' '}
                <b>{sum.invalid}</b> invalid — of {sum.total_rows} rows
              </p>
              {fileError && <p style={errText}>{fileError}</p>}
              <PreviewTable rows={report.rows} />
              <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                <button type="button" style={ghost} disabled={phase === 'committing'} onClick={() => setPhase('idle')}>
                  ← choose another file
                </button>
                <button
                  type="button"
                  style={{ ...s.submitBtn, ...(sum.valid === 0 || phase === 'committing' ? s.submitBtnDisabled : {}) }}
                  disabled={sum.valid === 0 || phase === 'committing'}
                  onClick={onConfirm}
                >
                  {phase === 'committing' ? 'sending…' : `confirm & send ${sum.valid} invite${sum.valid === 1 ? '' : 's'}`}
                </button>
              </div>
            </>
          )}

          {phase === 'done' && sum && report && (
            <>
              <p style={{ ...hint, color: '#1D7A52' }}>
                ✓ {sum.created} invited{sum.email_failed ? `, ${sum.email_failed} created but email failed` : ''} ·{' '}
                {sum.duplicates} skipped · {sum.invalid} invalid
              </p>
              {sum.email_failed > 0 && (
                <p style={hint}>
                  For the rows whose email failed, use the “reset link” button on that person in the
                  participants table to share a link manually.
                </p>
              )}
              <PreviewTable rows={report.rows} />
              <div style={{ marginTop: 16 }}>
                <button type="button" style={s.submitBtn} onClick={onClose}>done</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function PreviewTable({ rows }: { rows: BulkInviteRow[] }) {
  return (
    <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid #F0EFED', borderRadius: 8 }}>
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>Row</th>
            <th style={s.th}>Name</th>
            <th style={s.th}>Email</th>
            <th style={s.th}>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.row_number}>
              <td style={s.td}>{r.row_number}</td>
              <td style={s.td}>{r.first_name} {r.last_name}</td>
              <td style={s.td}>{r.email}</td>
              <td style={s.td}>
                <span style={{ ...s.badge, ...badgeFor(r.status) }}>{STATUS_LABEL[r.status]}</span>
                {r.detail ? <span style={{ fontSize: 11, color: '#8A8A8A', marginLeft: 6 }}>{r.detail}</span> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const overlay: CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,.18)', zIndex: 60,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}
const modal: CSSProperties = {
  width: 'min(720px, 94vw)', maxHeight: '88vh', overflowY: 'auto',
  background: '#fff', border: '1px solid #E2E2E2', borderRadius: 12,
}
const hint: CSSProperties = { fontSize: 13, color: '#3C3C3C', fontWeight: 300, lineHeight: 1.6, marginBottom: 14 }
const ghost: CSSProperties = {
  padding: '9px 16px', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
  color: '#8A8A8A', background: 'none', border: '1px solid #E2E2E2', borderRadius: 999, cursor: 'pointer',
}
const errText: CSSProperties = { fontSize: 13, color: '#C42828', marginTop: 6 }
```

- [ ] **Step 2: Wire the modal into ProjectDetailView**

In `frontend/src/pages/admin/ProjectDetailView.tsx`:

(a) Add the import after the existing `./adminHelpers` import:

```tsx
import BulkInviteModal from './BulkInviteModal'
```

(b) Add state next to the existing `inviteOpen` state (after line ~97):

```tsx
  const [bulkOpen, setBulkOpen] = useState(false)
```

(c) Replace the "invite toggle" block (the `<div>` that holds only the `+ Add participant` button) with one that adds a bulk button:

```tsx
      {/* invite toggle */}
      <div style={{ marginBottom: 20, display: 'flex', gap: 10, alignItems: 'center' }}>
        <button
          type="button"
          style={{ ...s.submitBtn, fontSize: 13, padding: '9px 20px' }}
          onClick={() => { setInviteOpen(o => !o); setFormMsg(null); setInviteLink(null) }}
        >
          {inviteOpen ? '× Cancel' : '+ Add participant'}
        </button>
        <button
          type="button"
          style={{ ...s.submitBtn, fontSize: 13, padding: '9px 20px', background: '#101820' }}
          onClick={() => setBulkOpen(true)}
        >
          ⇪ Bulk invite (CSV)
        </button>
      </div>
```

(d) Mount the modal just before the final closing `</div>` of the component's returned tree:

```tsx
      {bulkOpen && (
        <BulkInviteModal
          projectId={project.id}
          projectName={project.name}
          onClose={() => setBulkOpen(false)}
          onCommitted={() => onProjectRefresh?.()}
        />
      )}
```

- [ ] **Step 3: Verify it compiles, lints, and builds**

Run (inside `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add "AI ENABLEMENT HUB REBUILD/frontend/src/pages/admin/BulkInviteModal.tsx" \
        "AI ENABLEMENT HUB REBUILD/frontend/src/pages/admin/ProjectDetailView.tsx"
git commit -m "feat: bulk invite modal in the admin project view"
```

- [ ] **Step 5: Manual verification (real app)**

With the backend running against the dev DB and the frontend dev server up, sign in as an admin, open a project, click **Bulk invite (CSV)** and verify:
1. **Download template** → a file `invite-template.csv` with the header row.
2. Upload a small CSV mixing a valid row, an already-registered email, and a bad email → preview shows `will invite` / `skip — exists` / `skip — invalid` with correct counts, and **no** participant is added yet.
3. A semicolon-delimited file exported from Excel (with BOM) parses correctly (not one giant column).
4. **Confirm** → the valid users appear in the participants table (refreshed), and (dev `.env` has EMAIL__*) the invite email arrives.
5. Re-upload the same file → all rows now show `skip — exists`.
6. A malformed whole file (missing the email column) → red banner, nothing created.
7. Save the filled template as a native `.xlsx` and upload it → friendly banner telling them to Save As → CSV (not a cryptic encoding error).

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- Preview→confirm one-endpoint `dry_run` (Option A) → Task 3 endpoint. ✅
- CSV parsing: BOM, `,`/`;`, header order, extra columns, blank rows, in-file dedup → Task 1 + its tests. ✅
- Skip all existing → `existing_emails` + `build_preview` "duplicate" (Task 2/1), asserted in Task 3. ✅
- Per-row report + partial failure (email_failed, user still created) → Task 3 handler + test. ✅
- Guardrails: admin-only (Task 3 403/401 tests), file cap 1 MiB (413 test), row cap 200 (400 test), per-admin rate limit → Task 3. ✅
- File never persisted (in-memory `raw`, discarded) + audit log summary only → Task 3 handler. ✅
- Frontend template download + upload + preview + confirm + results + refresh → Tasks 4–5. ✅

**2. Placeholder scan** — no "TBD"/"handle errors"/"similar to"; every code + test step is complete. ✅

**3. Type consistency** — `PreviewRow.status` strings, `BulkInviteRow.status` `Literal`, and the TS `BulkInviteStatus` union all list exactly `valid | duplicate | invalid | created | email_failed`. `BulkInviteRow(**vars(p))` maps `PreviewRow`'s fields 1:1 to the pydantic model (same field names/order). `create_invited_users` takes `list[tuple[str, str, str]]` and the router passes `(p.first_name, p.last_name, p.email)`. `emails_in`/`existing_emails` both return `set[str]`. ✅

**4. Deviations noted** — frontend uses a hand-typed helper instead of `gen:api` (documented, matches `upload.ts`); whole-file CSV errors map to 400 `bad_request` via `InvalidCsvError(DomainError)` (no new exception handler needed). Both recorded above.
