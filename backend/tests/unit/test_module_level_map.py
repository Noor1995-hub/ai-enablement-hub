"""`module_level_map` — the module_id -> required_level map that `advance_level`
walks. Copy-defined in three services before it lived here (review 9.4b)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from src.core.constants import advance_level, module_level_map

GI_TRACK, GII_TRACK = uuid.uuid4(), uuid.uuid4()
GI_MOD, GII_MOD, ORPHAN_MOD = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

_TRACKS = [
    SimpleNamespace(id=GI_TRACK, required_level="explore"),
    SimpleNamespace(id=GII_TRACK, required_level="practitioner"),
]
_MODULES = [
    SimpleNamespace(id=GI_MOD, track_id=GI_TRACK),
    SimpleNamespace(id=GII_MOD, track_id=GII_TRACK),
]


def test_maps_each_module_to_its_tracks_required_level() -> None:
    assert module_level_map(_TRACKS, _MODULES) == {
        GI_MOD: "explore",
        GII_MOD: "practitioner",
    }


def test_a_module_whose_track_is_absent_is_skipped() -> None:
    """All three copies guarded with `if module.track_id in track_level` rather
    than raising — a module whose track is missing from the list must not blow
    up the admin directory or the dashboard."""
    modules = [*_MODULES, SimpleNamespace(id=ORPHAN_MOD, track_id=uuid.uuid4())]

    result = module_level_map(_TRACKS, modules)

    assert ORPHAN_MOD not in result
    assert len(result) == 2


def test_empty_inputs_give_an_empty_map() -> None:
    assert module_level_map([], []) == {}
    assert module_level_map(_TRACKS, []) == {}


def test_the_result_feeds_advance_level_unchanged() -> None:
    """End-to-end on the pure pair: one General I module fully done promotes
    explore -> practitioner, which is the behaviour all three call sites want."""
    counts = {GI_MOD: (3, 3), GII_MOD: (2, 0)}

    assert advance_level("explore", module_level_map(_TRACKS, _MODULES), counts) == "practitioner"
