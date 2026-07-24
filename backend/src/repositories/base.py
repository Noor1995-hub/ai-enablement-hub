from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.db.models import (
        AuthSession,
        AuthToken,
        Company,
        Feedback,
        Lesson,
        LessonProgress,
        Module,
        ModulePrerequisite,
        Project,
        ProjectComponentSetting,
        ProjectEmailTemplate,
        SurveyResponse,
        Track,
        User,
        UserLesson,
        UserModule,
        UserTrack,
    )

__all__ = [
    "AbstractAssignmentRepository",
    "AbstractAuthSessionRepository",
    "AbstractAuthTokenRepository",
    "AbstractContentRepository",
    "AbstractEmailTemplateRepository",
    "AbstractFeedbackRepository",
    "AbstractOrgRepository",
    "AbstractProgressRepository",
    "AbstractSurveyRepository",
    "AbstractUserRepository",
]


class AbstractUserRepository(ABC):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def emails_in(self, emails: list[str]) -> set[str]:
        """Which of the given (normalized) emails already have a user row
        (bulk-invite dedup)."""

    @abstractmethod
    async def get_by_external_id(self, external_id: str) -> User | None:
        """Lookup by the linked Entra ID object id (oid claim)."""

    @abstractmethod
    async def link_external_id(self, user: User, external_id: str) -> None:
        """Persist the Entra ID object id (first Microsoft sign-in linking)."""

    @abstractmethod
    async def set_password(self, user: User, password_hash: str) -> None:
        """Persist a new password hash and mark password_set=true."""

    @abstractmethod
    async def list_with_org_names(
        self, project_id: uuid.UUID | None = None
    ) -> list[tuple[User, str | None, str | None]]:
        """(user, company_name, project_name) newest-first, optionally by project."""

    @abstractmethod
    async def list_for_learning(self) -> list[tuple[User, str | None, str | None]]:
        """(user, project_name, company_name) ordered by first name (admin panel)."""

    @abstractmethod
    async def create(
        self,
        *,
        email: str,
        first_name: str,
        last_name: str,
        company_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> User:
        """Insert an invited user (role user, no password, password_set=false)."""

    @abstractmethod
    async def update_role(self, user: User, role: str) -> None: ...

    @abstractmethod
    async def set_maturity_override(self, user: User, level: str | None) -> None:
        """Persist the admin maturity pin (None clears it back to assessment-based)."""

    @abstractmethod
    async def delete(self, user: User) -> None:
        """Single DELETE; FK cascades wipe tokens/sessions/progress/survey."""

    @abstractmethod
    async def ids_for_project(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        """Every user id bound to the project (apply-defaults backfill)."""

    @abstractmethod
    async def count_by_ids(self, user_ids: list[uuid.UUID]) -> int:
        """How many of the given user ids exist (bulk-assignment validation)."""


class AbstractAuthTokenRepository(ABC):
    """Single-use invite/reset tokens (auth_tokens)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self, user_id: uuid.UUID, token_hash: str, purpose: str, expires_at: datetime
    ) -> AuthToken: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> AuthToken | None: ...

    @abstractmethod
    async def consume(self, token: AuthToken) -> bool:
        """Atomically mark the token used (consumed_at = now) only if it was not
        already consumed. Returns True if this call consumed it, False if a
        concurrent request beat us to it (enforces single-use under races)."""

    @abstractmethod
    async def delete_unconsumed(self, user_id: uuid.UUID, purpose: str | None = None) -> None:
        """Revoke a user's outstanding tokens by deleting them (all purposes if None)."""

    @abstractmethod
    async def delete_expired(self) -> int:
        """Purge tokens past their expiry (daily cleanup task); returns row count."""


class AbstractAuthSessionRepository(ABC):
    """Refresh-token sessions (auth_sessions)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> AuthSession: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> AuthSession | None: ...

    @abstractmethod
    async def revoke(self, auth_session: AuthSession) -> bool:
        """Atomically set revoked_at (and last_used_at) = now only if the session
        was not already revoked. Returns True if this call revoked it, False if a
        concurrent refresh/logout beat us to it (enforces single-use rotation)."""

    @abstractmethod
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def delete_dead(self) -> int:
        """Purge expired or revoked sessions (daily cleanup task); returns row count."""


class AbstractOrgRepository(ABC):
    """Companies, projects and per-project component settings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def list_companies(self) -> list[Company]:
        """All companies ordered by name."""

    @abstractmethod
    async def list_projects(self) -> list[Project]:
        """All projects ordered by name."""

    @abstractmethod
    async def get_company_by_name_ci(self, name: str) -> Company | None:
        """Case-insensitive exact name match (duplicate check)."""

    @abstractmethod
    async def create_company(self, name: str) -> Company: ...

    @abstractmethod
    async def get_company(self, company_id: uuid.UUID) -> Company | None: ...

    @abstractmethod
    async def get_project(self, project_id: uuid.UUID) -> Project | None: ...

    @abstractmethod
    async def create_project_with_default_components(
        self, name: str, company_id: uuid.UUID, defaults: list[dict[str, Any]]
    ) -> Project:
        """Insert the project and its default component settings in one transaction."""

    @abstractmethod
    async def get_component_settings(
        self, project_id: uuid.UUID
    ) -> list[ProjectComponentSetting]: ...

    @abstractmethod
    async def upsert_component_setting(
        self, project_id: uuid.UUID, component: str, *, hidden: bool, locked: bool
    ) -> None: ...

    @abstractmethod
    async def default_track_ids(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        """Track ids every new participant of the project receives at invite time."""

    @abstractmethod
    async def set_default_tracks(self, project_id: uuid.UUID, track_ids: list[uuid.UUID]) -> None:
        """Full replace of the project's default tracks."""


class AbstractEmailTemplateRepository(ABC):
    """Per-project invite/reset email overrides (project_email_templates)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def get(self, project_id: uuid.UUID, purpose: str) -> ProjectEmailTemplate | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: uuid.UUID) -> list[ProjectEmailTemplate]:
        """Every override row for the project (0–2 rows)."""

    @abstractmethod
    async def upsert(
        self, project_id: uuid.UUID, purpose: str, *, subject: str, body_markdown: str
    ) -> None:
        """Insert or replace the (project, purpose) override."""

    @abstractmethod
    async def delete(self, project_id: uuid.UUID, purpose: str) -> None:
        """Remove the override so the project falls back to the code default."""


class AbstractSurveyRepository(ABC):
    """survey_responses — at most one row per user (UNIQUE user_id)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def get_by_user_id(self, user_id: uuid.UUID) -> SurveyResponse | None: ...

    @abstractmethod
    async def create(self, user_id: uuid.UUID, values: dict[str, Any]) -> SurveyResponse: ...

    @abstractmethod
    async def update(self, row: SurveyResponse, values: dict[str, Any]) -> SurveyResponse: ...

    @abstractmethod
    async def get_complete_levels(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """user_id → score_level for complete surveys among the given users."""


class AbstractContentRepository(ABC):
    """Learning content: tracks, modules, prerequisites, lessons."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- tracks --
    @abstractmethod
    async def list_tracks(self) -> list[Track]:
        """All tracks ordered by sort_order."""

    @abstractmethod
    async def get_track(self, track_id: uuid.UUID) -> Track | None: ...

    @abstractmethod
    async def create_track(
        self, name: str, track_type: str, color: str | None, sort_order: int, required_level: str
    ) -> Track: ...

    @abstractmethod
    async def max_track_sort_order(self) -> int | None: ...

    # -- modules --
    @abstractmethod
    async def list_modules(self, track_id: uuid.UUID | None = None) -> list[Module]:
        """Modules ordered by sort_order, optionally for one track."""

    @abstractmethod
    async def get_module(self, module_id: uuid.UUID) -> Module | None: ...

    @abstractmethod
    async def max_module_sort_order(self, track_id: uuid.UUID) -> int | None: ...

    @abstractmethod
    async def shift_module_sort_orders(self, track_id: uuid.UUID, from_sort_order: int) -> None:
        """+1 every module in the track with sort_order >= from_sort_order."""

    @abstractmethod
    async def create_module(
        self,
        track_id: uuid.UUID,
        title: str,
        sort_order: int,
        prerequisite_ids: list[uuid.UUID],
    ) -> Module:
        """Insert module and its prerequisite links in one transaction."""

    @abstractmethod
    async def next_module_in_track(self, track_id: uuid.UUID, sort_order: int) -> Module | None: ...

    @abstractmethod
    async def list_prerequisites(self) -> list[ModulePrerequisite]: ...

    @abstractmethod
    async def delete_module(self, module: Module) -> None:
        """Cascades to its lessons, prerequisite links (both directions), and
        assignment/progress rows."""

    # -- lessons --
    @abstractmethod
    async def list_lessons(self, module_id: uuid.UUID) -> list[Lesson]:
        """Lessons of a module ordered by sort_order."""

    @abstractmethod
    async def list_lesson_summaries(self) -> list[Lesson]:
        """All lessons ordered by sort_order, content_blocks NOT loaded
        (admin learning overview)."""

    @abstractmethod
    async def count_tracks_by_ids(self, track_ids: list[uuid.UUID]) -> int:
        """How many of the given track ids exist (bulk-assignment validation)."""

    @abstractmethod
    async def count_modules_by_ids(self, module_ids: list[uuid.UUID]) -> int:
        """How many of the given module ids exist (bulk-assignment validation)."""

    @abstractmethod
    async def count_lessons_by_ids(self, lesson_ids: list[uuid.UUID]) -> int:
        """How many of the given lesson ids exist (bulk-assignment validation)."""

    @abstractmethod
    async def get_lesson(self, lesson_id: uuid.UUID) -> Lesson | None: ...

    @abstractmethod
    async def max_lesson_sort_order(self, module_id: uuid.UUID) -> int | None: ...

    @abstractmethod
    async def create_lesson(self, module_id: uuid.UUID, title: str, sort_order: int) -> Lesson: ...

    @abstractmethod
    async def update_lesson(self, lesson: Lesson, values: dict[str, Any]) -> Lesson: ...

    @abstractmethod
    async def delete_lesson(self, lesson: Lesson) -> None: ...

    @abstractmethod
    async def set_lesson_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        """Assign sort_order per lesson id in one transaction (batch reorder)."""


class AbstractFeedbackRepository(ABC):
    """feedback — free-text lesson feedback (one row per submission)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(self, user_id: uuid.UUID, lesson_id: uuid.UUID, message: str) -> Feedback: ...


class AbstractAssignmentRepository(ABC):
    """user_tracks / user_modules / user_lessons assignment links."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def track_ids_for_user(self, user_id: uuid.UUID) -> set[uuid.UUID]: ...

    @abstractmethod
    async def module_ids_for_user(self, user_id: uuid.UUID) -> set[uuid.UUID]: ...

    @abstractmethod
    async def lesson_ids_for_user(self, user_id: uuid.UUID) -> set[uuid.UUID]: ...

    @abstractmethod
    async def all_user_tracks(self) -> list[UserTrack]: ...

    @abstractmethod
    async def all_user_modules(self) -> list[UserModule]: ...

    @abstractmethod
    async def all_user_lessons(self) -> list[UserLesson]: ...

    @abstractmethod
    async def assigned_lesson_counts_by_module(
        self, user_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """module_id → (assigned lessons, assigned-and-completed lessons)."""

    @abstractmethod
    async def assigned_lesson_counts_by_module_for_users(
        self, user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, dict[uuid.UUID, tuple[int, int]]]:
        """Batched variant: user_id → {module_id → (assigned, completed)} for many
        users in ONE query (avoids the per-user N+1 on the admin directory)."""

    @abstractmethod
    async def set_user_track(
        self,
        user_id: uuid.UUID,
        track_id: uuid.UUID,
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        """Idempotent upsert (assigned) or delete (unassigned)."""

    @abstractmethod
    async def set_user_module(
        self,
        user_id: uuid.UUID,
        module_id: uuid.UUID,
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        """Idempotent upsert (assigned) or delete (unassigned)."""

    @abstractmethod
    async def set_user_lesson(
        self,
        user_id: uuid.UUID,
        lesson_id: uuid.UUID,
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        """Idempotent upsert (assigned) or delete (unassigned)."""

    @abstractmethod
    async def set_user_tracks(
        self,
        user_id: uuid.UUID,
        track_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        """Bulk variant of set_user_track, one statement + commit."""

    @abstractmethod
    async def set_user_modules(
        self,
        user_id: uuid.UUID,
        module_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        """Bulk variant of set_user_module, one statement + commit."""

    @abstractmethod
    async def set_user_lessons(
        self,
        user_id: uuid.UUID,
        lesson_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        """Bulk variant of set_user_lesson, one statement + commit."""


class AbstractProgressRepository(ABC):
    """lesson_progress — a row means the lesson is completed by the user."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def get(self, user_id: uuid.UUID, lesson_id: uuid.UUID) -> LessonProgress | None: ...

    @abstractmethod
    async def completed_lesson_ids(
        self, user_id: uuid.UUID, lesson_ids: list[uuid.UUID] | None = None
    ) -> set[uuid.UUID]:
        """The user's completed lesson ids, optionally restricted to a set."""

    @abstractmethod
    async def upsert(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, answers: dict[str, Any]
    ) -> None:
        """ON CONFLICT (user_id, lesson_id): update answers, keep completed_at."""
