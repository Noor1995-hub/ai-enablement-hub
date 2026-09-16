from __future__ import annotations

import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from src.core.configs.settings import Settings
from src.core.dependencies.auth import get_token_service, require_admin
from src.core.dependencies.domain import (
    get_admin_user_service,
    get_email_template_service,
    get_maturity_service,
    get_survey_service,
)
from src.core.dependencies.email import get_email_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.dependencies.settings import get_settings
from src.core.ratelimit import RateLimiter
from src.db.models import User
from src.schemas.admin_users import (
    AdminLearningResponse,
    AdminSurveyOut,
    AdminUserOut,
    AdminUsersResponse,
    AssignmentRequest,
    BulkAssignmentRequest,
    BulkInviteReport,
    BulkInviteRow,
    BulkInviteSummary,
    BulkLessonAssignmentRequest,
    BulkModuleAssignmentRequest,
    BulkTrackAssignmentRequest,
    EmailStatus,
    InviteRequest,
    LinkResponse,
    MaturityOverrideRequest,
    ReminderResponse,
    ResetLinkRequest,
    RoleUpdateRequest,
    SurveyLevelsResponse,
    UserSurveyResponse,
)
from src.services.admin_user_service import AdminUserService
from src.services.email_service import EmailService
from src.services.email_template_service import EmailTemplateService
from src.services.email_templates import REMINDER_TEMPLATE, build_reminder_tokens, render_email
from src.services.exceptions import PayloadTooLargeError
from src.services.invite_csv import MAX_INVITE_CSV_BYTES, build_preview, parse_invite_csv
from src.services.maturity_service import MaturityService
from src.services.survey_service import SurveyService
from src.services.token_service import TokenService

__all__ = ["router"]

router = APIRouter(prefix="/api/admin", tags=["admin:users"], dependencies=[Depends(require_admin)])

logger = logging.getLogger(__name__)

AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
MaturityServiceDep = Annotated[MaturityService, Depends(get_maturity_service)]
SurveyServiceDep = Annotated[SurveyService, Depends(get_survey_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
EmailServiceDep = Annotated[EmailService | None, Depends(get_email_service)]
EmailTemplateServiceDep = Annotated[EmailTemplateService, Depends(get_email_template_service)]

_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many attempts — try again in a minute",
    headers={"Retry-After": "60"},
)


def _invite_link(settings: Settings, raw_token: str) -> str:
    return f"{settings.app.url.rstrip('/')}/invite/{raw_token}"


def _login_url(settings: Settings) -> str | None:
    """The {{login_url}} token target (Microsoft sign-in) — only meaningful, and
    only offered, when Entra login is configured."""
    if settings.entra is None:
        return None
    return f"{settings.app.url.rstrip('/')}/login"


async def _email_the_link(
    email_service: EmailService | None,
    email_template_service: EmailTemplateService,
    *,
    purpose: Literal["invite", "reset"],
    project_id: uuid.UUID | None,
    to: str,
    first_name: str,
    last_name: str,
    link: str,
    ttl_days: int,
    login_url: str | None,
) -> EmailStatus:
    """None service = EMAIL__* unconfigured; a failed send never fails the
    endpoint — the admin falls back to copying the returned link. Content is the
    project's resolved template (custom override or code default)."""
    if email_service is None:
        return "disabled"
    content = await email_template_service.render(
        project_id,
        purpose,
        first_name=first_name,
        last_name=last_name,
        link=link,
        ttl_days=ttl_days,
        login_url=login_url,
    )
    sent = await email_service.send(to, content)
    return "sent" if sent else "failed"


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    admin_user_service: AdminUserServiceDep,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    status: Annotated[Literal["active", "invited", "attention"] | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminUsersResponse:
    """limit/offset/q/status are all optional — omitting them reproduces the
    full list exactly as before Task 9 (the old admin panel sends no query
    params). `total` is additive: count after q/status filtering, before
    limit/offset slicing."""
    users, total = await admin_user_service.list_users(
        project_id, q=q, status=status, limit=limit, offset=offset
    )
    return AdminUsersResponse(
        users=[AdminUserOut.model_validate(user) for user in users], total=total
    )


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
) -> AdminUserOut:
    """One user in the same shape `GET /users` returns (404 for unknown ids) —
    the People detail screen reads this instead of searching a cached page of
    the directory, which silently lost anyone past the first page."""
    return AdminUserOut.model_validate(await admin_user_service.get_user_enriched(user_id))


@router.post("/invites", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteRequest,
    admin_user_service: AdminUserServiceDep,
    token_service: TokenServiceDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    email_service: EmailServiceDep,
    email_template_service: EmailTemplateServiceDep,
) -> LinkResponse:
    """Create the user row + single-use invite token; the link is emailed to
    the user (when EMAIL__* is configured and body.send_email is true) and
    always returned as the admin's manual fallback."""
    if limiter.is_limited(f"invite:{body.email.strip().lower()}"):
        raise _RATE_LIMITED
    user = await admin_user_service.invite(
        body.email, body.first_name, body.last_name, body.project_id
    )
    raw_token = await token_service.issue_action_token(user, "invite")
    link = _invite_link(settings, raw_token)
    email_status: EmailStatus = (
        await _email_the_link(
            email_service,
            email_template_service,
            purpose="invite",
            project_id=body.project_id,
            to=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            link=link,
            ttl_days=settings.auth.invite_ttl_days,
            login_url=_login_url(settings),
        )
        if body.send_email
        else "skipped"
    )
    return LinkResponse(link=link, email_status=email_status)


@router.post("/invites/bulk", response_model=BulkInviteReport)
async def create_bulk_invites(
    admin: Annotated[User, Depends(require_admin)],
    admin_user_service: AdminUserServiceDep,
    token_service: TokenServiceDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    email_service: EmailServiceDep,
    email_template_service: EmailTemplateServiceDep,
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
    existing = await admin_user_service.existing_emails(
        [r.email for r in parsed if r.error is None]
    )
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
                email_service,
                email_template_service,
                purpose="invite",
                project_id=project_id,
                to=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                link=link,
                ttl_days=settings.auth.invite_ttl_days,
                login_url=_login_url(settings),
            )
            if email_status == "failed":
                p.status, p.detail = "email_failed", "user created — email could not be sent"
            else:
                p.status, p.detail = "created", None
        logger.info(
            "bulk invite: admin=%s project=%s created=%d duplicates=%d invalid=%d email_failed=%d",
            admin.id,
            project_id,
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


@router.post("/users/{user_id}/reset-link", response_model=LinkResponse)
async def create_reset_link(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    token_service: TokenServiceDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    email_service: EmailServiceDep,
    email_template_service: EmailTemplateServiceDep,
    body: ResetLinkRequest | None = None,
) -> LinkResponse:
    """Issue a password-reset link (emailed to the user when EMAIL__* is
    configured and body.send_email is true, always returned); prior unused
    reset tokens are revoked either way. An absent body means send_email=True,
    so bodyless callers keep the pre-flag behavior."""
    user = await admin_user_service.get_user(user_id)
    if limiter.is_limited(f"reset:{user.email}"):
        raise _RATE_LIMITED
    raw_token = await token_service.issue_action_token(user, "reset")
    link = _invite_link(settings, raw_token)
    send_email = body is None or body.send_email
    email_status: EmailStatus = (
        await _email_the_link(
            email_service,
            email_template_service,
            purpose="reset",
            project_id=user.project_id,
            to=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            link=link,
            ttl_days=settings.auth.reset_ttl_days,
            login_url=None,
        )
        if send_email
        else "skipped"
    )
    return LinkResponse(link=link, email_status=email_status)


@router.post("/users/{user_id}/reminder", response_model=ReminderResponse)
async def send_reminder(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    email_service: EmailServiceDep,
) -> ReminderResponse:
    """Nudge a learner who has content waiting. The template is a fixed
    module constant (not per-project-customizable, unlike invite/reset) —
    rendered directly via render_email, with no EmailTemplateService lookup."""
    user, project_name = await admin_user_service.reminder_context(user_id)
    if limiter.is_limited(f"reminder:{user.email}"):
        raise _RATE_LIMITED
    if email_service is None:
        return ReminderResponse(email_status="disabled")
    content = render_email(
        REMINDER_TEMPLATE.subject,
        REMINDER_TEMPLATE.body_markdown,
        tokens=build_reminder_tokens(
            first_name=user.first_name,
            last_name=user.last_name,
            project_name=project_name,
            login_url=f"{settings.app.url.rstrip('/')}/login",
        ),
    )
    sent = await email_service.send(user.email, content)
    return ReminderResponse(email_status="sent" if sent else "failed")


@router.patch("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_role(
    user_id: uuid.UUID, body: RoleUpdateRequest, admin_user_service: AdminUserServiceDep
) -> None:
    await admin_user_service.set_role(user_id, body.role)


@router.put("/users/{user_id}/maturity", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_maturity(
    user_id: uuid.UUID, body: MaturityOverrideRequest, maturity_service: MaturityServiceDep
) -> None:
    """Pin (or clear, when level is null) the user's maturity override. This is
    only the base of the live effective-maturity computation — it assigns no
    content and cannot demote below a level the user has already completed."""
    await maturity_service.set_override(user_id, body.level)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, admin_user_service: AdminUserServiceDep) -> None:
    """Single DELETE; FK cascades wipe tokens/sessions/survey/progress (fixes
    the legacy two-system atomicity problem B2 by construction)."""
    await admin_user_service.delete_user(user_id)


@router.put("/users/{user_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_track(
    user_id: uuid.UUID,
    track_id: uuid.UUID,
    body: AssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    await admin_user_service.set_track_assignment(user_id, track_id, body.assigned)


@router.put("/users/{user_id}/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_module(
    user_id: uuid.UUID,
    module_id: uuid.UUID,
    body: AssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    await admin_user_service.set_module_assignment(user_id, module_id, body.assigned)


@router.put("/users/{user_id}/tracks", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_tracks(
    user_id: uuid.UUID,
    body: BulkTrackAssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    """Bulk assign/unassign tracks ("Add/unassign all tracks"); 404 if any id is unknown."""
    await admin_user_service.set_track_assignments(user_id, body.track_ids, body.assigned)


@router.put("/users/{user_id}/modules", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_modules(
    user_id: uuid.UUID,
    body: BulkModuleAssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    """Bulk assign/unassign modules ("Add all modules"); 404 if any id is unknown."""
    await admin_user_service.set_module_assignments(user_id, body.module_ids, body.assigned)


@router.put("/users/{user_id}/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_lesson(
    user_id: uuid.UUID,
    lesson_id: uuid.UUID,
    body: AssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    await admin_user_service.set_lesson_assignment(user_id, lesson_id, body.assigned)


@router.put("/users/{user_id}/lessons", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_lessons(
    user_id: uuid.UUID,
    body: BulkLessonAssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    """Bulk assign/unassign lessons ("Add all lessons"); 404 if any id is unknown."""
    await admin_user_service.set_lesson_assignments(user_id, body.lesson_ids, body.assigned)


@router.post("/assignments/bulk", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_assign(body: BulkAssignmentRequest, admin_user_service: AdminUserServiceDep) -> None:
    """Many-users × one content kind ("assign N users to this track/module/
    lesson"); 404 if any user or content id is unknown, validated before any
    write. The schema enforces exactly one of track_ids/module_ids/lesson_ids."""
    await admin_user_service.bulk_assign(
        body.user_ids,
        track_ids=body.track_ids,
        module_ids=body.module_ids,
        lesson_ids=body.lesson_ids,
        assigned=body.assigned,
    )


@router.get("/learning", response_model=AdminLearningResponse)
async def get_learning_overview(
    admin_user_service: AdminUserServiceDep,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminLearningResponse:
    """Paginates the `users` array only — `modules`/`lessons` always come back
    complete. limit/offset/project_id are optional, so omitting them
    reproduces the pre-Task-9 full (unscoped) list, plus the additive `total`."""
    overview = await admin_user_service.learning_overview(
        project_id=project_id, limit=limit, offset=offset
    )
    return AdminLearningResponse(**overview)


@router.get("/surveys", response_model=SurveyLevelsResponse)
async def get_survey_levels(
    survey_service: SurveyServiceDep,
    user_ids: Annotated[str | None, Query(description="comma-separated user UUIDs")] = None,
) -> SurveyLevelsResponse:
    if not user_ids:
        return SurveyLevelsResponse(levels={})
    try:
        parsed = [uuid.UUID(item.strip()) for item in user_ids.split(",") if item.strip()]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="user_ids must be comma-separated UUIDs",
        ) from exc
    return SurveyLevelsResponse(levels=await survey_service.complete_levels(parsed))


@router.get("/surveys/{user_id}", response_model=UserSurveyResponse)
async def get_user_survey(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    survey_service: SurveyServiceDep,
) -> UserSurveyResponse:
    """The user's completed survey (or null) — admin results panel."""
    await admin_user_service.get_user(user_id)  # 404 for unknown users
    row = await survey_service.complete_survey_for(user_id)
    return UserSurveyResponse(
        survey=AdminSurveyOut.model_validate(row) if row is not None else None
    )
