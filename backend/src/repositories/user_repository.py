from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from src.db.models import Company, Project, User
from src.repositories.base import AbstractUserRepository

__all__ = ["UserRepository"]


class UserRepository(AbstractUserRepository):
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def emails_in(self, emails: list[str]) -> set[str]:
        if not emails:
            return set()
        result = await self._session.execute(select(User.email).where(User.email.in_(emails)))
        return set(result.scalars().all())

    async def get_by_external_id(self, external_id: str) -> User | None:
        result = await self._session.execute(select(User).where(User.external_id == external_id))
        return result.scalar_one_or_none()

    async def link_external_id(self, user: User, external_id: str) -> None:
        user.external_id = external_id
        await self._session.commit()
        await self._session.refresh(user)

    async def set_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        user.password_set = True
        await self._session.commit()
        await self._session.refresh(user)

    async def list_with_org_names(
        self, project_id: uuid.UUID | None = None, q: str | None = None
    ) -> list[tuple[User, str | None, str | None]]:
        stmt = (
            select(User, Company.name, Project.name)
            .outerjoin(Company, Company.id == User.company_id)
            .outerjoin(Project, Project.id == User.project_id)
            .order_by(User.created_at.desc())
        )
        if project_id is not None:
            stmt = stmt.where(User.project_id == project_id)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        result = await self._session.execute(stmt)
        return [(user, company, project) for user, company, project in result.all()]

    async def get_with_org_names(
        self, user_id: uuid.UUID
    ) -> tuple[User, str | None, str | None] | None:
        stmt = (
            select(User, Company.name, Project.name)
            .outerjoin(Company, Company.id == User.company_id)
            .outerjoin(Project, Project.id == User.project_id)
            .where(User.id == user_id)
        )
        row = (await self._session.execute(stmt)).first()
        return (row[0], row[1], row[2]) if row is not None else None

    async def list_for_learning(self) -> list[tuple[User, str | None, str | None]]:
        # Company resolved through the user's project (legacy handleGetLearning shape).
        project_company = aliased(Company)
        stmt = (
            select(User, Project.name, project_company.name)
            .outerjoin(Project, Project.id == User.project_id)
            .outerjoin(project_company, project_company.id == Project.company_id)
            .order_by(User.first_name)
        )
        result = await self._session.execute(stmt)
        return [(user, project, company) for user, project, company in result.all()]

    async def create(
        self,
        *,
        email: str,
        first_name: str,
        last_name: str,
        company_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> User:
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_id=company_id,
            project_id=project_id,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def update_role(self, user: User, role: str) -> None:
        user.role = role
        await self._session.commit()

    async def set_maturity_override(self, user: User, level: str | None) -> None:
        user.maturity_override = level
        await self._session.commit()

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.commit()

    async def ids_for_project(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(select(User.id).where(User.project_id == project_id))
        return list(result.scalars().all())

    async def count_by_ids(self, user_ids: list[uuid.UUID]) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(User).where(User.id.in_(user_ids))
        )
        return int(result.scalar_one())

    async def count_power_admins(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(User).where(User.role == "admin")
        )
        return int(result.scalar_one())

    async def project_ids_of(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID | None]:
        if not user_ids:
            return {}
        result = await self._session.execute(
            select(User.id, User.project_id).where(User.id.in_(user_ids))
        )
        return dict(result.tuples().all())
