# AI Chat Foundation ("Batch A" plumbing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared backend + frontend plumbing (LLM client seam, `conversations`/
`messages`/`project_ai_settings` tables, streaming chat endpoint, per-project AI paywall gate,
reusable chat UI) that the four AI features (chatbot/assessment/lesson/interview) will be built on
top of in later batches — nothing user-facing ships yet.

**Architecture:** Standard delaware layering (router → service → repository → model), extended
with a provider-agnostic `LlmClient` Protocol wrapping `AsyncAnthropic`. A new authz-style
dependency (`require_ai_surface`) gates the paid chat endpoint per-project, mirroring how
`require_admin` gates admin routes. Disconnect-safe persistence lives inside `ChatService`'s
streaming generator via a `finally` + `asyncio.shield`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, `anthropic` SDK (`AsyncAnthropic`),
`fastapi.sse` (`EventSourceResponse`/`ServerSentEvent`), React 18 + TypeScript, `openapi-fetch`.

## Global Constraints

- Backend layering is mandatory: router → service → repository → model, DI in
  `core/dependencies/` (`python-be-architecture.md`).
- No endpoint outside `/admin/*` accepts a user identifier from the request — ownership from the
  token only (the iron rule, `CLAUDE.md`).
- Async all the way down — `AsyncAnthropic`, never sync-in-threadpool.
- Backend checks: `cd backend && uv run poe format && uv run poe lint && uv run poe test` (≥80%
  coverage, ruff/ty clean) after every task.
- Frontend checks: `cd frontend && npm run typecheck && npm run lint && npm run build`.
- Migrations are never applied to any real DB without asking the user first
  (`feedback-azure-ask-first`); Phase 1/2 only ever create the migration **file**.
- Full design/reasoning lives in
  `docs/superpowers/specs/2026-07-23-ai-chat-foundation-design.md` — read it first if anything
  below is ambiguous.

---

## Phase 1 — Schema + settings/DI seam (no live model, no DB mutation)

### Task 1: `LlmSettings` + Anthropic dependency + Settings wiring

**Files:**
- Create: `backend/src/core/configs/llm.py`
- Modify: `backend/src/core/configs/settings.py` (add `llm: LlmSettings | None = None`)
- Modify: `backend/pyproject.toml` (add `anthropic` to `prod` optional-deps)
- Modify: `backend/tests/conftest.py` (`test_settings` fixture — add `llm=None`)
- Test: `backend/tests/unit/test_llm_settings.py`

