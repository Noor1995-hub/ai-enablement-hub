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
        CalibrationNote,
        Company,
        Conversation,
        Feedback,
        Lesson,
        LessonContentProposal,
        LessonProgress,
        Message,
        Module,
        ModulePrerequisite,
        Project,
        ProjectAiSetting,
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
    "AbstractCalibrationNoteRepository",
    "AbstractContentRepository",
    "AbstractConversationRepository",
    "AbstractEmailTemplateRepository",
    "AbstractFeedbackRepository",
    "AbstractMessageRepository",
    "AbstractOrgRepository",
    "AbstractProgressRepository",
    "AbstractProposalRepository",
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
        self, project_id: uuid.UUID | None = None, q: str | None = None
    ) -> list[tuple[User, str | None, str | None]]:
        """(user, company_name, project_name) newest-first, optionally by
        project and/or a case-insensitive substring match over first_name,
        last_name, email (q)."""

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
    async def last_used_by_user(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        """user_id -> most recent session last_used_at (admin "last active").
        An absent key means the user was never active (no session use yet)."""

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
    async def get_ai_settings(self, project_id: uuid.UUID) -> list[ProjectAiSetting]: ...

    @abstractmethod
    async def upsert_ai_setting(
        self, project_id: uuid.UUID, kind: str, *, enabled: bool
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

    @abstractmethod
    async def user_ids_with_survey(self, user_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """Which of the given users have any survey row at all (a draft counts
        as "assessment started", spec §4.4)."""


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
    async def lesson_context(
        self, lesson_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str, uuid.UUID, str, str]]:
        """Module/track labels for the given lessons, keyed by lesson id, as
        `(module_title, track_id, track_name, track_level)`.

        One batched read for a list of lessons the caller already has — the
        content-improvement queue needs the same Track/Module chips the proposal
        rows show. A lesson id with no row in the result simply has no context;
        callers must tolerate that rather than assume every id comes back.
        """

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

    @abstractmethod
    async def get_by_id(self, feedback_id: uuid.UUID) -> Feedback | None: ...

    @abstractmethod
    async def set_status(
        self, feedback: Feedback, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        """Update status + reviewer stamp; reviewed_by=None clears reviewed_at too."""

    @abstractmethod
    async def list_admin(
        self,
        *,
        status: str | None = None,
        track_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        limit: int,
        offset: int,
    ) -> list[Any]:
        """Joined admin queue rows (feedback + reporter/org/lesson/module/track names)."""

    @abstractmethod
    async def count_admin(
        self,
        *,
        status: str | None = None,
        track_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> int:
        """Total rows matching the same filters as list_admin (pagination total)."""

    @abstractmethod
    async def count_new(self, project_id: uuid.UUID | None = None) -> int:
        """How many feedback rows are still status='new', optionally scoped to a project."""

    @abstractmethod
    async def list_awaiting_suggestion(
        self, *, project_id: uuid.UUID | None = None, limit: int
    ) -> list[tuple[Feedback, Lesson]]:
        """`new` feedback that has no AI triage suggestion yet
        (`ai_suggested_at IS NULL`), oldest first, joined to its lesson (the
        triage agent's context). Bounded by `limit` — a run is never unbounded."""

    @abstractmethod
    async def count_awaiting_suggestion(self, *, project_id: uuid.UUID | None = None) -> int:
        """How many `new` rows still lack a suggestion (the "remaining" figure
        an admin sees after a bounded run)."""

    @abstractmethod
    async def set_ai_suggestion(
        self, feedback: Feedback, *, suggested_status: str, rationale: str
    ) -> None:
        """Write the three ai_* columns and stamp ai_suggested_at. NEVER touches
        `status`/`reviewed_by` — an AI suggestion is advice, the admin decides."""

    @abstractmethod
    async def mark_suggestion_attempted(self, feedback: Feedback) -> None:
        """Stamp `ai_suggested_at` WITHOUT a suggestion, so a row whose triage
        attempt failed drops out of the awaiting queue instead of re-consuming
        every future bounded run (the queue is oldest-first, so a permanently
        failing row would otherwise starve newer feedback). One attempt per
        row: the admin triages this one by hand, as they did before AI triage
        existed. Like set_ai_suggestion, it never touches the real `status`."""

    @abstractmethod
    async def list_accepted_with_lesson(self) -> list[tuple[Feedback, Lesson]]:
        """Every `status='accepted'` row joined to its lesson, oldest first.
        The content-improvement run subtracts the already-incorporated ids from
        this and groups what is left by lesson."""

    @abstractmethod
    async def list_by_ids(self, feedback_ids: list[uuid.UUID]) -> list[Feedback]:
        """The given feedback rows (proposal provenance display). An empty
        input returns an empty list without touching the database."""


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
    async def user_tracks_for_users(self, user_ids: list[uuid.UUID]) -> list[UserTrack]:
        """Every user_tracks row for the given users (carries assigned_via)."""

    @abstractmethod
    async def user_modules_for_users(self, user_ids: list[uuid.UUID]) -> list[UserModule]:
        """Every user_modules row for the given users (carries assigned_via)."""

    @abstractmethod
    async def user_lessons_for_users(self, user_ids: list[uuid.UUID]) -> list[UserLesson]:
        """Every user_lessons row for the given users (carries assigned_via)."""

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
    async def latest_completion_by_user(
        self, user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, datetime]:
        """user_id -> most recent lesson completion time (stall detection).
        An absent key means the user has completed nothing."""

    @abstractmethod
    async def upsert(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, answers: dict[str, Any]
    ) -> None:
        """ON CONFLICT (user_id, lesson_id): update answers, keep completed_at."""


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

    @abstractmethod
    async def update_summary(self, conversation_id: uuid.UUID, summary: dict[str, Any]) -> None:
        """Persist the interviewer's structured extraction into conversations.summary."""

    @abstractmethod
    async def delete(self, conversation_id: uuid.UUID) -> None:
        """Remove the conversation (and its messages, via FK cascade)."""


class AbstractMessageRepository(ABC):
    """messages — every chat turn, both sides (the 'save all dialogue' table)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self,
        conversation_id: uuid.UUID,
        *,
        role: str,
        content: str,
        metadata: dict[str, Any] | None,
    ) -> Message: ...

    @abstractmethod
    async def list_for_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        """Chronological, for the conversation-detail view."""

    @abstractmethod
    async def list_recent(self, conversation_id: uuid.UUID, *, limit: int) -> list[Message]:
        """Last `limit` messages, chronological order (window cap sent to the model)."""


class AbstractProposalRepository(ABC):
    """lesson_content_proposals — AI-drafted lesson revisions awaiting review."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self,
        *,
        lesson_id: uuid.UUID,
        proposed_blocks: list[Any],
        base_blocks: list[Any],
        source_feedback_ids: list[uuid.UUID],
        summary: str,
        status: str = "pending",
    ) -> LessonContentProposal:
        """Insert a draft. The feedback ids are stored as strings so the JSONB
        round-trip is lossless."""

    @abstractmethod
    async def get_by_id(self, proposal_id: uuid.UUID) -> LessonContentProposal | None: ...

    @abstractmethod
    async def covered_feedback_ids(self) -> set[uuid.UUID]:
        """Feedback ids already carried by a pending/approved/failed proposal —
        i.e. "incorporated" for the purposes of a run, so re-running never
        re-drafts the same feedback. `rejected` and `superseded` are absent on
        purpose: their source feedback becomes eligible again."""

    @abstractmethod
    async def list_admin(self, *, status: str | None = None, limit: int, offset: int) -> list[Any]:
        """Newest-first review queue rows (proposal + lesson/module/track names)."""

    @abstractmethod
    async def count_admin(self, *, status: str | None = None) -> int:
        """Total rows matching the same filter as list_admin (pagination total)."""

    @abstractmethod
    async def set_status(
        self, proposal: LessonContentProposal, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        """Update status + reviewer stamp; reviewed_by=None clears reviewed_at too."""

    @abstractmethod
    async def set_approved(
        self,
        proposal: LessonContentProposal,
        *,
        edited_blocks: list[Any] | None,
        reviewed_by: uuid.UUID,
    ) -> None:
        """Mark approved and stamp the reviewer. `edited_blocks` is the array
        the admin actually submitted, and is stored ONLY when it differed from
        `proposed_blocks` — passing None keeps the column NULL, which is the
        signal that the draft was accepted exactly as written and there is
        nothing to learn from it. `proposed_blocks` is never overwritten."""

    @abstractmethod
    async def set_critique(
        self, proposal: LessonContentProposal, *, agent_wrong: str, admin_preferred: str
    ) -> None:
        """Store the agent's self-assessment of the difference between its
        draft and the admin's version, and stamp `critiqued_at`."""


class AbstractCalibrationNoteRepository(ABC):
    """calibration_notes — guidance the agent suggested about its own drafting,
    pending an admin's approval before it can influence anything."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create_many(
        self, *, source_proposal_id: uuid.UUID, notes: list[str]
    ) -> list[CalibrationNote]:
        """One `suggested` row per note string, in the order given. An empty
        `notes` list inserts nothing and issues no statement."""

    @abstractmethod
    async def list_for_proposal(self, proposal_id: uuid.UUID) -> list[CalibrationNote]:
        """Every note distilled from this proposal, oldest first (the order the
        agent produced them in)."""

    @abstractmethod
    async def get_by_id(self, note_id: uuid.UUID) -> CalibrationNote | None: ...

    @abstractmethod
    async def list_admin(self, *, status: str | None = None, limit: int, offset: int) -> list[Any]:
        """Newest-first review rows: (note, source_lesson_id, source_lesson_title).
        BOTH joins are outer — `source_proposal_id` is ON DELETE SET NULL, so an
        approved note outlives the lesson it came from and must not disappear
        from the queue when that lesson is deleted.

        The order must be TOTAL, not just newest-first: one `create_many` batch
        shares a single `created_at`, so a tiebreaker is what stops a paged read
        from returning a row twice or skipping it entirely."""

    @abstractmethod
    async def count_admin(self, *, status: str | None = None) -> int:
        """Total rows matching the same filter as list_admin (pagination total)."""

    @abstractmethod
    async def set_status(
        self, note: CalibrationNote, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        """Update status + reviewer stamp; reviewed_by=None clears reviewed_at too
        (same contract as the sibling repositories)."""

    @abstractmethod
    async def list_for_injection(self, *, limit: int) -> list[str]:
        """Approved note TEXT ONLY, most-recently-approved first, capped at
        `limit`. Only `approved` — a `suggested` note has not been through the
        human gate, and `rejected`/`retired` are deliberately out (retired means
        it was hand-copied into house_style.md and injecting it too would
        duplicate it). A row with no `reviewed_at` sorts LAST, never first, so
        an unstamped approval can never displace the newest real guidance. The
        caller applies the character budget on top, via
        services/calibration_prompt.py::render_calibration_block."""
