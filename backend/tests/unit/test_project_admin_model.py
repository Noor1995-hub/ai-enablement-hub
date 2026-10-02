"""project_admins exists; the users.role CHECK no longer allows 'user+'."""

from __future__ import annotations

from src.db.base import Base
from src.db.models import ProjectAdmin, User


def test_project_admins_table_shape() -> None:
    table = Base.metadata.tables["project_admins"]
    assert [c.name for c in table.primary_key.columns] == ["user_id", "project_id"]
    fks = {fk.parent.name: (fk.column.table.name, fk.ondelete) for fk in table.foreign_keys}
    assert fks == {
        "user_id": ("users", "CASCADE"),
        "project_id": ("projects", "CASCADE"),
        "granted_by": ("users", "SET NULL"),
    }
    assert ProjectAdmin.__tablename__ == "project_admins"


def test_role_check_is_admin_or_user_only() -> None:
    checks = [c for c in User.__table__.constraints if getattr(c, "name", None) == "ck_users_role"]
    assert len(checks) == 1
    assert str(checks[0].sqltext) == "role IN ('admin', 'user')"