**Interfaces:**
- Produces: `LlmSettings(provider: str, model: str, api_key: SecretStr)` — frozen `BaseModel`.
  `Settings.llm: LlmSettings | None`, env prefix `LLM__` (`LLM__PROVIDER`, `LLM__MODEL`,
  `LLM__API_KEY`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_llm_settings.py
from __future__ import annotations

from pydantic import SecretStr

from src.core.configs.llm import LlmSettings


def test_llm_settings_holds_secret_key() -> None:
    settings = LlmSettings(
        provider="anthropic", model="claude-haiku-4-5", api_key=SecretStr("sk-test")
    )
    assert settings.provider == "anthropic"
    assert settings.model == "claude-haiku-4-5"
    assert settings.api_key.get_secret_value() == "sk-test"
```

- [ ] **Step 2: Run test to verify it fails**

Run (inside `backend/`): `uv run pytest tests/unit/test_llm_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.configs.llm'`

- [ ] **Step 3: Write `LlmSettings`, wire into `Settings`, add the dependency**

```python
# backend/src/core/configs/llm.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["LlmSettings"]


class LlmSettings(BaseModel):
    """Anthropic API settings; env prefix `LLM__` (see Settings).

    All three fields are required: setting one `LLM__*` variable with the others
    missing must fail startup loudly, never half-enable the feature (mirrors
    EmailSettings).
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    model: str
    api_key: SecretStr
```

Edit `backend/src/core/configs/settings.py`: add `llm: LlmSettings | None = None` to the `Settings`
class body (mirror the existing `email: EmailSettings | None = None` line exactly — same file,
copy its placement) and import `LlmSettings` at the top.

Edit `backend/pyproject.toml`: in the `prod` optional-dependencies list (alongside `httptools`,
`asyncpg`), add `"anthropic"`.

Run `cd backend && uv sync --extra dev --extra prod` to install it.

Edit `backend/tests/conftest.py`'s `test_settings` fixture:
```python
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    # email=None/storage=None/llm=None explicitly: keeps tests hermetic (and away
    # from real ACS/Blob/Anthropic calls) even once the developer's backend/.env
    # carries EMAIL__*/STORAGE__*/LLM__* values.
    return Settings(
        auth=AuthSettings(jwt_secret=SecretStr("integration-test-jwt-secret-0123456789")),
        email=None,
        storage=None,
        llm=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/configs/llm.py backend/src/core/configs/settings.py backend/pyproject.toml backend/uv.lock backend/tests/conftest.py backend/tests/unit/test_llm_settings.py
git commit -m "feat(llm): add LlmSettings + anthropic dependency"
```

---

### Task 2: `LlmClient` Protocol + `AnthropicLlmClient` adapter

**Files:**
- Create: `backend/src/services/llm_service.py`
- Test: `backend/tests/fixtures/llm.py` (test doubles)
- Test: `backend/tests/unit/test_llm_service.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `LlmUsage(input_tokens: int, output_tokens: int)` — frozen dataclass.
  - `LlmReplyStream` Protocol: `__aiter__(self) -> AsyncIterator[str]`,
    `async def usage(self) -> LlmUsage`.
  - `LlmClient` Protocol: `def stream_reply(self, *, system: str, messages: list[dict[str, str]], max_tokens: int) -> AbstractAsyncContextManager[LlmReplyStream]`.
  - `AnthropicLlmClient(client: AsyncAnthropic, *, model: str)` implementing `LlmClient`.

- [ ] **Step 1: Write the failing test (fake Anthropic SDK shape → adapter)**

```python
# backend/tests/fixtures/llm.py
"""LLM test doubles: a FakeLlmClient mirroring tests/fixtures/email.py's
RecordingSender/RaisingSender pattern, plus a fake shaped like AsyncAnthropic's
`messages.stream(...)` for testing the adapter itself."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import TracebackType

from src.services.llm_service import LlmUsage

__all__ = [
    "FakeAnthropicMessage",
    "FakeAnthropicStream",
    "FakeAnthropicStreamManager",
    "FakeLlmClient",
    "RaisingLlmClient",
]


class FakeAnthropicMessage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.usage = type("Usage", (), {"input_tokens": input_tokens, "output_tokens": output_tokens})()


class FakeAnthropicStream:
    """Shaped like anthropic's MessageStream: `.text_stream` + `.get_final_message()`."""

    def __init__(self, chunks: list[str], usage: tuple[int, int]) -> None:
        self._chunks = chunks
        self._usage = usage

    @property
    async def text_stream(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk

    async def get_final_message(self) -> FakeAnthropicMessage:
        return FakeAnthropicMessage(*self._usage)


class FakeAnthropicStreamManager:
    """Shaped like `client.messages.stream(...)`'s return value: an async context
    manager that yields a FakeAnthropicStream."""

    def __init__(self, chunks: list[str], usage: tuple[int, int]) -> None:
        self._stream = FakeAnthropicStream(chunks, usage)

    async def __aenter__(self) -> FakeAnthropicStream:
        return self._stream

    async def __aexit__(self, *exc: object) -> None:
        return None


class _FakeMessages:
    def __init__(self, chunks: list[str], usage: tuple[int, int]) -> None:
        self._chunks = chunks
        self._usage = usage

    def stream(self, **_: object) -> FakeAnthropicStreamManager:
        return FakeAnthropicStreamManager(self._chunks, self._usage)


class FakeAsyncAnthropic:
    """A fake shaped exactly like `AsyncAnthropic` for `AnthropicLlmClient` tests."""

    def __init__(self, chunks: list[str], usage: tuple[int, int] = (10, 5)) -> None:
        self.messages = _FakeMessages(chunks, usage)


class FakeLlmReplyStream:
    def __init__(self, chunks: list[str], usage: LlmUsage) -> None:
        self._chunks = chunks
        self._usage = usage

    async def __aenter__(self) -> FakeLlmReplyStream:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        return None

    async def __aiter__(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk

    async def usage(self) -> LlmUsage:
        return self._usage


class FakeLlmClient:
    """Stubs LlmClient: streams canned chunks, reports canned usage."""

    def __init__(self, chunks: list[str], usage: LlmUsage | None = None) -> None:
        self.chunks = chunks
        self.usage_value = usage or LlmUsage(input_tokens=10, output_tokens=len(chunks))
        self.calls: list[dict[str, object]] = []

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> FakeLlmReplyStream:
        self.calls.append({"system": system, "messages": messages, "max_tokens": max_tokens})
        return FakeLlmReplyStream(self.chunks, self.usage_value)


class RaisingLlmClient:
    """Every call blows up (dead Anthropic endpoint, bad key, ...)."""

    def stream_reply(self, **_: object) -> FakeLlmReplyStream:
        msg = "Anthropic API unreachable"
        raise RuntimeError(msg)
```

```python
# backend/tests/unit/test_llm_service.py
from __future__ import annotations

from tests.fixtures.llm import FakeAsyncAnthropic

from src.services.llm_service import AnthropicLlmClient


async def test_anthropic_client_streams_chunks_and_reports_usage() -> None:
    fake_sdk = FakeAsyncAnthropic(chunks=["Hel", "lo!"], usage=(12, 3))
    client = AnthropicLlmClient(fake_sdk, model="claude-haiku-4-5")

    collected: list[str] = []
    async with client.stream_reply(
        system="You are helpful.", messages=[{"role": "user", "content": "hi"}], max_tokens=1024
    ) as reply:
        async for chunk in reply:
            collected.append(chunk)
        usage = await reply.usage()

    assert collected == ["Hel", "lo!"]
    assert usage.input_tokens == 12
    assert usage.output_tokens == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_llm_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.services.llm_service'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/services/llm_service.py
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

__all__ = ["AnthropicLlmClient", "LlmClient", "LlmReplyStream", "LlmUsage"]


@dataclass(frozen=True)
class LlmUsage:
    input_tokens: int
    output_tokens: int


class LlmReplyStream(Protocol):
    """Async-iterate for text deltas; call `usage()` only after the iterator is
    fully exhausted (mirrors AsyncAnthropic's `stream.get_final_message()`)."""

    async def __aenter__(self) -> LlmReplyStream: ...
    async def __aexit__(self, *exc: object) -> None: ...
    def __aiter__(self) -> AsyncIterator[str]: ...
    async def usage(self) -> LlmUsage: ...


class LlmClient(Protocol):
    """The seam: tests stub this, `AnthropicLlmClient` is the only real
    implementation for now (see docs/ai-agents-plan.md §7 for the provider
    decision and the Foundry-adapter option kept open by this Protocol)."""

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> LlmReplyStream: ...


class _AnthropicReplyStream:
    """Adapts anthropic's `client.messages.stream(...)` async-context-manager
    (`.text_stream` / `.get_final_message()`) to the `LlmReplyStream` shape."""

    def __init__(self, manager: object) -> None:
        self._manager = manager
        self._stream: object | None = None

    async def __aenter__(self) -> _AnthropicReplyStream:
        self._stream = await self._manager.__aenter__()  # type: ignore[attr-defined]
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._manager.__aexit__(*exc)  # type: ignore[attr-defined]

    async def __aiter__(self) -> AsyncIterator[str]:
        assert self._stream is not None
        async for chunk in self._stream.text_stream:  # type: ignore[attr-defined]
            yield chunk

    async def usage(self) -> LlmUsage:
        assert self._stream is not None
        final = await self._stream.get_final_message()  # type: ignore[attr-defined]
        return LlmUsage(final.usage.input_tokens, final.usage.output_tokens)


class AnthropicLlmClient:
    """Thin wrapper over `AsyncAnthropic` — mirrors how EmailService wraps ACS."""

    def __init__(self, client: AsyncAnthropic, *, model: str) -> None:
        self._client = client
        self._model = model

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> _AnthropicReplyStream:
        manager = self._client.messages.stream(
            model=self._model, max_tokens=max_tokens, system=system, messages=messages
        )
        return _AnthropicReplyStream(manager)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/llm_service.py backend/tests/fixtures/llm.py backend/tests/unit/test_llm_service.py
git commit -m "feat(llm): add LlmClient Protocol + AnthropicLlmClient adapter"
```

---

### Task 3: `get_llm_service` DI

**Files:**
- Create: `backend/src/core/dependencies/llm.py`
- Test: `backend/tests/unit/test_llm_dependency.py`

**Interfaces:**
- Consumes: `LlmSettings` (Task 1), `AnthropicLlmClient` (Task 2).
- Produces: `get_llm_service(settings: Settings) -> AnthropicLlmClient | None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_llm_dependency.py
from __future__ import annotations

from pydantic import SecretStr

from src.core.configs.llm import LlmSettings
from src.core.configs.settings import Settings
from src.core.configs.auth import AuthSettings
from src.core.dependencies.llm import get_llm_service
from src.services.llm_service import AnthropicLlmClient


def _settings(llm: LlmSettings | None) -> Settings:
    return Settings(
        auth=AuthSettings(jwt_secret=SecretStr("x" * 20)), email=None, storage=None, llm=llm
    )


def test_returns_none_when_unconfigured() -> None:
    assert get_llm_service(_settings(None)) is None


def test_returns_client_when_configured() -> None:
    settings = _settings(
        LlmSettings(provider="anthropic", model="claude-haiku-4-5", api_key=SecretStr("sk-test"))
    )
    service = get_llm_service(settings)
    assert isinstance(service, AnthropicLlmClient)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_llm_dependency.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.dependencies.llm'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/core/dependencies/llm.py
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from anthropic import AsyncAnthropic
from fastapi import Depends

from src.core.configs.settings import Settings
from src.core.dependencies.settings import get_settings
from src.services.llm_service import AnthropicLlmClient

__all__ = ["get_llm_service"]


@lru_cache
def _anthropic_client(api_key: str) -> AsyncAnthropic:
    """Process-lifetime client, mirrors _email_client's @lru_cache pattern."""
    return AsyncAnthropic(api_key=api_key)


def get_llm_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnthropicLlmClient | None:
    """None when LLM__* is unconfigured — the chat router 404s in that case
    (mirrors EntraService's all-or-nothing pattern, not EmailService's, because
    chat has no meaning without a model)."""
    if settings.llm is None:
        return None
    return AnthropicLlmClient(
        _anthropic_client(settings.llm.api_key.get_secret_value()), model=settings.llm.model
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_dependency.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/dependencies/llm.py backend/tests/unit/test_llm_dependency.py
git commit -m "feat(llm): add get_llm_service DI provider"
```

---

### Task 4: `Conversation` + `Message` models

**Files:**
- Create: `backend/src/db/models/conversation.py`
- Modify: `backend/src/db/models/__init__.py`
- Test: `backend/tests/integration/test_models/test_conversation.py`

**Interfaces:**
- Produces: `Conversation(id, user_id, kind, context_ref, summary, created_at, updated_at)`,
  `Message(id, conversation_id, role, content, metadata, created_at)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_models/test_conversation.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.db.models import Conversation, Message
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_conversation_and_message_round_trip(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="chat-model@example.com")

    conversation = Conversation(user_id=user.id, kind="chatbot")
    db_session.add(conversation)
    await db_session.flush()

    message = Message(conversation_id=conversation.id, role="user", content="hi")
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(conversation)
    await db_session.refresh(message)

    assert conversation.context_ref is None
    assert conversation.summary is None
    assert message.metadata is None
    assert message.role == "user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_models/test_conversation.py -v`
Expected: FAIL — `ImportError: cannot import name 'Conversation' from 'src.db.models'`

- [ ] **Step 3: Write the models + register them**

```python
# backend/src/db/models/conversation.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["Conversation", "Message"]

_KINDS = "'chatbot', 'assessment', 'lesson', 'interview'"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (CheckConstraint(f"kind IN ({_KINDS})", name="kind"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    # lesson_id or survey question id; text because it's polymorphic across
    # kinds, not a single-target FK.
    context_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Interviewer's structured extraction (Batch C) — unused by this batch.
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="role"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Token counts, model id, truncated flag.
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

Note: the Python attribute is `metadata_` (mapped to the real column name `"metadata"` via
`mapped_column("metadata", ...)`) because `metadata` is a reserved attribute name on SQLAlchemy's
`DeclarativeBase` (`Base.metadata` is the schema registry) — using it directly would shadow that
and break the ORM. Every place that reads/writes this column in later tasks uses `message.metadata_`.

Edit `backend/src/db/models/__init__.py`: add
`from src.db.models.conversation import Conversation, Message` and add `"Conversation"`,
`"Message"` to `__all__` (alphabetical, matching the existing style).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_models/test_conversation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/db/models/conversation.py backend/src/db/models/__init__.py backend/tests/integration/test_models/test_conversation.py
git commit -m "feat(chat): add Conversation and Message models"
```

---

### Task 5: `ProjectAiSetting` model

**Files:**
- Modify: `backend/src/db/models/company.py`
- Modify: `backend/src/db/models/__init__.py`
- Test: `backend/tests/integration/test_models/test_project_ai_setting.py`

**Interfaces:**
- Produces: `ProjectAiSetting(id, project_id, kind, enabled)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_models/test_project_ai_setting.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.db.models import ProjectAiSetting
from tests.fixtures.factories import create_company, create_project

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_defaults_to_disabled(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "AI Setting Co")
    project = await create_project(db_session, company, "AI Setting Project")

    setting = ProjectAiSetting(project_id=project.id, kind="chatbot")
    db_session.add(setting)
    await db_session.commit()
    await db_session.refresh(setting)

    assert setting.enabled is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_models/test_project_ai_setting.py -v`
Expected: FAIL — `ImportError: cannot import name 'ProjectAiSetting'`

- [ ] **Step 3: Add the model**

Append to `backend/src/db/models/company.py` (add `"ProjectAiSetting"` to the existing `__all__`):

```python
class ProjectAiSetting(Base):
    """Per-project paid-feature gate for the 4 AI chat surfaces — a hard
    enforcement gate, NOT the visibility-only pattern ProjectComponentSetting
    uses (see the design doc's rationale)."""

    __tablename__ = "project_ai_settings"
    __table_args__ = (
        UniqueConstraint("project_id", "kind"),
        CheckConstraint(
            "kind IN ('chatbot', 'assessment', 'lesson', 'interview')", name="kind"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
```

Edit `backend/src/db/models/__init__.py`: add `ProjectAiSetting` to the `company` import line and
to `__all__` (alphabetical).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_models/test_project_ai_setting.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/db/models/company.py backend/src/db/models/__init__.py backend/tests/integration/test_models/test_project_ai_setting.py
git commit -m "feat(chat): add ProjectAiSetting model (per-project AI paywall gate)"
```

---

### Task 6: Abstract + concrete `Conversation`/`Message` repositories

**Files:**
- Modify: `backend/src/repositories/base.py`
- Create: `backend/src/repositories/conversation_repository.py`
- Create: `backend/src/repositories/message_repository.py`
- Test: `backend/tests/integration/test_repositories/test_conversation_repository.py`
- Test: `backend/tests/integration/test_repositories/test_message_repository.py`

**Interfaces:**
- Produces:
  - `AbstractConversationRepository`: `create(*, user_id, kind, context_ref=None) -> Conversation`,
    `get_by_id(conversation_id) -> Conversation | None`,
    `list_for_user(user_id, kind) -> list[Conversation]`, `touch(conversation_id) -> None`.
  - `AbstractMessageRepository`: `create(conversation_id, *, role, content, metadata) -> Message`,
    `list_for_conversation(conversation_id) -> list[Message]`,
    `list_recent(conversation_id, *, limit) -> list[Message]` (chronological order, last `limit`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integration/test_repositories/test_conversation_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.conversation_repository import ConversationRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_and_get_by_id(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo@example.com")
    repo = ConversationRepository(db_session)

    created = await repo.create(user_id=user.id, kind="chatbot")
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.kind == "chatbot"


async def test_list_for_user_filters_by_kind(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo-2@example.com")
    repo = ConversationRepository(db_session)
    await repo.create(user_id=user.id, kind="chatbot")
    await repo.create(user_id=user.id, kind="lesson")

    chatbot_only = await repo.list_for_user(user.id, "chatbot")

    assert len(chatbot_only) == 1
    assert chatbot_only[0].kind == "chatbot"


async def test_touch_updates_updated_at(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo-3@example.com")
    repo = ConversationRepository(db_session)
    created = await repo.create(user_id=user.id, kind="chatbot")
    original = created.updated_at

    await repo.touch(created.id)
    refreshed = await repo.get_by_id(created.id)

    assert refreshed is not None
    assert refreshed.updated_at >= original
```

```python
# backend/tests/integration/test_repositories/test_message_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_and_list_for_conversation(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="msg-repo@example.com")
    conversations = ConversationRepository(db_session)
    messages = MessageRepository(db_session)
    conversation = await conversations.create(user_id=user.id, kind="chatbot")

    await messages.create(conversation.id, role="user", content="hi", metadata=None)
    await messages.create(
        conversation.id, role="assistant", content="hello!", metadata={"truncated": False}
    )

    rows = await messages.list_for_conversation(conversation.id)

    assert [m.role for m in rows] == ["user", "assistant"]
    assert rows[1].metadata_ == {"truncated": False}


async def test_list_recent_returns_last_n_in_chronological_order(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="msg-repo-2@example.com")
    conversations = ConversationRepository(db_session)
    messages = MessageRepository(db_session)
    conversation = await conversations.create(user_id=user.id, kind="chatbot")
    for i in range(5):
        await messages.create(conversation.id, role="user", content=f"msg {i}", metadata=None)

    recent = await messages.list_recent(conversation.id, limit=2)

    assert [m.content for m in recent] == ["msg 3", "msg 4"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_repositories/test_conversation_repository.py tests/integration/test_repositories/test_message_repository.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the abstract + concrete repositories**

Append to `backend/src/repositories/base.py` (add both to `__all__`, alphabetical; add
`Conversation`, `Message` to the `TYPE_CHECKING` import block from `src.db.models`):

```python
class AbstractConversationRepository(ABC):
    """conversations — one row per chat session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self, *, user_id: uuid.UUID, kind: str, context_ref: str | None = None
    ) -> Conversation: ...

    @abstractmethod
    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: uuid.UUID, kind: str) -> list[Conversation]:
        """Newest-first, for the history list."""

    @abstractmethod
    async def touch(self, conversation_id: uuid.UUID) -> None:
        """Bump updated_at (a child message insert doesn't do this automatically)."""


class AbstractMessageRepository(ABC):
    """messages — every chat turn, both sides (the 'save all dialogue' table)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self, conversation_id: uuid.UUID, *, role: str, content: str, metadata: dict[str, Any] | None
    ) -> Message: ...

    @abstractmethod
    async def list_for_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        """Chronological, for the conversation-detail view."""

    @abstractmethod
    async def list_recent(self, conversation_id: uuid.UUID, *, limit: int) -> list[Message]:
        """Last `limit` messages, chronological order (window cap sent to the model)."""
```

```python
# backend/src/repositories/conversation_repository.py
from __future__ import annotations

import uuid

from sqlalchemy import func, select, update

from src.db.models import Conversation
from src.repositories.base import AbstractConversationRepository

__all__ = ["ConversationRepository"]


class ConversationRepository(AbstractConversationRepository):
    async def create(
        self, *, user_id: uuid.UUID, kind: str, context_ref: str | None = None
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, kind=kind, context_ref=context_ref)
        self._session.add(conversation)
        await self._session.commit()
        await self._session.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID, kind: str) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.kind == kind)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def touch(self, conversation_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )
        await self._session.commit()
```

```python
# backend/src/repositories/message_repository.py
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from src.db.models import Message
from src.repositories.base import AbstractMessageRepository

__all__ = ["MessageRepository"]


class MessageRepository(AbstractMessageRepository):
    async def create(
        self, conversation_id: uuid.UUID, *, role: str, content: str, metadata: dict[str, Any] | None
    ) -> Message:
        message = Message(
            conversation_id=conversation_id, role=role, content=content, metadata_=metadata
        )
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def list_for_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_recent(self, conversation_id: uuid.UUID, *, limit: int) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_repositories/test_conversation_repository.py tests/integration/test_repositories/test_message_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/repositories/base.py backend/src/repositories/conversation_repository.py backend/src/repositories/message_repository.py backend/tests/integration/test_repositories/test_conversation_repository.py backend/tests/integration/test_repositories/test_message_repository.py
git commit -m "feat(chat): add Conversation and Message repositories"
```

---

### Task 7: Alembic migration (all 3 tables)

**Files:**
- Create: `backend/alembic/versions/<new_revision>_chat_foundation.py`

**Interfaces:**
- Produces: `conversations`, `messages`, `project_ai_settings` tables in the DB schema.

- [ ] **Step 1: Confirm the current migration head**

Run (inside `backend/`): `uv run alembic heads`
Record the output — that revision id is this migration's `down_revision`. Do not guess it from
this plan or from `CLAUDE.md`'s "current state" section (it may have drifted).

- [ ] **Step 2: Generate and review the migration**

Run: `uv run poe migrate m="chat foundation"` (autogenerate). Open the generated file under
`backend/alembic/versions/` and replace its `upgrade()`/`downgrade()` with the explicit version
below (autogenerate sometimes orders columns/constraints differently than intended — review
before trusting it, per `python-be-architecture.md`). Keep the autogenerated `revision`/
`down_revision` values, just replace the body:

```python
"""chat foundation — conversations, messages, project_ai_settings

New tables for the AI chat feature's shared foundation (see
docs/superpowers/specs/2026-07-23-ai-chat-foundation-design.md): conversations
+ messages persist every chat turn; project_ai_settings is a per-project
paywall gate (hard enforcement, not the visibility-only pattern
project_component_settings uses).

Revision ID: <keep autogenerated>
Revises: <keep autogenerated — must equal the `alembic heads` output from Step 1>
Create Date: 2026-07-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "<keep autogenerated>"
down_revision: str | None = "<keep autogenerated>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("context_ref", sa.Text(), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('chatbot', 'assessment', 'lesson', 'interview')", name=op.f("ck_conversations_kind")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_conversations_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')", name=op.f("ck_messages_role")
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_messages_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)

    op.create_table(
        "project_ai_settings",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('chatbot', 'assessment', 'lesson', 'interview')",
            name=op.f("ck_project_ai_settings_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_ai_settings_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_ai_settings")),
        sa.UniqueConstraint(
            "project_id", "kind", name=op.f("uq_project_ai_settings_project_id_kind")
        ),
    )


def downgrade() -> None:
    op.drop_table("project_ai_settings")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_table("conversations")
```

- [ ] **Step 3: Sanity-check against the integration test DB (NOT the dev/prod DB)**

The existing `tests/conftest.py::engine` fixture creates all tables from `Base.metadata` directly
(no Alembic involved) — so Tasks 4-6's tests already prove the models work. This migration file
itself is only exercised for real when `poe upgrade` runs against an actual Postgres instance,
which is gated behind user approval (Phase 3). **Do not run `poe upgrade` in this task.**

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(chat): add migration for conversations, messages, project_ai_settings"
```

---

## Phase 2 — Service + router + AI-enablement gate + guardrails + automated tests

### Task 8: `OrgRepository`/`OrgService` AI-settings methods

**Files:**
- Modify: `backend/src/repositories/base.py` (`AbstractOrgRepository` additions)
- Modify: `backend/src/repositories/org_repository.py`
- Modify: `backend/src/services/org_service.py`
- Test: `backend/tests/integration/test_repositories/test_org_repository.py` (extend if it exists,
  else create following the existing repo test conventions)
- Test: `backend/tests/unit/test_org_service.py` (extend if it exists, else create)

**Interfaces:**
- Produces:
  - `AbstractOrgRepository.get_ai_settings(project_id) -> list[ProjectAiSetting]`,
    `.upsert_ai_setting(project_id, kind, *, enabled) -> None`.
  - `OrgService.resolve_ai_settings(project_id: uuid.UUID | None) -> dict[str, bool]` (all 4
    kinds, `False` fallback for missing rows — mirrors `resolve_components`).
  - `OrgService.set_ai_surface(project_id, kind, *, enabled: bool) -> None` (404 if project
    unknown — mirrors `set_component`).

- [ ] **Step 1: Write the failing tests**

```python
# add to backend/tests/integration/test_repositories/test_org_repository.py
from src.db.models import ProjectAiSetting  # add to existing imports
from src.repositories.org_repository import OrgRepository  # if not already imported


async def test_get_ai_settings_empty_by_default(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "Org Repo AI Co")
    project = await create_project(db_session, company, "Org Repo AI Project")
    repo = OrgRepository(db_session)

    assert await repo.get_ai_settings(project.id) == []


async def test_upsert_ai_setting_then_get(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "Org Repo AI Co 2")
    project = await create_project(db_session, company, "Org Repo AI Project 2")
    repo = OrgRepository(db_session)

    await repo.upsert_ai_setting(project.id, "chatbot", enabled=True)
    rows = await repo.get_ai_settings(project.id)

    assert len(rows) == 1
    assert rows[0].kind == "chatbot"
    assert rows[0].enabled is True

    # upsert again flips it, doesn't duplicate the row
    await repo.upsert_ai_setting(project.id, "chatbot", enabled=False)
    rows = await repo.get_ai_settings(project.id)
    assert len(rows) == 1
    assert rows[0].enabled is False
```

```python
# add to backend/tests/unit/test_org_service.py
import uuid
from unittest.mock import AsyncMock
from types import SimpleNamespace

from src.repositories.base import AbstractOrgRepository
from src.services.exceptions import NotFoundError
from src.services.org_service import OrgService


async def test_resolve_ai_settings_defaults_all_four_to_false() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_ai_settings.return_value = []
    service = OrgService(org)

    settings = await service.resolve_ai_settings(uuid.uuid4())

    assert settings == {"chatbot": False, "assessment": False, "lesson": False, "interview": False}


async def test_resolve_ai_settings_none_project_id_is_all_false() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    service = OrgService(org)

    settings = await service.resolve_ai_settings(None)

    assert settings == {"chatbot": False, "assessment": False, "lesson": False, "interview": False}
    org.get_ai_settings.assert_not_awaited()


async def test_resolve_ai_settings_reflects_stored_rows() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_ai_settings.return_value = [SimpleNamespace(kind="chatbot", enabled=True)]
    service = OrgService(org)

    settings = await service.resolve_ai_settings(uuid.uuid4())

    assert settings["chatbot"] is True
    assert settings["lesson"] is False


async def test_set_ai_surface_unknown_project_raises_not_found() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_project.return_value = None
    service = OrgService(org)

    with pytest.raises(NotFoundError):
        await service.set_ai_surface(uuid.uuid4(), "chatbot", enabled=True)
```

(add `import pytest` at the top of `test_org_service.py` if not already present)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_repositories/test_org_repository.py tests/unit/test_org_service.py -v -k "ai_setting or ai_surface"`
Expected: FAIL — `AttributeError: 'OrgRepository' object has no attribute 'get_ai_settings'` (and
similar for the service methods)

- [ ] **Step 3: Implement**

Append to `AbstractOrgRepository` in `backend/src/repositories/base.py` (add `ProjectAiSetting` to
the `TYPE_CHECKING` import from `src.db.models`):

```python
    @abstractmethod
    async def get_ai_settings(self, project_id: uuid.UUID) -> list[ProjectAiSetting]: ...

    @abstractmethod
    async def upsert_ai_setting(self, project_id: uuid.UUID, kind: str, *, enabled: bool) -> None: ...
```

Append to `backend/src/repositories/org_repository.py` (add `ProjectAiSetting` to the import from
`src.db.models`):

```python
    async def get_ai_settings(self, project_id: uuid.UUID) -> list[ProjectAiSetting]:
        result = await self._session.execute(
            select(ProjectAiSetting).where(ProjectAiSetting.project_id == project_id)
        )
        return list(result.scalars().all())

    async def upsert_ai_setting(self, project_id: uuid.UUID, kind: str, *, enabled: bool) -> None:
        stmt = pg_insert(ProjectAiSetting).values(project_id=project_id, kind=kind, enabled=enabled)
        stmt = stmt.on_conflict_do_update(
            index_elements=["project_id", "kind"], set_={"enabled": stmt.excluded.enabled}
        )
        await self._session.execute(stmt)
        await self._session.commit()
```

Append to `backend/src/services/org_service.py` (add `"chatbot", "assessment", "lesson",
"interview"` as a module-level `_AI_KINDS` tuple near the top, alongside the existing imports):

```python
_AI_KINDS = ("chatbot", "assessment", "lesson", "interview")
```

```python
    async def resolve_ai_settings(self, project_id: uuid.UUID | None) -> dict[str, bool]:
        """enabled per AI kind, False fallback for missing rows or no project."""
        if project_id is None:
            return dict.fromkeys(_AI_KINDS, False)
        rows = await self._org.get_ai_settings(project_id)
        by_kind = {row.kind: row.enabled for row in rows}
        return {kind: by_kind.get(kind, False) for kind in _AI_KINDS}

    async def set_ai_surface(self, project_id: uuid.UUID, kind: str, *, enabled: bool) -> None:
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        await self._org.upsert_ai_setting(project_id, kind, enabled=enabled)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_repositories/test_org_repository.py tests/unit/test_org_service.py -v -k "ai_setting or ai_surface"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/repositories/base.py backend/src/repositories/org_repository.py backend/src/services/org_service.py backend/tests/integration/test_repositories/test_org_repository.py backend/tests/unit/test_org_service.py
git commit -m "feat(chat): add per-project AI-settings methods to OrgRepository/OrgService"
```

---

### Task 9: `schemas/chat.py` + admin AI-settings schemas

**Files:**
- Create: `backend/src/schemas/chat.py`
- Modify: `backend/src/schemas/admin_org.py`
- Test: `backend/tests/unit/test_chat_schema.py`

**Interfaces:**
- Produces: `ChatMessageCreate(content: str, conversation_id: uuid.UUID | None)`,
  `ConversationSummary`, `MessageResponse`, `ConversationListResponse`,
  `ConversationDetailResponse`; `AiSurfaceState(enabled: bool)`, `AiSettingsResponse`,
  `AiSurfaceUpdateRequest(enabled: bool)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_chat_schema.py
from __future__ import annotations

import pytest

from src.schemas.chat import ChatMessageCreate


def test_blank_content_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        ChatMessageCreate(content="   ", conversation_id=None)


def test_oversized_content_is_rejected() -> None:
    with pytest.raises(ValueError, match="4000"):
        ChatMessageCreate(content="x" * 4001, conversation_id=None)


def test_content_is_stripped() -> None:
    body = ChatMessageCreate(content="  hi  ", conversation_id=None)
    assert body.content == "hi"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_chat_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.schemas.chat'`

- [ ] **Step 3: Implement**

```python
# backend/src/schemas/chat.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = [
    "ChatMessageCreate",
    "ConversationDetailResponse",
    "ConversationListResponse",
    "ConversationSummary",
    "MessageResponse",
]


class ChatMessageCreate(BaseModel):
    content: str
    conversation_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "content must not be empty"
            raise ValueError(msg)
        if len(stripped) > 4000:
            msg = "content must be at most 4000 characters"
            raise ValueError(msg)
        return stripped


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    context_ref: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationDetailResponse(BaseModel):
    conversation: ConversationSummary
    messages: list[MessageResponse]
```

Append to `backend/src/schemas/admin_org.py` (add to `__all__`):

```python
class AiSurfaceState(BaseModel):
    enabled: bool


class AiSettingsResponse(BaseModel):
    settings: dict[str, AiSurfaceState]


class AiSurfaceUpdateRequest(BaseModel):
    enabled: bool
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_chat_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/schemas/chat.py backend/src/schemas/admin_org.py backend/tests/unit/test_chat_schema.py
git commit -m "feat(chat): add chat and admin AI-settings schemas"
```

---

### Task 10: `ChatService`

**Files:**
- Create: `backend/src/services/chat_service.py`
- Create: `backend/src/services/prompts.py`
- Create: `backend/prompts/chatbot.md`, `backend/prompts/assessment.md`,
  `backend/prompts/lesson.md`, `backend/prompts/interview.md`
- Test: `backend/tests/unit/test_chat_service.py`

**Interfaces:**
- Consumes: `AbstractConversationRepository`, `AbstractMessageRepository` (Task 6), `LlmClient`
  (Task 2), `load_prompt(kind: str) -> str` (this task).
- Produces: `ChatService.resolve_conversation(*, user_id, kind, conversation_id) -> Conversation`
  (raises `NotFoundError` if `conversation_id` is set but unknown/not the caller's).
  `ChatService.send_message(*, conversation: Conversation, content: str) -> AsyncIterator[ChatStreamEvent]`
  where `ChatStreamEvent = TokenEvent(text: str) | DoneEvent(conversation_id, truncated, usage: LlmUsage) `.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_chat_service.py
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.services.chat_service import ChatService, DoneEvent, TokenEvent
from src.services.exceptions import NotFoundError
from tests.fixtures.llm import FakeLlmClient


def _service(llm: FakeLlmClient) -> tuple[ChatService, AsyncMock, AsyncMock]:
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    messages.list_recent.return_value = []
    return ChatService(conversations, messages, llm), conversations, messages


async def test_resolve_conversation_creates_new_when_no_id() -> None:
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    conversations.create.return_value = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
    user_id = uuid.uuid4()

    conversation = await service.resolve_conversation(
        user_id=user_id, kind="chatbot", conversation_id=None
    )

    conversations.create.assert_awaited_once_with(user_id=user_id, kind="chatbot")
    assert conversation is conversations.create.return_value


async def test_resolve_conversation_rejects_someone_elses() -> None:
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    other_user_id = uuid.uuid4()
    conversations.get_by_id.return_value = SimpleNamespace(id=uuid.uuid4(), user_id=other_user_id)

    with pytest.raises(NotFoundError):
        await service.resolve_conversation(
            user_id=uuid.uuid4(), kind="chatbot", conversation_id=uuid.uuid4()
        )


async def test_send_message_streams_tokens_then_done_and_persists() -> None:
    llm = FakeLlmClient(chunks=["Hel", "lo!"])
    service, _, messages = _service(llm)
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

    events = [e async for e in service.send_message(conversation=conversation, content="hi")]

    assert [type(e).__name__ for e in events] == ["TokenEvent", "TokenEvent", "DoneEvent"]
    assert events[0] == TokenEvent("Hel")
    assert events[1] == TokenEvent("lo!")
    done = events[2]
    assert isinstance(done, DoneEvent)
    assert done.conversation_id == conversation.id
    assert done.truncated is False

    # user turn + assistant turn persisted; assistant content is the full accumulation
    assert messages.create.await_count == 2
    user_call, assistant_call = messages.create.await_args_list
    assert user_call.kwargs == {"role": "user", "content": "hi", "metadata": None}
    assert assistant_call.kwargs["role"] == "assistant"
    assert assistant_call.kwargs["content"] == "Hello!"
    assert assistant_call.kwargs["metadata"]["truncated"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_chat_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.services.chat_service'`

- [ ] **Step 3: Implement**

```python
# backend/src/services/prompts.py
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

__all__ = ["load_prompt"]

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache
def load_prompt(kind: str) -> str:
    """Reads backend/prompts/<kind>.md. All 4 kinds ship a file in this batch
    (placeholders for 3, real minimal content for chatbot) — a missing file is
    an internal mistake, not a case to handle gracefully."""
    return (_PROMPTS_DIR / f"{kind}.md").read_text(encoding="utf-8").strip()
```

```markdown
<!-- backend/prompts/chatbot.md -->
You are the AI Enablement Hub's assistant. You help learners understand AI
concepts, tools, and how to apply them at delaware. Be concise, practical, and
honest about what you don't know. This is placeholder content for the Batch A
plumbing verification — the real chatbot prompt is written in a later batch.
```

```markdown
<!-- backend/prompts/assessment.md -->
Placeholder prompt — the real assessment deep-dive prompt (probing for richer
answers during the assessment, never suggesting or evaluating an answer) is
written in a later batch. This file exists only so the kind doesn't 404.
```

```markdown
<!-- backend/prompts/lesson.md -->
Placeholder prompt — the real lesson-helper prompt (answering questions using
the current lesson's content as context) is written in a later batch. This
file exists only so the kind doesn't 404.
```

```markdown
<!-- backend/prompts/interview.md -->
Placeholder prompt — the real interviewer prompt (goal-driven probing for pain
points/use-cases, producing a structured summary) is written in a later batch.
This file exists only so the kind doesn't 404.
```

```python
# backend/src/services/chat_service.py
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.services.exceptions import NotFoundError
from src.services.prompts import load_prompt

if TYPE_CHECKING:
    from src.db.models import Conversation
    from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
    from src.services.llm_service import LlmClient, LlmUsage

__all__ = ["ChatService", "ChatStreamEvent", "DoneEvent", "TokenEvent"]

_HISTORY_WINDOW = 20
_MAX_TOKENS = 1024


@dataclass(frozen=True)
class TokenEvent:
    text: str


@dataclass(frozen=True)
class DoneEvent:
    conversation_id: uuid.UUID
    truncated: bool
    usage: LlmUsage | None


ChatStreamEvent = TokenEvent | DoneEvent


class ChatService:
    """Owns the completion loop: persist the user turn -> call the model ->
    stream the assistant turn -> persist it on completion (or on client
    disconnect, marked truncated)."""

    def __init__(
        self,
        conversations: AbstractConversationRepository,
        messages: AbstractMessageRepository,
        llm: LlmClient,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._llm = llm

    async def resolve_conversation(
        self, *, user_id: uuid.UUID, kind: str, conversation_id: uuid.UUID | None
    ) -> Conversation:
        """Runs BEFORE any streaming starts (never inside the generator) so a
        NotFoundError becomes a plain 404 through the existing exception
        handler, not a mid-stream error event."""
        if conversation_id is None:
            return await self._conversations.create(user_id=user_id, kind=kind)
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundError("Conversation")
        return conversation

    async def send_message(
        self, *, conversation: Conversation, content: str
    ) -> AsyncIterator[ChatStreamEvent]:
        await self._messages.create(conversation.id, role="user", content=content, metadata=None)
        system_prompt = load_prompt(conversation.kind)
        history = await self._history_for(conversation.id)

        chunks: list[str] = []
        truncated = False
        usage: LlmUsage | None = None
        try:
            async with self._llm.stream_reply(
                system=system_prompt, messages=history, max_tokens=_MAX_TOKENS
            ) as reply:
                async for text in reply:
                    chunks.append(text)
                    yield TokenEvent(text)
                usage = await reply.usage()
        except GeneratorExit:
            truncated = True
            raise
        finally:
            accumulated = "".join(chunks)
            if accumulated:
                metadata: dict[str, Any] = {"truncated": truncated}
                if usage is not None:
                    metadata["usage"] = {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                    }
                await asyncio.shield(
                    self._messages.create(
                        conversation.id, role="assistant", content=accumulated, metadata=metadata
                    )
                )
                await asyncio.shield(self._conversations.touch(conversation.id))

        if not truncated:
            yield DoneEvent(conversation_id=conversation.id, truncated=False, usage=usage)

    async def _history_for(self, conversation_id: uuid.UUID) -> list[dict[str, str]]:
        rows = await self._messages.list_recent(conversation_id, limit=_HISTORY_WINDOW)
        return [{"role": m.role, "content": m.content} for m in rows if m.role in ("user", "assistant")]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_chat_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/chat_service.py backend/src/services/prompts.py backend/prompts/ backend/tests/unit/test_chat_service.py
git commit -m "feat(chat): add ChatService with disconnect-safe persistence"
```

---

### Task 11: `core/dependencies/chat.py` — repos, `get_chat_service`, `require_ai_surface`

**Files:**
- Create: `backend/src/core/dependencies/chat.py`
- Test: `backend/tests/unit/test_require_ai_surface.py`

**Interfaces:**
- Consumes: `get_session`, `get_current_user`, `get_org_service` (`domain.py`), `get_llm_service`
  (Task 3), `ConversationRepository`/`MessageRepository` (Task 6), `ChatService` (Task 10).
- Produces: `get_conversation_repository`, `get_message_repository`, `get_chat_service`,
  `require_ai_surface(kind, user, org) -> None` (raises `HTTPException(403)`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_require_ai_surface.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.core.dependencies.chat import require_ai_surface
from src.services.org_service import OrgService


async def test_raises_403_when_disabled() -> None:
    org = AsyncMock(spec=OrgService)
    org.resolve_ai_settings.return_value = {
        "chatbot": False, "assessment": False, "lesson": False, "interview": False
    }
    user = type("U", (), {"project_id": uuid.uuid4()})()

    with pytest.raises(HTTPException) as exc_info:
        await require_ai_surface(kind="chatbot", user=user, org=org)
    assert exc_info.value.status_code == 403


async def test_raises_403_when_no_project() -> None:
    org = AsyncMock(spec=OrgService)
    user = type("U", (), {"project_id": None})()

    with pytest.raises(HTTPException) as exc_info:
        await require_ai_surface(kind="chatbot", user=user, org=org)
    assert exc_info.value.status_code == 403
    org.resolve_ai_settings.assert_not_awaited()


async def test_passes_when_enabled() -> None:
    org = AsyncMock(spec=OrgService)
    org.resolve_ai_settings.return_value = {
        "chatbot": True, "assessment": False, "lesson": False, "interview": False
    }
    user = type("U", (), {"project_id": uuid.uuid4()})()

    await require_ai_surface(kind="chatbot", user=user, org=org)  # does not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_require_ai_surface.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.dependencies.chat'`

- [ ] **Step 3: Implement**

```python
# backend/src/core/dependencies/chat.py
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.database import get_session
from src.core.dependencies.domain import get_org_service
from src.core.dependencies.llm import get_llm_service
from src.db.models import User
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.services.chat_service import ChatService
from src.services.llm_service import AnthropicLlmClient
from src.services.org_service import OrgService

__all__ = [
    "get_chat_service",
    "get_conversation_repository",
    "get_message_repository",
    "require_ai_surface",
]

ChatKind = Literal["chatbot", "assessment", "lesson", "interview"]


def get_conversation_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationRepository:
    return ConversationRepository(session)


def get_message_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageRepository:
    return MessageRepository(session)


def get_chat_service(
    conversations: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    messages: Annotated[MessageRepository, Depends(get_message_repository)],
    llm: Annotated[AnthropicLlmClient | None, Depends(get_llm_service)],
) -> ChatService | None:
    """None when LLM__* is unconfigured — the router 404s (see get_llm_service)."""
    if llm is None:
        return None
    return ChatService(conversations, messages, llm)


async def require_ai_surface(
    kind: ChatKind,
    user: Annotated[User, Depends(get_current_user)],
    org: Annotated[OrgService, Depends(get_org_service)],
) -> None:
    """A user with no project can't be verified as paying, so it's treated as
    disabled. Mirrors require_admin's shape (a reusable authz-style dependency
    raising HTTPException directly)."""
    settings = await org.resolve_ai_settings(user.project_id)
    if not settings[kind]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="AI feature not enabled for your project"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_require_ai_surface.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/dependencies/chat.py backend/tests/unit/test_require_ai_surface.py
git commit -m "feat(chat): add chat DI providers and require_ai_surface gate"
```

---

### Task 12: `routers/chat.py` + rate limiting + `main.py` registration

**Files:**
- Create: `backend/src/routers/chat.py`
- Modify: `backend/src/main.py`
- Modify: `backend/src/services/chat_service.py` (adds `list_conversations`/`get_conversation_detail`,
  see Step 3 — the router needs both and they weren't part of Task 10's scope)
- Test: `backend/tests/integration/test_routers/test_chat.py`

**Interfaces:**
- Consumes: `ChatService`, `require_ai_surface` (Task 11), `RateLimiter`
  (`core/dependencies/ratelimit.py`, existing), `ChatMessageCreate`/`ConversationSummary`/etc.
  (Task 9).
- Produces: `POST /api/chat/{kind}` (SSE), `GET /api/chat/conversations?kind=`,
  `GET /api/chat/conversations/{id}`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integration/test_routers/test_chat.py
from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from src.core.configs.llm import LlmSettings
from src.core.dependencies.llm import get_llm_service
from pydantic import SecretStr
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_company, create_project, create_user
from tests.fixtures.llm import FakeLlmClient

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    """Minimal SSE parser for test assertions: [(event, data_dict), ...]."""
    events = []
    event_name = "message"
    for line in raw.splitlines():
        if line.startswith("event:"):
            event_name = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            events.append((event_name, json.loads(line.removeprefix("data:").strip())))
            event_name = "message"
    return events


async def _enable_ai(client: AsyncClient, project_id: uuid.UUID, kind: str, admin_headers: dict) -> None:
    response = await client.put(
        f"/api/admin/projects/{project_id}/ai/{kind}", json={"enabled": True}, headers=admin_headers
    )
    assert response.status_code == 204


class TestSendChatMessage:
    async def test_streams_tokens_and_done_when_enabled(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        company = await create_company(db_session, "Chat Router Co")
        project = await create_project(db_session, company, "Chat Router Project")
        admin = await create_user(db_session, email="chat-router-admin@example.com", role="admin")
        user = await create_user(
            db_session, email="chat-router-user@example.com",
            company_id=company.id, project_id=project.id,
        )
        await _enable_ai(client, project.id, "chatbot", auth_headers(admin, test_settings))

        fake_llm = FakeLlmClient(chunks=["Hi", " there!"])
        client.app_state_override = fake_llm if False else None  # placeholder, see override below
        from src.core.dependencies.chat import get_chat_service
        from src.services.chat_service import ChatService
        from src.repositories.conversation_repository import ConversationRepository
        from src.repositories.message_repository import MessageRepository

        async def _override_chat_service() -> ChatService:
            return ChatService(ConversationRepository(db_session), MessageRepository(db_session), fake_llm)

        client._transport.app.dependency_overrides[get_chat_service] = _override_chat_service  # type: ignore[attr-defined]
        try:
            async with client.stream(
                "POST", "/api/chat/chatbot", json={"content": "hi"},
                headers=auth_headers(user, test_settings),
            ) as response:
                assert response.status_code == 200
                raw = "".join([chunk async for chunk in response.aiter_text()])
        finally:
            del client._transport.app.dependency_overrides[get_chat_service]  # type: ignore[attr-defined]

        events = _parse_sse(raw)
        assert [e for e, _ in events] == ["token", "token", "done"]
        assert events[0][1] == {"text": "Hi"}
        assert events[2][1]["truncated"] is False

    async def test_403_when_ai_disabled(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        company = await create_company(db_session, "Chat Router Co 2")
        project = await create_project(db_session, company, "Chat Router Project 2")
        user = await create_user(
            db_session, email="chat-router-disabled@example.com",
            company_id=company.id, project_id=project.id,
        )

        response = await client.post(
            "/api/chat/chatbot", json={"content": "hi"}, headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_anonymous_is_401(self, client: AsyncClient) -> None:
        response = await client.post("/api/chat/chatbot", json={"content": "hi"})
        assert response.status_code == 401

    async def test_unknown_conversation_id_is_404(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        company = await create_company(db_session, "Chat Router Co 3")
        project = await create_project(db_session, company, "Chat Router Project 3")
        admin = await create_user(db_session, email="chat-router-admin-3@example.com", role="admin")
        user = await create_user(
            db_session, email="chat-router-404@example.com",
            company_id=company.id, project_id=project.id,
        )
        await _enable_ai(client, project.id, "chatbot", auth_headers(admin, test_settings))

        response = await client.post(
            "/api/chat/chatbot",
            json={"content": "hi", "conversation_id": str(uuid.uuid4())},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 404


class TestListAndGetConversations:
    async def test_list_and_detail_ungated_by_ai_setting(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        # AI stays default-disabled for this project, but history endpoints
        # aren't gated by require_ai_surface.
        company = await create_company(db_session, "Chat History Co")
        project = await create_project(db_session, company, "Chat History Project")
        user = await create_user(
            db_session, email="chat-history@example.com",
            company_id=company.id, project_id=project.id,
        )
        from src.repositories.conversation_repository import ConversationRepository

        conversation = await ConversationRepository(db_session).create(user_id=user.id, kind="chatbot")

        list_response = await client.get(
            "/api/chat/conversations?kind=chatbot", headers=auth_headers(user, test_settings)
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["conversations"]) == 1

        detail_response = await client.get(
            f"/api/chat/conversations/{conversation.id}", headers=auth_headers(user, test_settings)
        )
        assert detail_response.status_code == 200

    async def test_detail_404_for_someone_elses_conversation(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        company = await create_company(db_session, "Chat History Co 2")
        project = await create_project(db_session, company, "Chat History Project 2")
        owner = await create_user(
            db_session, email="chat-owner@example.com", company_id=company.id, project_id=project.id
        )
        other = await create_user(db_session, email="chat-other@example.com")
        from src.repositories.conversation_repository import ConversationRepository

        conversation = await ConversationRepository(db_session).create(user_id=owner.id, kind="chatbot")

        response = await client.get(
            f"/api/chat/conversations/{conversation.id}", headers=auth_headers(other, test_settings)
        )
        assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_routers/test_chat.py -v`
Expected: FAIL — `404 Not Found` for all routes (router doesn't exist yet) / import errors for
`get_chat_service`/`ConversationRepository`

- [ ] **Step 3: Implement the router**

```python
# backend/src/routers/chat.py
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.chat import ChatKind, get_chat_service, require_ai_surface
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.ratelimit import RateLimiter
from src.db.models import User
from src.schemas.chat import (
    ChatMessageCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
)
from src.services.chat_service import ChatService, DoneEvent, TokenEvent
from src.services.exceptions import NotFoundError

__all__ = ["router"]

router = APIRouter(prefix="/api/chat", tags=["chat"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]
ChatServiceDep = Annotated[ChatService | None, Depends(get_chat_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

_RATE_LIMITED_SHORT = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many messages — try again shortly",
    headers={"Retry-After": "60"},
)
_RATE_LIMITED_DAILY = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Daily chat limit reached",
    headers={"Retry-After": "3600"},
)


@router.post(
    "/{kind}",
    response_class=EventSourceResponse,
    dependencies=[Depends(require_ai_surface)],
)
async def send_chat_message(
    kind: ChatKind,
    body: ChatMessageCreate,
    user: CurrentUserDep,
    chat_service: ChatServiceDep,
    limiter: RateLimiterDep,
) -> AsyncIterator[ServerSentEvent]:
    if chat_service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat is not configured")
    if limiter.is_limited(f"chat:{user.id}", max_calls=20, window_seconds=300):
        raise _RATE_LIMITED_SHORT
    if limiter.is_limited(f"chat-daily:{user.id}", max_calls=200, window_seconds=86400):
        raise _RATE_LIMITED_DAILY

    conversation = await chat_service.resolve_conversation(
        user_id=user.id, kind=kind, conversation_id=body.conversation_id
    )

    async def _events() -> AsyncIterator[ServerSentEvent]:
        async for event in chat_service.send_message(conversation=conversation, content=body.content):
            if isinstance(event, TokenEvent):
                yield ServerSentEvent(data={"text": event.text}, event="token")
            elif isinstance(event, DoneEvent):
                usage = (
                    {"input_tokens": event.usage.input_tokens, "output_tokens": event.usage.output_tokens}
                    if event.usage is not None
                    else None
                )
                yield ServerSentEvent(
                    data={
                        "conversation_id": str(event.conversation_id),
                        "truncated": event.truncated,
                        "usage": usage,
                    },
                    event="done",
                )

    return _events()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: CurrentUserDep,
    chat_service: ChatServiceDep,
    kind: ChatKind = Query(...),
) -> ConversationListResponse:
    if chat_service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat is not configured")
    conversations = await chat_service.list_conversations(user_id=user.id, kind=kind)
    return ConversationListResponse(
        conversations=[ConversationSummary.model_validate(c) for c in conversations]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUserDep,
    chat_service: ChatServiceDep,
) -> ConversationDetailResponse:
    if chat_service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat is not configured")
    try:
        conversation, messages = await chat_service.get_conversation_detail(
            user_id=user.id, conversation_id=conversation_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ConversationDetailResponse(
        conversation=ConversationSummary.model_validate(conversation),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )
```

This introduces two `ChatService` methods not yet written (`list_conversations`,
`get_conversation_detail`) — add them to `backend/src/services/chat_service.py` (thin
pass-throughs, same shape as `resolve_conversation`):

```python
    async def list_conversations(self, *, user_id: uuid.UUID, kind: str) -> list[Conversation]:
        return await self._conversations.list_for_user(user_id, kind)

    async def get_conversation_detail(
        self, *, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> tuple[Conversation, list[Message]]:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundError("Conversation")
        messages = await self._messages.list_for_conversation(conversation_id)
        return conversation, messages
```

(add `Message` to the `TYPE_CHECKING` import block in `chat_service.py`)

Edit `backend/src/main.py`: add `chat` to the `from src.routers import (...)` block (alphabetical)
and `app.include_router(chat.router)` alongside the others.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_routers/test_chat.py -v`
Expected: PASS. If the SSE-stream test's dependency-override plumbing doesn't work as sketched
(httpx's `AsyncClient` wraps the transport in a way that makes `client._transport.app` awkward to
reach), fall back to the standard `app.dependency_overrides[...]` pattern used by the `client`
fixture itself — read `tests/conftest.py`'s `client` fixture again and mirror its override
mechanism exactly rather than reaching through private attributes.

- [ ] **Step 5: Commit**

```bash
git add backend/src/routers/chat.py backend/src/main.py backend/src/services/chat_service.py backend/tests/integration/test_routers/test_chat.py
git commit -m "feat(chat): add chat router with SSE streaming, rate limits, AI gate"
```

---

### Task 13: Admin AI-settings endpoints

**Files:**
- Modify: `backend/src/routers/admin_org.py`
- Test: `backend/tests/integration/test_routers/test_admin_org.py` (extend existing)

**Interfaces:**
- Produces: `GET /api/admin/projects/{project_id}/ai`, `PUT /api/admin/projects/{project_id}/ai/{kind}`.

- [ ] **Step 1: Write the failing tests**

```python
# add to backend/tests/integration/test_routers/test_admin_org.py
class TestAiSettings:
    async def test_get_defaults_all_false(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="ai-settings-admin@example.com", role="admin")
        company = await create_company(db_session, "AI Settings Co")
        project = await create_project(db_session, company, "AI Settings Project")

        response = await client.get(
            f"/api/admin/projects/{project.id}/ai", headers=auth_headers(admin, test_settings)
        )

        assert response.status_code == 200
        settings = response.json()["settings"]
        assert all(v["enabled"] is False for v in settings.values())
        assert set(settings) == {"chatbot", "assessment", "lesson", "interview"}

    async def test_put_enables_one_surface(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="ai-settings-admin-2@example.com", role="admin")
        company = await create_company(db_session, "AI Settings Co 2")
        project = await create_project(db_session, company, "AI Settings Project 2")

        put_response = await client.put(
            f"/api/admin/projects/{project.id}/ai/chatbot",
            json={"enabled": True},
            headers=auth_headers(admin, test_settings),
        )
        assert put_response.status_code == 204

        get_response = await client.get(
            f"/api/admin/projects/{project.id}/ai", headers=auth_headers(admin, test_settings)
        )
        assert get_response.json()["settings"]["chatbot"]["enabled"] is True
        assert get_response.json()["settings"]["lesson"]["enabled"] is False

    async def test_non_admin_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="ai-settings-user@example.com")
        company = await create_company(db_session, "AI Settings Co 3")
        project = await create_project(db_session, company, "AI Settings Project 3")

        response = await client.get(
            f"/api/admin/projects/{project.id}/ai", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
```

(match the imports already present at the top of `test_admin_org.py` — `create_user`,
`create_company`, `create_project`, `auth_headers`, `AsyncClient`, `AsyncSession`, `Settings` should
already be imported there; add any missing ones)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_routers/test_admin_org.py -v -k ai_settings`
Expected: FAIL — 404 (routes don't exist yet)

- [ ] **Step 3: Implement**

Append to `backend/src/routers/admin_org.py` (add `AiSettingsResponse`, `AiSurfaceState`,
`AiSurfaceUpdateRequest` to the existing `from src.schemas.admin_org import (...)` block, and
`Literal` is already imported):

```python
@router.get("/projects/{project_id}/ai", response_model=AiSettingsResponse)
async def get_ai_settings(project_id: uuid.UUID, org_service: OrgServiceDep) -> AiSettingsResponse:
    settings = await org_service.resolve_ai_settings(project_id)
    return AiSettingsResponse(
        settings={kind: AiSurfaceState(enabled=enabled) for kind, enabled in settings.items()}
    )


@router.put("/projects/{project_id}/ai/{kind}", status_code=status.HTTP_204_NO_CONTENT)
async def put_ai_setting(
    project_id: uuid.UUID,
    kind: Literal["chatbot", "assessment", "lesson", "interview"],
    body: AiSurfaceUpdateRequest,
    org_service: OrgServiceDep,
) -> None:
    await org_service.set_ai_surface(project_id, kind, enabled=body.enabled)
```

Note: unlike `get_components` (which uses `require_project=True` to 404 on an unknown project),
`resolve_ai_settings` doesn't currently take that flag — for this admin-only read endpoint, an
unknown `project_id` will just return all-`False` rather than 404. This is a minor inconsistency
with the existing `/components` endpoint; if strict parity matters, extend
`resolve_ai_settings` with the same `require_project: bool = False` parameter `resolve_components`
has, and pass `True` here. Decide during implementation review; either is defensible for Batch A.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_routers/test_admin_org.py -v -k ai_settings`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/routers/admin_org.py backend/tests/integration/test_routers/test_admin_org.py
git commit -m "feat(chat): add admin AI-settings endpoints"
```

---

### Task 14: Authz matrix entries + full backend test suite

**Files:**
- Modify: `backend/tests/integration/test_routers/test_authz.py`

**Interfaces:**
- None new — this task only wires existing endpoints into the shared matrix.

- [ ] **Step 1: Add matrix entries for the two ungated GET endpoints**

The `_MATRIX` list assumes a flat `(name, method, path, body, admin_only)` shape with no extra
gating — that fits `GET /api/chat/conversations` and `GET /api/chat/conversations/{id}` (auth
only, no AI-gate), but NOT `POST /api/chat/{kind}` (which also needs the seed project's AI setting
enabled or it 403s regardless of role — a third dimension the shared matrix doesn't model). Add
only the two GET endpoints to `_MATRIX`, and give `POST /api/chat/{kind}` its own dedicated test
class instead of forcing it into the shared table.

Add to `_MATRIX` (needs a conversation to exist for the detail-path case — reuse the `seed`
fixture's `user`, creating one conversation for them at the top of the test that uses this list,
matching how `seed.lesson` etc. are pre-created):

```python
    ("chat-conversations-list", "GET", lambda s: "/api/chat/conversations?kind=chatbot", lambda s: None, False),
```

(the `{id}` detail path needs a real id per-seed-user, which the flat matrix can't express cleanly
— cover its 401/404 cases in the dedicated `TestListAndGetConversations` class already written in
Task 12, which is sufficient; don't force it into `_MATRIX`)

- [ ] **Step 2: Run the full authz suite**

Run: `uv run pytest tests/integration/test_routers/test_authz.py -v`
Expected: PASS

- [ ] **Step 3: Run the entire backend suite + checks**

Run: `uv run poe format && uv run poe lint && uv run poe test`
Expected: all green, coverage ≥80%. If coverage is short, add unit tests for any untested branch
(e.g. `ChatService.list_conversations`/`get_conversation_detail`) rather than lowering the bar.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_routers/test_authz.py
git commit -m "test(chat): add chat endpoints to the authz matrix"
```

---

## Phase 3 — Local live-model manual verification (APPROVAL GATE)

**STOP: do not proceed with this phase without asking the user first.** This phase runs the dev
backend against a real database and applies the migration — both are exactly the kind of
DB-mutating action `feedback-azure-ask-first` and this project's standing rules require asking
about, even though the target here is Matthias's own local/dev environment rather than Azure
directly. Confirm which database (local Postgres vs. the shared Azure dev DB) before running
anything.

- [ ] **Step 1 (after approval): Set local LLM env vars**

In `backend/.env`, add (using Matthias's existing personal Anthropic key, per the decision that
local dev doesn't need the dedicated workspace/spend-cap key yet):
```
LLM__PROVIDER=anthropic
LLM__MODEL=claude-haiku-4-5
LLM__API_KEY=<Matthias's key>
```

- [ ] **Step 2 (after approval): Confirm target DB, then apply the migration**

Run: `uv run alembic heads` to double check it matches this migration's `down_revision`, then
`uv run poe upgrade` against whichever DB was approved in the stop-and-ask above.

- [ ] **Step 3: Enable the chatbot AI surface for a test project via the API**

With the dev backend running (`uv run poe dev`), use `/docs` or curl to `PUT
/api/admin/projects/{project_id}/ai/chatbot {"enabled": true}` with an admin token for whichever
project the verifying user belongs to.

- [ ] **Step 4: Curl/Swagger-verify the streaming endpoint end-to-end**

`POST /api/chat/chatbot {"content": "Hello!"}` with that user's token — confirm real text streams
back as `event: token` lines, ending with `event: done` carrying a `conversation_id`. Then query
the DB directly (or `GET /api/chat/conversations?kind=chatbot`) to confirm rows landed in
`conversations` and `messages`.

- [ ] **Step 5: Verify disconnect-safe persistence**

Start a `POST /api/chat/chatbot` request (e.g. via curl with `--max-time 1` so it aborts
mid-stream, or by closing a browser tab mid-response), then check the DB: an assistant `messages`
row should exist with `metadata->>'truncated' = 'true'` even though the client never received the
full reply. If this doesn't work as designed, that confirms the risk flagged in the spec — note
exactly what happened (which step failed) so Task 10's implementation can be revisited before
calling Phase 2 complete.

---

## Phase 4 — Frontend

**Sequencing note:** Tasks 15, 16, and 18 write code that calls new backend routes
(`/api/chat/*`, `/api/admin/projects/{project_id}/ai*`) through the typed `client.GET`/`client.PUT`
wrapper — but `schema.d.ts` doesn't know about those routes until Task 19's `gen:api` runs
(approval-gated). This is expected and fine: `npm run dev` (Vite) doesn't block on TypeScript
errors, so each task is still manually checkable in the browser as it's built; `npm run typecheck`
only turns fully green after Task 19. Don't be alarmed if `typecheck` fails partway through this
phase — that's the expected state until Task 19 completes.

### Task 15: `useChat` hook

**Files:**
- Create: `frontend/src/lib/useChat.ts`
- Test: manual (frontend has no unit-test harness for hooks in this repo yet; verify via the
  `DevChat` page in Task 17 instead — do not introduce a new test framework for one hook)

**Interfaces:**
- Produces: `useChat(kind: ChatKind)` returning
  `{ messages: ChatUiMessage[], send(content: string): void, loading: boolean, error: string | null,
  conversations: ConversationSummary[], loadConversation(id: string): void, startNew(): void }`.

- [ ] **Step 1: Write the hook**

```typescript
// frontend/src/lib/useChat.ts
import { useCallback, useState } from 'react'
import { getAccessToken, refreshAccessToken } from '../api/tokens'
import { client } from '../api/client'

export type ChatKind = 'chatbot' | 'assessment' | 'lesson' | 'interview'

export interface ChatUiMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ConversationSummary {
  id: string
  kind: string
  context_ref: string | null
  created_at: string
  updated_at: string
}

async function fetchWithAuth(input: string, init: RequestInit): Promise<Response> {
  const access = getAccessToken()
  const headers = new Headers(init.headers)
  if (access) headers.set('Authorization', `Bearer ${access}`)
  let response = await fetch(input, { ...init, headers })
  if (response.status === 401) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      headers.set('Authorization', `Bearer ${refreshed}`)
      response = await fetch(input, { ...init, headers })
    }
  }
  return response
}

function parseSseLine(
  line: string,
  currentEvent: string,
): { event: string; data: unknown } | null {
  if (line.startsWith('event:')) return null
  if (line.startsWith('data:')) {
    return { event: currentEvent, data: JSON.parse(line.slice('data:'.length).trim()) }
  }
  return null
}

export function useChat(kind: ChatKind) {
  const [messages, setMessages] = useState<ChatUiMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])

  const send = useCallback(
    async (content: string) => {
      setLoading(true)
      setError(null)
      setMessages((prev) => [...prev, { role: 'user', content }])
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

      try {
        const response = await fetchWithAuth(`/api/chat/${kind}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, conversation_id: conversationId }),
        })
        if (!response.ok || !response.body) {
          setError(`Chat request failed (${response.status})`)
          setLoading(false)
          return
        }
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let currentEvent = 'message'
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''
          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEvent = line.slice('event:'.length).trim()
              continue
            }
            const parsed = parseSseLine(line, currentEvent)
            if (!parsed) continue
            if (parsed.event === 'token') {
              const { text } = parsed.data as { text: string }
              setMessages((prev) => {
                const next = [...prev]
                next[next.length - 1] = {
                  role: 'assistant',
                  content: next[next.length - 1].content + text,
                }
                return next
              })
            } else if (parsed.event === 'done') {
              const { conversation_id } = parsed.data as { conversation_id: string }
              setConversationId(conversation_id)
            } else if (parsed.event === 'error') {
              const { message } = parsed.data as { message: string }
              setError(message)
            }
          }
        }
      } catch {
        setError('Connection lost while streaming the reply.')
      } finally {
        setLoading(false)
      }
    },
    [kind, conversationId],
  )

  const loadConversations = useCallback(async () => {
    const { data } = await client.GET('/api/chat/conversations', { params: { query: { kind } } })
    if (data) setConversations(data.conversations)
  }, [kind])

  const loadConversation = useCallback(async (id: string) => {
    const { data } = await client.GET('/api/chat/conversations/{conversation_id}', {
      params: { path: { conversation_id: id } },
    })
    if (data) {
      setConversationId(id)
      setMessages(data.messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })))
    }
  }, [])

  const startNew = useCallback(() => {
    setConversationId(null)
    setMessages([])
    setError(null)
  }, [])

  return { messages, send, loading, error, conversations, loadConversations, loadConversation, startNew }
}
```

Note: `client.GET('/api/chat/conversations/{conversation_id}', ...)` and the `kind` query param
shape must match whatever `npm run gen:api` actually generates once the backend endpoints exist —
**this exact call shape is provisional until Task 19's `gen:api` step regenerates `schema.d.ts`;
fix any mismatch then, following the generated types rather than this plan.**

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/useChat.ts
git commit -m "feat(chat): add useChat hook (manual SSE parsing, not native EventSource)"
```

---

### Task 16: `<ChatPanel>` component

**Files:**
- Create: `frontend/src/components/ChatPanel.tsx`

**Interfaces:**
- Consumes: `useChat` (Task 15).
- Produces: `<ChatPanel kind={ChatKind} />`.

- [ ] **Step 1: Write the component**

```tsx
// frontend/src/components/ChatPanel.tsx
import { useEffect, useState } from 'react'
import { type ChatKind, useChat } from '../lib/useChat'

interface ChatPanelProps {
  kind: ChatKind
}

export default function ChatPanel({ kind }: ChatPanelProps) {
  const { messages, send, loading, error, conversations, loadConversations, loadConversation, startNew } =
    useChat(kind)
  const [input, setInput] = useState('')
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    if (showHistory) void loadConversations()
  }, [showHistory, loadConversations])

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return
    setInput('')
    void send(trimmed)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: 480, fontFamily: 'var(--dlw-font-body)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: 12, borderBottom: '1px solid #E2E2E2' }}>
        <button type="button" onClick={startNew} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
          + New conversation
        </button>
        <button type="button" onClick={() => setShowHistory((v) => !v)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
          History
        </button>
      </div>

      {showHistory && (
        <div style={{ borderBottom: '1px solid #E2E2E2', maxHeight: 160, overflowY: 'auto' }}>
          {conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => {
                void loadConversation(c.id)
                setShowHistory(false)
              }}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: 8, background: 'none', border: 'none', cursor: 'pointer' }}
            >
              {new Date(c.updated_at).toLocaleString()}
            </button>
          ))}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? '#C42828' : '#F2F2F2',
              color: m.role === 'user' ? '#fff' : '#1A1A1A',
              borderRadius: 12,
              padding: '8px 12px',
              maxWidth: '80%',
              whiteSpace: 'pre-wrap',
            }}
          >
            {m.content}
          </div>
        ))}
        {error && <div style={{ color: '#C42828', fontSize: 13 }}>{error}</div>}
      </div>

      <p style={{ fontSize: 11, color: '#8A8A8A', padding: '0 12px', margin: '0 0 8px' }}>
        Conversations are stored and may be reviewed by hub admins to improve the hub.
      </p>

      <form onSubmit={onSubmit} style={{ display: 'flex', gap: 8, padding: 12, borderTop: '1px solid #E2E2E2' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          style={{ flex: 1, padding: '8px 12px', borderRadius: 999, border: '1px solid #E2E2E2' }}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{ borderRadius: 999, padding: '8px 16px', background: '#C42828', color: '#fff', border: 'none', cursor: 'pointer' }}
        >
          {loading ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
```

This is functional-level styling for Batch A's verification purposes — real visual polish (the
floating icon, exact placement/animation) is Batch B's job once the panel is mounted for real, per
the spec.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ChatPanel.tsx
git commit -m "feat(chat): add ChatPanel component with history list and transparency notice"
```

---

### Task 17: `DevChat` dev-only verification route

**Files:**
- Create: `frontend/src/pages/DevChat.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `ChatPanel` (Task 16).

