"""The playbook as a tagged document (#149). The model writes prose inside tags; code parses it
into the same PlaybookExtraction the tool call used to produce. Prose needs no escaping, so a
quote or a brace in the person's words can no longer break the playbook."""

from __future__ import annotations

import copy
import re

import pytest

from src.schemas.interview import PlaybookExtraction
from src.services.playbook_document import (
    PlaybookFormatError,
    output_template,
    parse_playbook,
    render_playbook_document,
)
from tests.fixtures.playbook import EXTRACTION


def _render(**shared_changes: object) -> str:
    data = copy.deepcopy(EXTRACTION)
    data["shared"].update(shared_changes)
    return render_playbook_document(data)


def test_a_rendered_playbook_parses_back_to_the_same_extraction() -> None:
    parsed = parse_playbook(render_playbook_document(EXTRACTION))

    assert parsed == EXTRACTION
    PlaybookExtraction.model_validate(parsed)


def test_rank_start_here_and_order_come_from_position_not_from_the_model() -> None:
    data = copy.deepcopy(EXTRACTION)
    for use_case in data["shared"]["use_cases"]:
        use_case.update(rank=7, start_here=False)
    for move in data["shared"]["next_moves"]:
        move["order"] = 9
    text = render_playbook_document(data)

    assert "<rank>" not in text and "<start_here>" not in text and "<order>" not in text
    shared = parse_playbook(text)["shared"]
    assert [u["rank"] for u in shared["use_cases"]] == [1, 2]
    assert [u["start_here"] for u in shared["use_cases"]] == [True, False]
    assert [m["order"] for m in shared["next_moves"]] == [1, 2]


def test_prose_is_taken_literally() -> None:
    awkward = (
        'U zei: "dit klopt niet" en {braces}, a < b, C:\\Users\\Jan, „Dutch” é.\n'
        "- a bullet line\n"
        "- another one"
    )

    shared = parse_playbook(_render(where_you_are_today=awkward))["shared"]

    assert shared["where_you_are_today"] == awkward


def test_an_empty_nullable_tag_is_null_and_no_items_is_an_empty_list() -> None:
    use_case = parse_playbook(render_playbook_document(EXTRACTION))["shared"]["use_cases"][1]

    assert use_case["assumption_to_check"] is None
    assert use_case["systems_involved"] == []


def test_text_outside_the_two_boxes_is_ignored() -> None:
    text = "Here is the playbook.\n" + render_playbook_document(EXTRACTION) + "\nDone."

    assert parse_playbook(text) == EXTRACTION


def test_more_than_five_use_cases_are_kept() -> None:
    six = [dict(EXTRACTION["shared"]["use_cases"][1]) for _ in range(6)]

    shared = parse_playbook(_render(use_cases=six))["shared"]

    assert len(shared["use_cases"]) == 6
    assert [u["rank"] for u in shared["use_cases"]] == [1, 2, 3, 4, 5, 6]


def _problems(text: str) -> list[str]:
    with pytest.raises(PlaybookFormatError) as exc_info:
        parse_playbook(text)
    return exc_info.value.problems


def test_a_missing_box_is_a_format_error() -> None:
    text = render_playbook_document(EXTRACTION)
    without_shared = text[: text.index("<shared>")]

    assert "shared: missing" in _problems(without_shared)


def test_a_missing_field_is_a_format_error() -> None:
    text = re.sub(r"<do_this_today>.*?</do_this_today>", "", _render(), flags=re.S)

    assert "shared.do_this_today: missing" in _problems(text)


def test_a_duplicated_field_is_a_format_error() -> None:
    text = _render().replace(
        "<where_you_are_today>", "<where_you_are_today>x</where_you_are_today><where_you_are_today>"
    )

    assert "shared.where_you_are_today: duplicated" in _problems(text)


def test_an_unclosed_tag_is_a_format_error() -> None:
    text = _render().replace("</do_this_today>", "")

    assert any("do_this_today" in p and "not closed" in p for p in _problems(text))


def test_a_bad_yes_no_or_number_is_a_format_error() -> None:
    text = render_playbook_document(EXTRACTION)
    bad_bool = text.replace(
        "<cross_functional>no</cross_functional>", "<cross_functional>maybe</cross_functional>", 1
    )
    bad_int = text.replace(
        "<linked_use_case>1</linked_use_case>", "<linked_use_case>one</linked_use_case>", 1
    )

    assert "shared.use_cases.0.cross_functional: not yes or no" in _problems(bad_bool)
    assert "shared.next_moves.0.linked_use_case: not a number" in _problems(bad_int)


def test_format_errors_never_contain_the_prose() -> None:
    text = _render(where_you_are_today="LEAKME " * 20).replace("</reframes>", "")

    problems = _problems(text)

    assert problems
    assert not any("LEAKME" in p for p in problems)


