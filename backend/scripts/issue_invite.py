"""Issue an invite/reset link for a user by email, bypassing the API.

Bootstrap tool: after migration every user has password_set=false and cannot
log in, but POST /api/admin/invites needs an admin bearer token — chicken and
egg. This mints the action token directly through TokenService (the exact
wiring the endpoint uses) and prints the frontend link.

Run from backend/ (uses DATABASE__*/AUTH__* from .env):
    uv run python scripts/issue_invite.py you@example.com
    uv run python scripts/issue_invite.py you@example.com --purpose reset --app-url https://hub.example.com
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.core.dependencies.settings import get_settings
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.services.token_service import TokenPurpose, TokenService


async def main(email: str, purpose: TokenPurpose, app_url: str) -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database.url.get_secret_value())
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            users = UserRepository(session)
            user = await users.get_by_email(email.strip().lower())
            if user is None:
                print(f"no user with email {email!r}", file=sys.stderr)
                return 1
            token_service = TokenService(
                users, AuthTokenRepository(session), AuthSessionRepository(session), settings.auth
            )
            raw = await token_service.issue_action_token(user, purpose)
        print(f"{purpose} link for {user.first_name} {user.last_name} <{user.email}>:")
        print(f"{app_url.rstrip('/')}/invite/{raw}")
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("--purpose", choices=["invite", "reset"], default="invite")
    parser.add_argument("--app-url", default="http://localhost:5173")
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(main(args.email, cast("TokenPurpose", args.purpose), args.app_url))
    )