- [ ] **Step 1: Write the page**

```tsx
// frontend/src/pages/DevChat.tsx
// Temporary Batch A verification harness — deleted once Batch B mounts
// ChatPanel for real (floating icon / assessment / lesson mounts).
import ChatPanel from '../components/ChatPanel'

export default function DevChat() {
  return (
    <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#fafafa' }}>
      <div style={{ height: '80vh', width: 480, border: '1px solid #E2E2E2', borderRadius: 12, background: '#fff' }}>
        <ChatPanel kind="chatbot" />
      </div>
    </div>
  )
}
```

Edit `frontend/src/App.tsx`: import `DevChat` alongside the other page imports, and add a route
inside `<Routes>` (session-gated like the other authenticated routes):
```tsx
<Route path="/dev-chat" element={session ? <DevChat /> : <Navigate to="/login" replace />} />
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DevChat.tsx frontend/src/App.tsx
git commit -m "feat(chat): add temporary /dev-chat verification route"
```

---

### Task 18: Admin `ProjectDetailView` AI-toggle additions

**Files:**
- Modify: `frontend/src/pages/Admin.tsx` (owns the data-fetching/state/toggle-handler — the
  `componentAccess`/`onToggleComponent` state for the *existing* 3-component toggles lives here,
  NOT in `ProjectDetailView.tsx`, confirmed by reading both files: `ProjectDetailView` is a
  presentational child that just receives `componentAccess`/`handlers.onToggleComponent` as props)