def test_the_template_names_every_field_the_model_must_write() -> None:
    template = output_template()

    for tag in ("internal", "shared", "item", "where_you_are_today", "use_cases", "tier", "basis"):
        assert f"<{tag}>" in template and f"</{tag}>" in template
    for field in PlaybookExtraction.model_json_schema()["$defs"]["UseCase"]["properties"]:
        if field in ("rank", "start_here"):
            assert f"<{field}>" not in template
        else:
            assert f"<{field}>" in template
    assert "Quick Win" in template and "yes or no" in template


def test_the_template_round_trips_once_filled_in() -> None:
    # Every tag in the template is one the parser reads: same field list, same order.
    rendered_tags = re.findall(r"<(\w+)>", render_playbook_document(EXTRACTION))
    template_tags = re.findall(r"<(\w+)>", output_template())

    assert set(template_tags) == set(rendered_tags)


def test_the_template_hints_contain_no_tags_the_model_could_copy_open() -> None:
    # A hint line copied into the answer must not open a tag the parser then sees unclosed.
    template = output_template()

    for tag in set(re.findall(r"<(\w+)>", template)):
        assert template.count(f"<{tag}>") == template.count(f"</{tag}>"), tag


def test_yes_no_and_numbers_tolerate_case_and_a_trailing_full_stop() -> None:
    text = render_playbook_document(EXTRACTION)
    text = text.replace(
        "<cross_functional>no</cross_functional>", "<cross_functional>No.</cross_functional>", 1
    )
    text = text.replace(
        "<linked_use_case>1</linked_use_case>", "<linked_use_case> 1. </linked_use_case>", 1
    )

    shared = parse_playbook(text)["shared"]

    assert shared["use_cases"][0]["cross_functional"] is False
    assert shared["next_moves"][0]["linked_use_case"] == 1


def test_a_fixed_value_in_other_capitals_becomes_the_exact_value() -> None:
    text = render_playbook_document(EXTRACTION)
    text = text.replace("<difficulty>Quick Win</difficulty>", "<difficulty>quick win</difficulty>")
    text = text.replace("<tier>RICH</tier>", "<tier>Rich</tier>")

    parsed = parse_playbook(text)

    assert parsed["shared"]["use_cases"][0]["difficulty"] == "Quick Win"
    assert parsed["internal"]["input_quality"]["tier"] == "RICH"


def test_an_unknown_fixed_value_is_left_for_validation() -> None:
    text = render_playbook_document(EXTRACTION).replace(
        "<difficulty>Quick Win</difficulty>", "<difficulty>Tiny Win</difficulty>"
    )

    assert parse_playbook(text)["shared"]["use_cases"][0]["difficulty"] == "Tiny Win"


def test_the_systems_list_asks_only_for_systems_the_person_named() -> None:
    # #149, v13: a bare example item made the model fill systems_involved with systems nobody
    # named. The hint says what belongs there, and that an empty list is fine.
    template = output_template()
    block = template[template.index("<systems_involved>") : template.index("</systems_involved>")]

    assert "a system the person named" in block
    assert "no items if they named none" in block


# Two rules that follow from what the format means (#149, v13/v14 slips).


def test_a_text_field_without_its_closing_tag_ends_at_the_next_tag() -> None:
    # A text field can't hold tags, so the next tag ends it.
    text = render_playbook_document(EXTRACTION)
    for tag in ("in_practice", "cross_functional", "action"):
        text = text.replace(f"</{tag}>", "", 1)

    assert parse_playbook(text) == EXTRACTION


def test_a_list_written_in_two_blocks_is_one_list() -> None:
    text = render_playbook_document(EXTRACTION)
    first_close = text.index("</item>", text.index("<next_moves>")) + len("</item>")
    split = text[:first_close] + "\n</next_moves>\n<next_moves>" + text[first_close:]

    shared = parse_playbook(split)["shared"]

    assert shared["next_moves"] == EXTRACTION["shared"]["next_moves"]
    assert [m["order"] for m in shared["next_moves"]] == [1, 2]


def test_a_duplicated_block_that_is_not_a_list_is_still_a_format_error() -> None:
    text = _render().replace(
        "<do_this_today>",
        "<do_this_today><action>x</action><time_required>y</time_required>"
        "<why_this_one>z</why_this_one></do_this_today><do_this_today>",
    )

    assert "shared.do_this_today: duplicated" in _problems(text)


def test_an_unclosed_block_is_still_a_format_error() -> None:
    # Only text fields close themselves; a block left open is a real gap.
    text = _render().replace("</next_moves>", "")

    assert any("next_moves" in p and "not closed" in p for p in _problems(text))
