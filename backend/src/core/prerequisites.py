"""Module prerequisite graph rules (spec 2026-10-05, B4). Pure."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

__all__ = ["would_create_cycle"]


def would_create_cycle(
    edges: Iterable[tuple[uuid.UUID, uuid.UUID]],
    module_id: uuid.UUID,
    prerequisite_ids: Iterable[uuid.UUID],
) -> bool:
    """True when giving `module_id` exactly `prerequisite_ids` would make it
    depend on itself, directly or through a chain. `edges` are the graph's
    (module, prerequisite) pairs today; the module's own edges are replaced.

    A cycle locks every module on it forever (each waits for the next)."""
    requires: dict[uuid.UUID, set[uuid.UUID]] = {}
    for module, prerequisite in edges:
        if module != module_id:
            requires.setdefault(module, set()).add(prerequisite)
    stack = list(prerequisite_ids)
    seen: set[uuid.UUID] = set()
    while stack:
        current = stack.pop()
        if current == module_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(requires.get(current, ()))
    return False