- Modify: `frontend/src/pages/admin/ProjectDetailView.tsx` (renders the toggles)

**Interfaces:**
- Produces: 4 toggle switches (chatbot/assessment/lesson/interview) next to the existing 3
  component toggles, calling `PUT /api/admin/projects/{id}/ai/{kind}`.
- **Depends on Task 19's `gen:api` for full typechecking** — `client.GET`/`client.PUT` calls to
  the new `/api/admin/projects/{project_id}/ai*` paths reference routes `schema.d.ts` doesn't know
  about yet. This is expected: `npm run dev` (Vite) doesn't block on type errors the way
  `npm run typecheck` does, so the UI is manually checkable now; the full `typecheck`/`lint`/
  `build` green run happens only after Task 19 regenerates `schema.d.ts` (its own Step 3).

- [ ] **Step 1: Add AI-settings state to `Admin.tsx`**

Add alongside the existing project-view state (near `projectComponents`/`loadingComponents`/
`togglingComponent`/`componentError`, currently around line 65-68 — confirm by searching for
`togglingComponent` in the file, since exact line numbers drift):

```tsx
const [aiSettings, setAiSettings] = useState<Record<string, { enabled: boolean }>>({})
const [loadingAiSettings, setLoadingAiSettings] = useState(false)
const [togglingAi, setTogglingAi] = useState<string | null>(null)
const [aiSettingsError, setAiSettingsError] = useState<string | null>(null)
```

