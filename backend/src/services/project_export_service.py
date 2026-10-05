"""Project data export (#92): one .xlsx of a project's learners, one sheet per
section the admin ticked — people, assessment, progress, interview.

Who's in it: the project's learners only. Power admins and the project's own
admins are staff, not learners, and are left out (the dashboard's rule, spec
2026-10-01 §6). Someone who runs another project but is a member of this one
IS a learner here, although the People directory's learners-only view hides
anyone who runs any project. The file holds personal data; the router logs ids
only, never emails.

Like DashboardService it reuses the pure rules (`advance_level`,
`module_level_map`, the survey label maps, `strip_ready_marker`) and calls no
other service."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from src.core import survey_labels
from src.core.constants import advance_level, module_level_map
from src.core.xlsx import Sheet, render_workbook
from src.services.exceptions import NotFoundError
from src.services.interview_language import resolve_language
from src.services.interview_marker import strip_ready_marker

if TYPE_CHECKING:
    import uuid
    from collections.abc import Collection

    from src.core.xlsx import Cell
    from src.db.models import Conversation, SurveyResponse, User
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractAuthSessionRepository,
        AbstractContentRepository,
        AbstractConversationRepository,
        AbstractMessageRepository,
        AbstractOrgRepository,
        AbstractProgressRepository,
        AbstractProjectAdminRepository,
        AbstractSurveyRepository,
        AbstractUserRepository,
    )

__all__ = ["ProjectExport", "ProjectExportService"]

_LEARNER = ("First name", "Last name", "Email")
_SPEAKER = {"user": "Learner", "assistant": "Interviewer"}


@dataclass(frozen=True)
class ProjectExport:
    filename: str
    content: bytes


def _learner(user: User) -> list[Cell]:
    return [user.first_name, user.last_name, user.email]


def _status(user: User) -> str:
    if not user.is_active:
        return "Deactivated"
    return "Active" if user.password_set or user.external_id is not None else "Invited"


def _label(code: str | int | None, mapping: dict[Any, str]) -> str | None:
    return None if code is None else mapping.get(code, str(code))


def _labels(codes: list[str] | None, mapping: dict[str, str]) -> str | None:
    return None if not codes else "; ".join(mapping.get(code, code) for code in codes)


def _codes(codes: list[str] | None) -> str | None:
    return None if not codes else "; ".join(codes)


def _yes_no(value: bool | None) -> str | None:
    return None if value is None else ("Yes" if value else "No")


def _flatten(value: Any, path: str) -> list[tuple[str, str]]:
    """A playbook box (nested dicts/lists of the stored JSON) as (field, text)
    pairs, e.g. ("use_cases[1].pain_it_kills", "..."). Read from the raw JSON,
    not the pydantic schema, so an older playbook shape still exports."""
    if isinstance(value, dict):
        return [
            pair
            for key, item in value.items()
            for pair in _flatten(item, f"{path}.{key}" if path else str(key))
        ]
    if isinstance(value, list):
        return [
            pair
            for index, item in enumerate(value, 1)
            for pair in _flatten(item, f"{path}[{index}]")
        ]
    if value is None:
        return [(path, "")]
    if isinstance(value, bool):
        return [(path, "Yes" if value else "No")]
    return [(path, str(value))]


def _filename(project_name: str, today: datetime) -> str:
    ascii_name = unicodedata.normalize("NFKD", project_name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "project"
    return f"{slug}-export-{today:%Y-%m-%d}.xlsx"


class ProjectExportService:
    def __init__(
        self,
        users: AbstractUserRepository,
        org: AbstractOrgRepository,
        project_admins: AbstractProjectAdminRepository,
        sessions: AbstractAuthSessionRepository,
        surveys: AbstractSurveyRepository,
        assignments: AbstractAssignmentRepository,
        content: AbstractContentRepository,
        progress: AbstractProgressRepository,
        conversations: AbstractConversationRepository,
        messages: AbstractMessageRepository,
    ) -> None:
        self._users = users
        self._org = org
        self._project_admins = project_admins
        self._sessions = sessions
        self._surveys = surveys
        self._assignments = assignments
        self._content = content
        self._progress = progress
        self._conversations = conversations
        self._messages = messages

    async def export(self, project_id: uuid.UUID, sections: Collection[str]) -> ProjectExport:
        """`sections` is already validated against EXPORT_SECTIONS by the router;
        sheets come out in the fixed EXPORT_SECTIONS order whatever the input order."""
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")

        staff = await self._project_admins.admin_ids_for_project(project_id)
        learners = [
            user
            for user, _, _ in await self._users.list_with_org_names(project_id)
            if user.role != "admin" and user.id not in staff
        ]
        learners.sort(key=lambda u: (u.last_name.casefold(), u.first_name.casefold(), u.email))
        surveys = {s.user_id: s for s in await self._surveys.list_for_users(_ids(learners))}

        sheets: list[Sheet] = []
        if "people" in sections:
            sheets.append(await self._people(learners, surveys))
        if "assessment" in sections:
            sheets.append(self._assessment(learners, surveys))
        if "progress" in sections:
            sheets.append(await self._progress_sheet(learners))
        if "interview" in sections:
            sheets.extend(await self._interview(learners))

        now = datetime.now(UTC)
        return ProjectExport(_filename(project.name, now), render_workbook(sheets))

    async def _people(
        self, learners: list[User], surveys: dict[uuid.UUID, SurveyResponse]
    ) -> Sheet:
        user_ids = _ids(learners)
        last_active = await self._sessions.last_used_by_user(user_ids)
        counts = await self._assignments.assigned_lesson_counts_by_module_for_users(user_ids)
        module_level = module_level_map(
            await self._content.list_tracks(), await self._content.list_modules()
        )
        sheet = Sheet(
            "People",
            [
                *_LEARNER,
                "Status",
                "Maturity",
                "Maturity pinned by admin",
                "Assessment",
                "Last active (UTC)",
                "Invited on (UTC)",
            ],
        )
        for user in learners:
            survey = surveys.get(user.id)
            scored = survey.score_level if survey and survey.status == "complete" else None
            base = user.maturity_override or scored
            maturity = advance_level(base, module_level, counts.get(user.id, {})) if base else None
            sheet.rows.append(
                [
                    *_learner(user),
                    _status(user),
                    maturity,
                    user.maturity_override,
                    _assessment_status(survey),
                    last_active.get(user.id),
                    user.created_at,
                ]
            )
        return sheet

    @staticmethod
    def _assessment(learners: list[User], surveys: dict[uuid.UUID, SurveyResponse]) -> Sheet:
        competency_headers = [
            header
            for c in survey_labels.COMPETENCIES
            for header in (f"{c.key.upper()} {c.label}", f"{c.key.upper()} code")
        ]
        sheet = Sheet(
            "Assessment",
            [
                *_LEARNER,
                "Status",
                "Started (UTC)",
                "Completed (UTC)",
                "Job title",
                "Department",
                "Score level",
                *(f"{c.key.upper()} rung" for c in survey_labels.COMPETENCIES),
                "Usage band",
                "Safety flag",
                *competency_headers,
                "AI use frequency",
                "AI use frequency code",
                "Breadth of use",
                "Breadth of use code",
                "Tools used",
                "Tools used codes",
                "Things set up",
                "Things set up codes",
                "Barriers",
                "Barriers codes",
                "Attitude",
                "Attitude code",
                "Readiness to change",
                "Readiness to change code",
                "What excites you",
                "Biggest time sink",
            ],
        )
        for user in learners:
            survey = surveys.get(user.id)
            if survey is None:
                continue
            competencies: list[Cell] = []
            for c in survey_labels.COMPETENCIES:
                if c.multi:
                    codes = survey.c5_codes
                    competencies += [_labels(codes, c.options), _codes(codes)]
                else:
                    code = getattr(survey, f"{c.key}_code")
                    competencies += [_label(code, c.options), code]
            sheet.rows.append(
                [
                    *_learner(user),
                    _assessment_status(survey),
                    survey.started_at,
                    survey.completed_at,
                    survey.job_title,
                    survey.department,
                    survey.score_level,
                    *(getattr(survey, f"{c.key}_rung") for c in survey_labels.COMPETENCIES),
                    survey.usage_band,
                    _yes_no(survey.safety_flag),
                    *competencies,
                    _label(survey.b_freq, survey_labels.FREQ),
                    survey.b_freq,
                    _label(survey.b_breadth, survey_labels.BREADTH),
                    survey.b_breadth,
                    _labels(survey.b_tools, survey_labels.TOOLS),
                    _codes(survey.b_tools),
                    _labels(survey.b_setup, survey_labels.SETUP),
                    _codes(survey.b_setup),
                    _labels(survey.b_barriers, survey_labels.BARRIERS),
                    _codes(survey.b_barriers),
                    _label(survey.b_attitude, survey_labels.ATTITUDE),
                    survey.b_attitude,
                    _label(survey.b_readiness, survey_labels.READINESS),
                    survey.b_readiness,
                    survey.q_excitement,
                    survey.q_timesink,
                ]
            )
        return sheet

    async def _progress_sheet(self, learners: list[User]) -> Sheet:
        """One row per lesson a learner is assigned OR has completed (Introduction
        lessons and freely reviewable lower tracks can be completed unassigned)."""
        user_ids = _ids(learners)
        assigned = {
            (link.user_id, link.lesson_id)
            for link in await self._assignments.user_lessons_for_users(user_ids)
        }
        completed = await self._progress.completions_for_users(user_ids)
        tracks = {track.id: track for track in await self._content.list_tracks()}
        modules = {module.id: module for module in await self._content.list_modules()}
        lessons = {lesson.id: lesson for lesson in await self._content.list_lesson_summaries()}

        def outline(lesson_id: uuid.UUID) -> tuple[int, int, int, str]:
            lesson = lessons[lesson_id]
            module = modules[lesson.module_id]
            track = tracks[module.track_id]
            return (track.sort_order, module.sort_order, lesson.sort_order, str(lesson_id))

        per_user: dict[uuid.UUID, set[uuid.UUID]] = {}
        for user_id, lesson_id in assigned | completed.keys():
            if lesson_id in lessons:
                per_user.setdefault(user_id, set()).add(lesson_id)

        sheet = Sheet(
            "Progress",
            [*_LEARNER, "Track", "Module", "Lesson", "Assigned", "Completed", "Completed on (UTC)"],
        )
        for user in learners:
            for lesson_id in sorted(per_user.get(user.id, ()), key=outline):
                lesson = lessons[lesson_id]
                module = modules[lesson.module_id]
                done_at = completed.get((user.id, lesson_id))
                sheet.rows.append(
                    [
                        *_learner(user),
                        tracks[module.track_id].name,
                        module.title,
                        lesson.title,
                        _yes_no((user.id, lesson_id) in assigned),
                        _yes_no(done_at is not None),
                        done_at,
                    ]
                )
        return sheet

    async def _interview(self, learners: list[User]) -> list[Sheet]:
        by_user = {
            conversation.user_id: conversation
            for conversation in await self._conversations.interviews_for_users(_ids(learners))
        }
        messages: dict[uuid.UUID, list[Any]] = {}
        for message in await self._messages.list_for_conversations(
            [conversation.id for conversation in by_user.values()]
        ):
            messages.setdefault(message.conversation_id, []).append(message)

        header = [*_LEARNER, "Interview status", "Language"]
        playbook = Sheet("Interview playbook", [*header, "Part", "Field", "Value"])
        transcript = Sheet("Interview transcript", [*header, "#", "Speaker", "Sent (UTC)", "Text"])
        for user in learners:
            conversation = by_user.get(user.id)
            if conversation is None:
                continue
            context: list[Cell] = [
                *_learner(user),
                _interview_status(conversation),
                resolve_language(conversation.language),
            ]
            summary = conversation.summary if isinstance(conversation.summary, dict) else {}
            for part in ("shared", "internal"):
                if part in summary:
                    for path, text in _flatten(summary[part], ""):
                        playbook.rows.append([*context, part, path, text])
            for number, message in enumerate(messages.get(conversation.id, []), 1):
                transcript.rows.append(
                    [
                        *context,
                        number,
                        _SPEAKER.get(message.role, message.role),
                        message.created_at,
                        strip_ready_marker(message.content),
                    ]
                )
        return [playbook, transcript]


def _ids(users: list[User]) -> list[uuid.UUID]:
    return [user.id for user in users]


def _assessment_status(survey: SurveyResponse | None) -> str:
    if survey is None:
        return "Not started"
    return "Complete" if survey.status == "complete" else "Draft"


def _interview_status(conversation: Conversation) -> str:
    # Same test as InterviewService: a stored summary means the playbook was built.
    return "Complete" if conversation.summary is not None else "In progress"
