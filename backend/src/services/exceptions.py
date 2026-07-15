from __future__ import annotations

__all__ = [
    "AuthError",
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
    "LessonSetMismatchError",
    "NotFoundError",
    "PayloadTooLargeError",
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
    """Uploaded file exceeds the max size allowed for its media kind. → 413"""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"File exceeds the maximum allowed size of {max_bytes} bytes")
