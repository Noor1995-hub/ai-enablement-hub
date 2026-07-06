from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

__all__ = [
    "AuthMethodsResponse",
    "EntraRedeemRequest",
    "InviteInfoResponse",
    "LoginRequest",
    "LogoutRequest",
    "RefreshRequest",
    "SetPasswordRequest",
    "TokenPairResponse",
]


class AuthMethodsResponse(BaseModel):
    password: bool
    entra: bool


class EntraRedeemRequest(BaseModel):
    code: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SetPasswordRequest(BaseModel):
    token: str
    # ≥8 mirrors the old SetPassword page; ≤72 because bcrypt ignores bytes past 72.
    password: str = Field(min_length=8, max_length=72)


class InviteInfoResponse(BaseModel):
    purpose: Literal["invite", "reset"]
    email: str
    first_name: str