- [ ] **Step 2: Fetch AI settings alongside components in `loadProjectData`**

In `loadProjectData` (search for `const loadProjectData = useCallback`), extend the existing
`Promise.all` (currently fetching `usersRes`/`compRes`/`learningRes`) with a 4th call, and set the
loading/error state around it exactly like `loadingComponents`/`componentError` already are:

```tsx
const loadProjectData = useCallback(async (projectId: string) => {
  setLoadingProjectUsers(true)
  setLoadingComponents(true)
  setLoadingAiSettings(true)
  setProjectUsersError(null)
  setComponentError(null)
  setAiSettingsError(null)

  try {
    const [usersRes, compRes, learningRes, aiRes] = await Promise.all([
      client.GET('/api/admin/users', { params: { query: { project_id: projectId } } }),
      client.GET('/api/admin/projects/{project_id}/components', { params: { path: { project_id: projectId } } }),
      client.GET('/api/admin/learning'),
      client.GET('/api/admin/projects/{project_id}/ai', { params: { path: { project_id: projectId } } }),
    ])

    if (usersRes.data) {
      const users = usersRes.data.users
      setProjectUsers(users)
      if (users.length > 0) {
        client.GET('/api/admin/surveys', {
          params: { query: { user_ids: users.map(u => u.id).join(',') } },
        })
          .then(({ data }) => { if (data) setSurveyLevels(data.levels) })
          .catch(() => {})
      }
    } else {
      setProjectUsersError(errorMessage(usersRes.error, 'Failed to load users.'))
    }

    if (compRes.data) setProjectComponents(compRes.data.components)
    else setComponentError(errorMessage(compRes.error, 'Failed to load component settings.'))

    if (aiRes.data) setAiSettings(aiRes.data.settings)
    else setAiSettingsError(errorMessage(aiRes.error, 'Failed to load AI settings.'))

    if (learningRes.data) setLearningData(learningRes.data)
  } catch {
    setProjectUsersError('Network error.')
  }
  setLoadingProjectUsers(false)
  setLoadingComponents(false)
  setLoadingAiSettings(false)
}, [])
```

