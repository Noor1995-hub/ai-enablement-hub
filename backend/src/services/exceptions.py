from __future__ import annotations

__all__ = [
    "AuthError",
    "ConflictError",
    "DomainError",
    "DuplicateCompanyNameError",
    "EmailAlreadyRegisteredError",
    "InvalidCredentialsError",
    "InvalidRequestError",
    "InvalidSessionError",
    "LessonSetMismatchError",
    "NotFoundError",
    "SurveyAlreadyCompleteError",
    "SurveyNotInProgressError",
    "TokenExpiredError",
    "TokenNotFoundError",
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


class DomainError(Exception):
    """Base for non-auth use-case failures; carries the client-facing message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """A referenced entity does not exist. → 404"""

    def __init__(self, entity: str) -> None:
        super().__init__(f"{entity} not found")


class ConflictError(DomainError):
    """The request conflicts with current state. → 409"""


class EmailAlreadyRegisteredError(ConflictError):
    def __init__(self) -> None:
        super().__init__("A user with this email already exists")


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


class LessonSetMismatchError(DomainError):
    """Batch reorder ids don't exactly match the module's lessons. → 400"""

    def __init__(self) -> None:
        super().__init__("lesson_ids must contain exactly the module's lesson ids")
