from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.security import hash_password
from src.db.models import (
    Company,
    Lesson,
    LessonProgress,
    Module,
    ModulePrerequisite,
    Project,
    ProjectComponentSetting,
    SurveyResponse,
    Track,
    User,
    UserLesson,
    UserModule,
    UserTrack,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "VALID_ANSWERS",
    "assign_lesson",
    "assign_module",
    "assign_track",
    "complete_lesson",
    "create_company",
    "create_lesson",
    "create_module",
    "create_prerequisite",
    "create_project",
    "create_survey",
    "create_track",
    "create_user",
    "unlock_component",
]


async def _persist[T](session: AsyncSession, instance: T) -> T:
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return instance


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str | None = None,
    role: str = "user",
    is_active: bool = True,
    first_name: str = "Test",
    last_name: str = "User",
    company_id: Any = None,
    project_id: Any = None,
) -> User:
    """Insert a user row; password=None mirrors a freshly-invited user."""
    return await _persist(
        session,
        User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=is_active,
            company_id=company_id,
            project_id=project_id,
            password_hash=hash_password(password) if password is not None else None,
            password_set=password is not None,
        ),
    )


async def create_company(session: AsyncSession, name: str = "Acme") -> Company:
    return await _persist(session, Company(name=name))


async def create_project(session: AsyncSession, company: Company, name: str = "Rollout") -> Project:
    """Bare project row — deliberately without component settings, so tests can
    cover the defaults fallback. Use the POST endpoint for the full behavior."""
    return await _persist(session, Project(name=name, company_id=company.id))


async def unlock_component(
    session: AsyncSession,
    project: Project,
    component: str,
    *,
    hidden: bool = False,
    locked: bool = False,
) -> None:
    """Directly upsert a component row — the component-lock hard gate
    (require_component_unlocked) 403s any caller whose project has it hidden or
    locked, so any test exercising that component's endpoints needs this (the
    `locked=True` override lets tests also cover the still-locked case)."""
    stmt = pg_insert(ProjectComponentSetting).values(
        project_id=project.id, component=component, hidden=hidden, locked=locked
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["project_id", "component"],
        set_={"hidden": stmt.excluded.hidden, "locked": stmt.excluded.locked},
    )
    await session.execute(stmt)
    await session.commit()


async def create_track(
    session: AsyncSession,
    name: str = "Core Track",
    *,
    track_type: str = "general",
    color: str | None = None,
    sort_order: int = 0,
    required_level: str = "explore",
    is_introduction: bool = False,
) -> Track:
    return await _persist(
        session,
        Track(
            name=name,
            track_type=track_type,
            color=color,
            sort_order=sort_order,
            required_level=required_level,
            is_introduction=is_introduction,
        ),
    )


async def create_module(
    session: AsyncSession, track: Track, title: str = "Module", *, sort_order: int = 0
) -> Module:
    return await _persist(session, Module(track_id=track.id, title=title, sort_order=sort_order))


async def create_prerequisite(
    session: AsyncSession, module: Module, prerequisite: Module
) -> ModulePrerequisite:
    return await _persist(
        session,
        ModulePrerequisite(module_id=module.id, prerequisite_module_id=prerequisite.id),
    )


async def create_lesson(
    session: AsyncSession,
    module: Module,
    title: str = "Lesson",
    *,
    sort_order: int = 0,
    content_blocks: list[Any] | None = None,
) -> Lesson:
    return await _persist(
        session,
        Lesson(
            module_id=module.id,
            title=title,
            sort_order=sort_order,
            content_blocks=content_blocks or [],
        ),
    )


async def assign_track(session: AsyncSession, user: User, track: Track) -> UserTrack:
    return await _persist(session, UserTrack(user_id=user.id, track_id=track.id))


async def assign_module(session: AsyncSession, user: User, module: Module) -> UserModule:
    return await _persist(session, UserModule(user_id=user.id, module_id=module.id))


async def assign_lesson(session: AsyncSession, user: User, lesson: Lesson) -> UserLesson:
    return await _persist(session, UserLesson(user_id=user.id, lesson_id=lesson.id))


async def complete_lesson(
    session: AsyncSession, user: User, lesson: Lesson, answers: dict[str, Any] | None = None
) -> LessonProgress:
    return await _persist(
        session, LessonProgress(user_id=user.id, lesson_id=lesson.id, answers=answers or {})
    )


# A full, valid, competent answer set — scores to practitioner.
VALID_ANSWERS: dict[str, Any] = {
    "c1_code": "HAVE",
    "c2_code": "HAVE",
    "c3_code": "HAVE",
    "c4_code": "PARTIAL",
    "c5_codes": ["KEPT_OUT"],
    "c6_code": "HAVE",
    "b_freq": "WEEKLY",
    "b_breadth": "SEVERAL",
}


async def create_survey(
    session: AsyncSession, user: User, *, status: str = "in_progress", **fields: Any
) -> SurveyResponse:
    values: dict[str, Any] = {**VALID_ANSWERS, **fields}
    return await _persist(session, SurveyResponse(user_id=user.id, status=status, **values))