- [ ] **Step 3: Add the toggle handler**

Add right after the existing `toggleComponent` function (search for `/* ── component toggles ── */`):

```tsx
/* ── AI-surface toggles ── */
async function toggleAiSurface(kind: string, current: { enabled: boolean }) {
  if (!selectedProject) return
  const next = { enabled: !current.enabled }
  setTogglingAi(kind)
  setAiSettingsError(null)
  try {
    const { error } = await client.PUT('/api/admin/projects/{project_id}/ai/{kind}', {
      params: { path: { project_id: selectedProject.id, kind } },
      body: { enabled: next.enabled },
    })
    if (error) {
      setAiSettingsError(errorMessage(error, 'Failed to update AI access.'))
    } else {
      setAiSettings(prev => ({ ...prev, [kind]: next }))
    }
  } catch { setAiSettingsError('Network error.') }
  setTogglingAi(null)
}
```

- [ ] **Step 4: Pass the new props into `<ProjectDetailView>`**

Find where `<ProjectDetailView>` is rendered (search for `componentAccess={{`, currently around
line 429) and add a sibling `aiAccess` prop plus `onToggleAi` in `handlers`:

```tsx
componentAccess={{
  data: projectComponents,
  loading: loadingComponents,
  error: componentError,
  toggling: togglingComponent,
}}
aiAccess={{
  data: aiSettings,
  loading: loadingAiSettings,
  error: aiSettingsError,
  toggling: togglingAi,
}}
handlers={{
  onBack: closeProject,
  onToggleComponent: toggleComponent,
  onToggleAi: toggleAiSurface,
  // ...(rest of the existing handlers, unchanged)
```

