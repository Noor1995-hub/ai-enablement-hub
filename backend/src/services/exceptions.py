from __future__ import annotations

__all__ = [
    "AdminTargetForbiddenError",
    "AiGenerationError",
    "AssessmentRequiredError",
    "AuthError",
    "ComponentLockedError",
    "ConflictError",
    "DomainError",
    "DuplicateCompanyNameError",
    "EmailAlreadyRegisteredError",
    "EntraExchangeError",
    "EntraUserNotFoundError",
    "InvalidCredentialsError",
    "InvalidCsvError",
    "InvalidEmailTemplateError",
    "InvalidRequestError",
    "InvalidSessionError",
    "LastPowerAdminError",
    "LessonNotAccessibleError",
    "LessonSetMismatchError",
    "NotFoundError",
    "PayloadTooLargeError",
    "SelfModificationError",
    "SurveyAlreadyCompleteError",
    "SurveyNotInProgressError",
    "TokenExpiredError",
    "TokenNotFoundError",
    "UnsupportedMediaTypeError",
]


class AuthError(Exception):
    """Base for auth use-case failures; routers map subclasses to HTTP errors."""


class InvalidCredentialsError(AuthError):
    """Login failed (unknown email, wrong password, no password set, inactive). → 401"""


class InvalidSessionError(AuthError):
    """Refresh token unknown, revoked, expired, or its user is gone/inactive. → 401"""


class TokenNotFoundError(AuthError):
    """Invite/reset token unknown, already used, or its user is gone/inactive. → 404"""


class TokenExpiredError(AuthError):
    """Invite/reset token exists but is past its expiry. → 410"""


class EntraExchangeError(AuthError):
    """Entra code exchange or id_token validation failed. → redirect ?error=entra_failed"""


class EntraUserNotFoundError(AuthError):
    """Microsoft account has no matching invited hub user (or it is inactive).
    → redirect ?error=not_invited"""


class DomainError(Exception):
    """Base for non-auth use-case failures; carries the client-facing message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """A referenced entity does not exist. → 404"""

    def __init__(self, entity: str) -> None:
        super().__init__(f"{entity} not found")


class ComponentLockedError(DomainError):
    """The caller's project has this hub component (assessment/learning/
    interview) hidden, or locked and the caller doesn't bypass locks (power
    admins and project admins on their own project do). → 403"""

    def __init__(self, component: str) -> None:
        super().__init__(f"The {component} component is not available for your project")


class LessonNotAccessibleError(DomainError):
    """The lesson exists, but it is neither assigned to the caller nor in a
    track their effective maturity covers. → 403

    Distinct from ComponentLockedError: that one is a project-level switch,
    this one is per-lesson. Both are bypassed by AdminScopeService.bypasses_locks.
    """

    def __init__(self) -> None:
        super().__init__("This lesson is not available on your learning path")


class AssessmentRequiredError(DomainError):
    """The interview is briefed from the caller's completed assessment, so it needs one.
    Callers who bypass locks are exempt so they can test the flow (spec 2026-10-01
    decision 5). → 403"""

    def __init__(self) -> None:
        super().__init__("Complete your assessment before starting the interview")


class AdminTargetForbiddenError(DomainError):
    """A project admin addressed a power admin, another project admin, or
    themselves through a scoped admin route. → 403"""

    def __init__(self) -> None:
        super().__init__("Project admins can only manage learners")


class ConflictError(DomainError):
    """The request conflicts with current state. → 409"""


class EmailAlreadyRegisteredError(ConflictError):
    def __init__(self) -> None:
        super().__init__("A user with this email already exists")


class SelfModificationError(ConflictError):
    def __init__(self) -> None:
        super().__init__("You can't change your own role or delete your own account")


class LastPowerAdminError(ConflictError):
    def __init__(self) -> None:
        super().__init__("At least one power admin must remain")


class DuplicateCompanyNameError(ConflictError):
    def __init__(self) -> None:
        super().__init__("A company with this name already exists")


class SurveyAlreadyCompleteError(ConflictError):
    def __init__(self) -> None:
        super().__init__("The survey is already complete and can no longer be edited")


class SurveyNotInProgressError(ConflictError):
    """Complete called with no in-progress draft (fixes legacy issue B3). → 409"""

    def __init__(self) -> None:
        super().__init__("There is no in-progress survey to complete — save your answers first")


class InvalidRequestError(DomainError):
    """Structurally valid request that references the wrong thing. → 400"""


class InvalidEmailTemplateError(DomainError):
    """A per-project email template an admin tried to save is malformed
    (blank, references an unknown token, or is missing its link token). → 400"""


class InvalidCsvError(DomainError):
    """The uploaded CSV cannot be processed as a whole (bad encoding, empty,
    missing a required column, or too many rows). → 400"""


class LessonSetMismatchError(DomainError):
    """Batch reorder ids don't exactly match the module's lessons. → 400"""

    def __init__(self) -> None:
        super().__init__("lesson_ids must contain exactly the module's lesson ids")


class UnsupportedMediaTypeError(DomainError):
    """Uploaded file's content type is not an allowed image/video type. → 415"""

    def __init__(self, content_type: str) -> None:
        super().__init__(f"Unsupported media type: {content_type or 'unknown'}")


class PayloadTooLargeError(DomainError):
    """Uploaded file (or, with `what="Lesson content"`, a lesson save) exceeds
    the max size allowed. → 413"""

    def __init__(self, max_bytes: int, *, what: str = "File") -> None:
        super().__init__(f"{what} exceeds the maximum allowed size of {max_bytes} bytes")


class AiGenerationError(DomainError):
    """An on-demand model call produced nothing usable. Mapped to 502.

    Distinct from the drafting path, which absorbs a failure per lesson into a
    `failed` proposal row: an ad-hoc admin request has no queue to protect, so
    the failure has to reach the caller.
    """
