from __future__ import annotations

import uuid

from src.core.prerequisites import would_create_cycle

A, B, C, D = (uuid.uuid4() for _ in range(4))


def test_self_is_a_cycle() -> None:
    assert would_create_cycle([], A, [A])


def test_two_step_cycle() -> None:
    # B requires A today; now A would require B.
    assert would_create_cycle([(B, A)], A, [B])


def test_three_step_cycle() -> None:
    # C requires B, B requires A; A would require C.
    assert would_create_cycle([(C, B), (B, A)], A, [C])


def test_a_chain_without_a_loop_is_fine() -> None:
    # C requires B; A would require C. Nothing leads back to A.
    assert not would_create_cycle([(C, B)], A, [C])


def test_the_modules_own_old_edges_are_replaced() -> None:
    # A requires B today (A, B); the new set drops B and adds C. B → A does
    # not exist, so no cycle, and the old A → B edge must not count.
    assert not would_create_cycle([(A, B), (C, D)], A, [C])


def test_an_empty_set_never_cycles() -> None:
    assert not would_create_cycle([(B, A), (A, B)], A, [])