- [ ] **Step 5: Extend `ProjectDetailView.tsx`'s props and render the new table**

Add a new prop interface next to the existing `ComponentAccessProps` (near line 44):

```tsx
interface AiAccessProps {
  data: Record<string, { enabled: boolean }>
  loading: boolean
  error: string | null
  toggling: string | null
}
```

Add `aiAccess: AiAccessProps` to `ProjectDetailViewProps` (near line 67), and
`onToggleAi: (kind: string, current: { enabled: boolean }) => void` to the `Handlers` interface
(near line 53, right after `onToggleComponent`).

Destructure the new prop alongside the existing `componentAccess` destructure (near line 89-92):

```tsx
const {
  data: aiSettings, loading: loadingAiSettings, error: aiSettingsError, toggling: togglingAi,
} = aiAccess
```

and add `onToggleAi` to the `handlers` destructure (near line 94-98) and `aiAccess` to the
function's parameter list (near line 78-83).

Add a new table block immediately after the existing component-access `<div>` closes (right after
the `{/* component access */}` block ends, currently around line 425 where the
`COMPONENT_KEYS.map` closes) — a new sibling section, same card/table styling, reusing the
existing `s.toggleOpen`/`s.toggleLocked`/`s.toggleBusy` style tokens from `adminStyles.ts` (green
"open"-style for enabled, red "locked"-style for disabled — no new style tokens needed):

