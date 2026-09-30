from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.base import AbstractUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["UnitOfWork"]


class UnitOfWork(AbstractUnitOfWork):
    """The commit boundary for a use case that writes more than once.

    Repositories still own the session; this is the seam that lets a SERVICE
    decide where the transaction ends without reaching into the session itself.
    It lives in the repository layer, so a service depending on it is a downward
    call — the "services never call services" rule is untouched.

    Only the flows that need atomicity use it (assessment completion, proposal
    approval). Every other repository method keeps committing internally.

    There is deliberately no `rollback()`: no service needs one. A use case
    that raises before `commit()` leaves its staged writes uncommitted, and the
    request-scoped session discards them when it closes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()