```tsx
{/* AI feature access */}
<div style={{ ...s.tableCard, marginBottom: 28 }}>
  <div style={s.tableHeader}>
    <p style={s.tableTitle}>AI features</p>
  </div>
  {aiSettingsError && (
    <div style={{ margin: '0 24px 16px', padding: '10px 14px', background: '#FFF0EF', border: '1px solid #FBCFCC', borderRadius: 6, fontSize: 13, color: '#C42828' }}>
      {aiSettingsError}
    </div>
  )}
  {loadingAiSettings ? (
    <p style={{ padding: '32px 24px', fontSize: 14, color: '#B6B6B6', fontWeight: 300 }}>loading…</p>
  ) : (
    <table style={s.table}>
      <thead>
        <tr>
          <th style={s.th}>AI feature</th>
          <th style={s.th}>Access</th>
        </tr>
      </thead>
      <tbody>
        {AI_KINDS.map(({ key, label }) => {
          const current = aiSettings[key] ?? { enabled: false }
          const busy = togglingAi === key
          return (
            <tr key={key}>
              <td style={{ ...s.td, ...s.tdName }}>{label}</td>
              <td style={s.td}>
                <button
                  style={{ ...(current.enabled ? s.toggleOpen : s.toggleLocked), ...(busy ? s.toggleBusy : {}) }}
                  onClick={() => onToggleAi(key, current)}
                  disabled={busy}
                >
                  {busy ? '…' : current.enabled ? 'enabled' : 'disabled'}
                </button>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )}
</div>
```

Add the `AI_KINDS` constant near the top of `ProjectDetailView.tsx`, alongside the other
module-level constants (near `roleBadgeColor`):

```tsx
const AI_KINDS: { key: string; label: string }[] = [
  { key: 'chatbot', label: 'Chatbot' },
  { key: 'assessment', label: 'Assessment deep-dive' },
  { key: 'lesson', label: 'Lesson helper' },
  { key: 'interview', label: 'Interviewer' },
]
```

- [ ] **Step 6: Manual check**

Run `npm run dev`, sign in as admin, open a project's detail view, confirm 4 new toggles appear
below the existing 3 component toggles and clicking one calls the PUT endpoint (check the network
tab) and reflects the new state on reload. Full type/lint/build verification is deferred to
Task 19 (see the note above).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Admin.tsx frontend/src/pages/admin/ProjectDetailView.tsx
git commit -m "feat(chat): add per-project AI-surface toggles to admin ProjectDetailView"
```

---

### Task 19: Regenerate `schema.d.ts` (APPROVAL GATE)

**STOP: ask the user before running this.** `npm run gen:api` requires the backend running
against a database, and starting the dev backend triggers a real daily auth-cleanup DELETE against
whichever DB it's pointed at — this project's standing rule requires asking first (see the
lesson-feedback precedent in `docs/superpowers/specs/2026-07-14-lesson-feedback-design.md`).

- [ ] **Step 1 (after approval): Regenerate**

With the dev backend running (`cd backend && uv run poe dev`), run (inside `frontend/`):
`npm run gen:api`. Confirm `src/api/schema.d.ts` now has real types for `/api/chat/{kind}`,
`/api/chat/conversations`, `/api/chat/conversations/{conversation_id}`, and the two admin AI
endpoints.

- [ ] **Step 2: Fix any type mismatches surfaced by the real generated types**

Revisit Task 15's `useChat.ts` `client.GET(...)` calls and Task 18's `client.PUT(...)` calls —
adjust parameter names/shapes to match whatever the real generation produced (it is the source of
truth, not this plan's guesses).

- [ ] **Step 3: Run frontend checks**

Run: `npm run typecheck && npm run lint && npm run build`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/schema.d.ts frontend/src/lib/useChat.ts frontend/src/pages/admin/ProjectDetailView.tsx
git commit -m "chore(chat): regenerate schema.d.ts for the chat and AI-settings endpoints"
```

---

## Phase 5 — End-to-end browser verification (no deploy)

- [ ] **Step 1:** Run backend (`cd backend && uv run poe dev`) and frontend (`cd frontend && npm run dev`) locally.
- [ ] **Step 2:** As an admin, enable the `chatbot` AI surface for a test project (via `ProjectDetailView`'s new toggles from Task 18).
- [ ] **Step 3:** As a user in that project, visit `/dev-chat`, send a message, confirm it streams token-by-token.
- [ ] **Step 4:** Reload, confirm the "History" list shows the conversation; click it, confirm it resumes with prior messages.
- [ ] **Step 5:** Confirm the transparency notice line is visible in the panel.
- [ ] **Step 6:** As a user in a project **without** the toggle enabled, confirm sending a message returns 403 (visible as the panel's error state).
- [ ] **Step 7:** Record results (what worked, what didn't, any deviations from this plan) — **do not deploy**. Batch A ships dark/unmounted; deploying it is a separate decision for a later session.

---

## Self-Review Notes (from writing this plan)

- **Spec coverage:** every section of the design doc maps to a task — provider/SDK (Tasks 1-3),
  data model (Tasks 4-6), migration (Task 7), AI gate (Tasks 5, 8, 11), service/router/guardrails
  (Tasks 9-12), admin endpoints (Task 13), authz matrix (Task 14), Phase 3 manual verification
  (its own phase), frontend (Tasks 15-18), `gen:api` (Task 19), browser verification (Phase 5).
- **Known provisional pieces, flagged rather than hidden:** the SSE-stream integration test's
  dependency-override mechanism (Task 12) may need adjustment once actually run — noted inline.
  The disconnect-safe-persistence design (Task 10, `GeneratorExit` + `asyncio.shield`) is a
  best-effort design for a documented open risk (spec's own words) — Phase 3 Step 5 is where it
  actually gets proven or disproven against reality.
- **Type consistency check:** `ChatService.send_message` yields `TokenEvent`/`DoneEvent` (Task 10)
  — the router (Task 12) pattern-matches on exactly those two types. `LlmClient.stream_reply`
  (Task 2) returns something usable as `async with ... as reply: async for chunk in reply: ...
  await reply.usage()` — `ChatService` (Task 10) uses it exactly that way. `Message.metadata_`
  (Task 4, aliased column) is used consistently in Task 6's repository and Task 10's service —
  every write path uses `metadata_` as the constructor kwarg name, matching the model field.
