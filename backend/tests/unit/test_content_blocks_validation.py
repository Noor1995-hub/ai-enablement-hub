import copy

from src.services.content_blocks_validation import (
    check_house_style,
    check_link_schemes,
    check_media_immutable,
    media_locators,
    normalise_nested_ids,
    validate_content_blocks,
)


def test_valid_blocks_pass() -> None:
    blocks = [
        {"id": "b1", "type": "heading", "level": 2, "text": "Prompting basics"},
        {"id": "b2", "type": "paragraph", "text": "Be specific."},
        {
            "id": "b3",
            "type": "quiz",
            "questions": [
                {
                    "id": "q1",
                    "q": "What helps most?",
                    "options": ["vagueness", "specificity"],
                    "correct": 1,
                    "explanation": "Specific prompts win.",
                }
            ],
        },
    ]
    assert validate_content_blocks(blocks) == []


def test_not_a_list_is_rejected() -> None:
    assert validate_content_blocks({"id": "b1", "type": "paragraph"}) == [
        "content_blocks must be a list"
    ]


def test_unknown_type_is_rejected() -> None:
    errors = validate_content_blocks([{"id": "b1", "type": "banner", "text": "x"}])
    assert any("unknown type" in e for e in errors)


def test_missing_required_field_is_rejected() -> None:
    errors = validate_content_blocks([{"id": "b1", "type": "paragraph"}])
    assert any("text" in e for e in errors)


def test_missing_id_is_rejected() -> None:
    errors = validate_content_blocks([{"type": "paragraph", "text": "hi"}])
    assert any("id" in e for e in errors)


def test_quiz_correct_out_of_range_is_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "quiz",
                "questions": [
                    {
                        "id": "q1",
                        "q": "Q?",
                        "options": ["a", "b"],
                        "correct": 5,
                        "explanation": "e",
                    }
                ],
            }
        ]
    )
    assert any("correct" in e for e in errors)


def test_image_missing_blob_path_is_rejected() -> None:
    errors = validate_content_blocks([{"id": "b1", "type": "image", "alt": "a chart"}])
    assert any("blob_path" in e for e in errors)


def test_interactive_bad_mode_is_rejected() -> None:
    errors = validate_content_blocks(
        [{"id": "b1", "type": "interactive", "mode": "wat", "prompt": "p"}]
    )
    assert any("mode" in e for e in errors)


def test_card_with_no_id_is_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "card_group",
                "cards": [{"title": "T", "body": "B"}],
            }
        ]
    )
    assert any("cards[0]" in e and "id" in e for e in errors)


def test_quiz_question_with_no_id_is_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "quiz",
                "questions": [
                    {
                        "q": "Q?",
                        "options": ["a", "b"],
                        "correct": 0,
                        "explanation": "e",
                    }
                ],
            }
        ]
    )
    assert any("questions[0]" in e and "id" in e for e in errors)


def test_try_it_yourself_step_with_no_id_is_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "try_it_yourself",
                "task": "Do it",
                "material": "Your AI tool",
                "whatToNotice": "n",
                "steps": [{"label": "Step 1", "text": "Do the thing."}],
            }
        ]
    )
    assert any("steps[0]" in e and "id" in e for e in errors)


def test_sort_item_with_dangling_bucket_id_is_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "interactive",
                "mode": "sort",
                "prompt": "p",
                "buckets": [{"id": "bucket1", "label": "Good"}],
                "items": [{"id": "i1", "text": "x", "bucketId": "no-such-bucket", "reason": "r"}],
            }
        ]
    )
    assert any("bucketId" in e for e in errors)


def test_predict_correct_option_id_not_in_options_is_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "interactive",
                "mode": "predict",
                "prompt": "p",
                "options": [{"id": "o1", "label": "A", "reason": "r"}],
                "correctOptionId": "not-an-option",
            }
        ]
    )
    assert any("correctOptionId" in e for e in errors)


def test_fully_populated_nested_blocks_pass() -> None:
    blocks = [
        {
            "id": "b1",
            "type": "card_group",
            "cards": [{"id": "c1", "title": "T", "body": "B"}],
        },
        {
            "id": "b2",
            "type": "quiz",
            "questions": [
                {
                    "id": "q1",
                    "q": "Q?",
                    "options": ["a", "b"],
                    "correct": 1,
                    "explanation": "e",
                }
            ],
        },
        {
            "id": "b3",
            "type": "try_it_yourself",
            "task": "Do it",
            "material": "Your AI tool",
            "whatToNotice": "n",
            "steps": [{"id": "s1", "label": "Step 1", "text": "Do the thing."}],
        },
        {
            "id": "b4",
            "type": "interactive",
            "mode": "sort",
            "prompt": "p",
            "buckets": [{"id": "bucket1", "label": "Good"}],
            "items": [{"id": "i1", "text": "x", "bucketId": "bucket1", "reason": "r"}],
        },
        {
            "id": "b5",
            "type": "interactive",
            "mode": "predict",
            "prompt": "p",
            "options": [{"id": "o1", "label": "A", "reason": "r"}],
            "correctOptionId": "o1",
        },
        {
            "id": "b6",
            "type": "interactive",
            "mode": "spot_the_flaw",
            "prompt": "p",
            "example": "e",
            "candidates": [
                {"id": "f1", "text": "x", "isFlaw": True, "reason": "r"},
                {"id": "f2", "text": "y", "isFlaw": False, "reason": "r"},
            ],
        },
    ]
    assert validate_content_blocks(blocks) == []


def test_duplicate_top_level_block_ids_are_rejected() -> None:
    # Two blocks under one id collide on key={block.id} in the learner
    # renderer, and a duplicated media block would even satisfy
    # check_media_immutable (both copies match the base entry for that id).
    errors = validate_content_blocks(
        [
            {"id": "b1", "type": "paragraph", "text": "First."},
            {"id": "b1", "type": "paragraph", "text": "Second."},
        ]
    )
    assert errors == ["block[1] duplicate id 'b1'"]


def test_duplicate_nested_item_ids_are_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "card_group",
                "cards": [
                    {"id": "c1", "title": "T", "body": "B"},
                    {"id": "c1", "title": "T2", "body": "B2"},
                ],
            }
        ]
    )
    assert errors == ["block[0].cards[1] duplicate id 'c1'"]


def test_the_same_nested_id_in_two_different_blocks_is_allowed() -> None:
    # Nested ids only have to be unique within their own list — two card_groups
    # that each number their cards from c1 are fine, and real lessons do this.
    assert (
        validate_content_blocks(
            [
                {
                    "id": "b1",
                    "type": "card_group",
                    "cards": [{"id": "c1", "title": "T", "body": "B"}],
                },
                {
                    "id": "b2",
                    "type": "card_group",
                    "cards": [{"id": "c1", "title": "U", "body": "C"}],
                },
            ]
        )
        == []
    )


_CARD_GROUP_NO_IDS = {
    "id": "b3",
    "type": "card_group",
    "cards": [{"title": "First", "body": "B1"}, {"title": "Second", "body": "B2"}],
}
_QUIZ_NO_IDS = {
    "id": "b4",
    "type": "quiz",
    "questions": [
        {"q": "Q?", "options": ["a", "b"], "correct": 1, "explanation": "e"},
        {"q": "R?", "options": ["c", "d"], "correct": 0, "explanation": "e"},
    ],
}
_TRY_IT_NO_IDS = {
    "id": "b5",
    "type": "try_it_yourself",
    "task": "Do it",
    "material": "Your AI tool",
    "whatToNotice": "n",
    "steps": [{"label": "Step 1", "text": "Do the thing."}],
}
_SORT_NO_IDS = {
    "id": "b6",
    "type": "interactive",
    "mode": "sort",
    "prompt": "p",
    "buckets": [{"label": "Good"}],
    "items": [{"text": "x", "bucketId": "b6-buckets0", "reason": "r"}],
}


def test_normalise_mints_ids_for_id_less_cards() -> None:
    result = normalise_nested_ids([_CARD_GROUP_NO_IDS])

    assert [card["id"] for card in result[0]["cards"]] == ["b3-cards0", "b3-cards1"]
    assert validate_content_blocks(result) == []


def test_normalise_mints_ids_for_id_less_quiz_questions() -> None:
    result = normalise_nested_ids([_QUIZ_NO_IDS])

    assert [q["id"] for q in result[0]["questions"]] == ["b4-questions0", "b4-questions1"]
    assert validate_content_blocks(result) == []


def test_normalise_mints_ids_for_steps_buckets_and_sort_items() -> None:
    result = normalise_nested_ids([_TRY_IT_NO_IDS, _SORT_NO_IDS])

    assert [step["id"] for step in result[0]["steps"]] == ["b5-steps0"]
    assert [bucket["id"] for bucket in result[1]["buckets"]] == ["b6-buckets0"]
    assert [item["id"] for item in result[1]["items"]] == ["b6-items0"]
    # The minted bucket id is the one the sort item already points at, so the
    # bucketId cross-reference resolves.
    assert validate_content_blocks(result) == []


def test_normalise_leaves_existing_ids_exactly_as_they_were() -> None:
    blocks = [
        {"id": "b1", "type": "card_group", "cards": [{"id": "keep-me", "title": "T", "body": "B"}]},
    ]

    assert normalise_nested_ids(blocks) == blocks


def test_normalise_never_mutates_its_input() -> None:
    blocks = [copy.deepcopy(_CARD_GROUP_NO_IDS)]
    before = copy.deepcopy(blocks)

    result = normalise_nested_ids(blocks)

    assert blocks == before
    assert all("id" not in card for card in blocks[0]["cards"])
    assert result is not blocks


def test_normalise_keeps_quiz_options_as_plain_strings() -> None:
    result = normalise_nested_ids([_QUIZ_NO_IDS])

    assert result[0]["questions"][0]["options"] == ["a", "b"]


def test_normalise_passes_through_a_block_with_no_top_level_id() -> None:
    # Nothing stable to derive nested ids from; inventing a parent id here
    # would hide the missing block id that the validator must report.
    orphan = {"type": "card_group", "cards": [{"title": "T", "body": "B"}]}

    result = normalise_nested_ids([orphan])

    assert result == [orphan]
    assert any("missing non-empty string 'id'" in e for e in validate_content_blocks(result))


def test_normalise_is_idempotent() -> None:
    once = normalise_nested_ids([_CARD_GROUP_NO_IDS, _QUIZ_NO_IDS, _SORT_NO_IDS])

    assert normalise_nested_ids(once) == once


def test_normalise_returns_an_empty_list_for_non_list_input() -> None:
    assert normalise_nested_ids({"id": "b1", "type": "paragraph"}) == []
    assert normalise_nested_ids(None) == []


def test_normalise_passes_non_dict_entries_through() -> None:
    assert normalise_nested_ids(["not a block", 7]) == ["not a block", 7]


def test_normalise_never_mints_an_id_that_collides_within_the_list() -> None:
    # A model could hand back one card already carrying the id the scheme would
    # derive for another. Minting it anyway would produce a duplicate that the
    # uniqueness check then rejects, so the collision is stepped over instead.
    blocks = [
        {
            "id": "b1",
            "type": "card_group",
            "cards": [{"title": "T", "body": "B"}, {"id": "b1-cards0", "title": "U", "body": "C"}],
        }
    ]

    result = normalise_nested_ids(blocks)

    assert [card["id"] for card in result[0]["cards"]] == ["b1-cards0-1", "b1-cards0"]
    assert validate_content_blocks(result) == []


_IMAGE = {"id": "m1", "type": "image", "blob_path": "images/a.png", "alt": "a chart"}
_EMBED = {"id": "m2", "type": "video", "source": "embed", "url": "https://x.test/v"}
_BLOB_VIDEO = {"id": "m3", "type": "video", "source": "blob", "blob_path": "videos/b.mp4"}
_TEXT = {"id": "t1", "type": "paragraph", "text": "Hello."}


def test_media_locators_extracts_every_persisted_locator() -> None:
    assert media_locators([_TEXT, _IMAGE, _EMBED, _BLOB_VIDEO]) == [
        ("image", "images/a.png"),
        ("video:embed", "https://x.test/v"),
        ("video:blob", "videos/b.mp4"),
    ]


def test_media_locators_ignores_the_ephemeral_url() -> None:
    # A read-time SAS url must never be mistaken for a locator.
    stamped = {**_IMAGE, "url": "https://blob.test/images/a.png?sig=abc"}
    assert media_locators([stamped]) == [("image", "images/a.png")]


def test_unchanged_media_passes() -> None:
    assert check_media_immutable([_TEXT, _IMAGE], [_IMAGE, _TEXT]) == []


def test_dropping_a_media_block_is_allowed() -> None:
    # The agent may restructure a lesson and leave an image out; the admin sees
    # that in the diff. Only ADDING or ALTERING a locator is forbidden.
    assert check_media_immutable([_IMAGE, _TEXT], [_TEXT]) == []


def test_inventing_an_image_is_rejected() -> None:
    errors = check_media_immutable([_TEXT], [_TEXT, _IMAGE])
    assert any("images/a.png" in e for e in errors)


def test_altering_a_blob_path_is_rejected() -> None:
    moved = {**_IMAGE, "blob_path": "images/somewhere-else.png"}
    errors = check_media_immutable([_IMAGE], [moved])
    assert any("somewhere-else" in e for e in errors)


def test_duplicating_an_existing_image_is_rejected() -> None:
    errors = check_media_immutable([_IMAGE], [_IMAGE, {**_IMAGE, "id": "m1b"}])
    assert any("images/a.png" in e for e in errors)


def test_changing_alt_text_is_allowed() -> None:
    # Only the locator is immutable — captions/alt text are editable content.
    assert check_media_immutable([_IMAGE], [{**_IMAGE, "alt": "a clearer caption"}]) == []


def test_swapping_two_image_locators_is_rejected() -> None:
    # A bag/Counter comparison sees the same two paths present either way and
    # would miss this; matching by block id catches the swap.
    img_a = {"id": "m1", "type": "image", "blob_path": "images/a.png", "alt": "a"}
    img_b = {"id": "m2", "type": "image", "blob_path": "images/b.png", "alt": "b"}
    swapped_a = {**img_a, "blob_path": "images/b.png"}
    swapped_b = {**img_b, "blob_path": "images/a.png"}
    errors = check_media_immutable([img_a, img_b], [swapped_a, swapped_b])
    assert any("images/a.png" in e or "images/b.png" in e for e in errors)


def test_flipping_embed_to_blob_on_the_same_id_is_rejected() -> None:
    # Same locator string, but the renderer would now treat it as a storage
    # path instead of an embed URL -- the kind must be part of the identity.
    flipped = {"id": "m2", "type": "video", "source": "blob", "blob_path": "https://x.test/v"}
    errors = check_media_immutable([_EMBED], [flipped])
    assert any("https://x.test/v" in e for e in errors)


def test_media_block_with_no_id_is_rejected() -> None:
    no_id = {"type": "image", "blob_path": "images/a.png", "alt": "a chart"}
    errors = check_media_immutable([], [no_id])
    assert any("no id" in e for e in errors)


def test_proposed_not_a_list_is_rejected() -> None:
    assert check_media_immutable([], "not a list") != []


# --- check_house_style: only judges blocks the agent actually WROTE (new, or
# changed from their base counterpart by id). A block copied through
# unchanged is exempt from every rule below, even if it would otherwise
# violate one — see check_house_style's docstring for why that scoping is
# load-bearing, not an optimisation. ---

_CHECK_UNDERSTANDING_TEXT = "Check your understanding"
_HEADING_CHECK = {"id": "h1", "type": "heading", "level": 2, "text": _CHECK_UNDERSTANDING_TEXT}


def _quiz_one_question(options: list[str], correct: int) -> dict:
    return {
        "id": "b1",
        "type": "quiz",
        "questions": [
            {
                "id": "q1",
                "q": "Which is best?",
                "options": options,
                "correct": correct,
                "explanation": "Because.",
            }
        ],
    }


def _quiz_two_questions(corrects: tuple[int, int]) -> dict:
    # Every option is the same length (4 chars) so rule 4 (unique longest
    # option) never fires here — these fixtures are for rules 5 and 6 only.
    return {
        "id": "b1",
        "type": "quiz",
        "questions": [
            {
                "id": "q1",
                "q": "First?",
                "options": ["aaaa", "bbbb"],
                "correct": corrects[0],
                "explanation": "Because.",
            },
            {
                "id": "q2",
                "q": "Second?",
                "options": ["cccc", "dddd"],
                "correct": corrects[1],
                "explanation": "Because.",
            },
        ],
    }


# rule 1: no em dash, en dash, or ellipsis in any text field


def test_house_style_forbidden_dash_in_a_changed_block_is_caught() -> None:
    base = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
    proposed = [{"id": "b1", "type": "paragraph", "text": "New text — with an em dash."}]
    errors = check_house_style(base, proposed)
    assert any("contains a forbidden dash or ellipsis" in e for e in errors)


def test_house_style_forbidden_dash_in_an_unchanged_block_is_not_caught() -> None:
    # The real corpus predates this rule; a faithful copy must not be judged.
    legacy = {"id": "b1", "type": "paragraph", "text": "Legacy text — with an em dash."}
    assert check_house_style([legacy], [legacy]) == []


# rule 2: at most two bold spans in one text field


def test_house_style_too_many_bold_spans_in_a_changed_block_is_caught() -> None:
    base = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
    proposed = [
        {
            "id": "b1",
            "type": "paragraph",
            "text": "This is **great** and **wonderful** and also **amazing**.",
        }
    ]
    errors = check_house_style(base, proposed)
    assert any("more than two bold spans" in e for e in errors)


def test_house_style_too_many_bold_spans_in_an_unchanged_block_is_not_caught() -> None:
    legacy = {
        "id": "b1",
        "type": "paragraph",
        "text": "This is **great** and **wonderful** and also **amazing**.",
    }
    assert check_house_style([legacy], [legacy]) == []


def test_house_style_bullet_lead_in_bold_spans_are_exempt_from_the_cap() -> None:
    base = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
    proposed = [
        {
            "id": "b1",
            "type": "paragraph",
            "text": (
                "Pick one:\n"
                "- **Speed.** Get an answer back fast.\n"
                "- **Depth.** Get a thorough answer.\n"
                "- **Cost.** Spend less per call."
            ),
        }
    ]
    assert check_house_style(base, proposed) == []


def test_house_style_one_ordinary_bold_span_alongside_bullet_lead_ins_is_not_capped() -> None:
    # Exempt the bullet lead-ins FIRST, then apply the cap of two to what is
    # left. One real bold span plus three lead-ins must not be rejected --
    # house_style.md itself models exactly this combination.
    base = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
    proposed = [
        {
            "id": "b1",
            "type": "paragraph",
            "text": (
                "Here is the **one key idea** of this section.\n"
                "- **Speed.** Get an answer back fast.\n"
                "- **Depth.** Get a thorough answer.\n"
                "- **Cost.** Spend less per call."
            ),
        }
    ]
    assert check_house_style(base, proposed) == []


# rule 3: "Artifact"/"Artifacts" is forbidden; the house term is "Artefact"/"Artefacts"


def test_house_style_artifact_word_in_a_changed_block_is_caught() -> None:
    base = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
    proposed = [{"id": "b1", "type": "paragraph", "text": "This is an Artifact of the run."}]
    errors = check_house_style(base, proposed)
    assert any("Artifact" in e for e in errors)


def test_house_style_artifact_word_in_an_unchanged_block_is_not_caught() -> None:
    legacy = {"id": "b1", "type": "paragraph", "text": "This is an Artifact of the run."}
    assert check_house_style([legacy], [legacy]) == []


def test_house_style_artifact_plural_in_a_changed_block_is_caught() -> None:
    base = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
    proposed = [{"id": "b1", "type": "paragraph", "text": "These are the Artifacts of the run."}]
    errors = check_house_style(base, proposed)
    assert any("Artifact" in e for e in errors)


# rule 4: the correct answer is never the unique longest option


def test_house_style_unique_longest_correct_option_in_a_changed_quiz_is_caught() -> None:
    quiz = _quiz_one_question(["short", "a much longer option than the rest"], 1)
    errors = check_house_style([], [_HEADING_CHECK, quiz])
    assert any("unique longest option" in e for e in errors)


def test_house_style_unique_longest_correct_option_in_an_unchanged_quiz_is_not_caught() -> None:
    quiz = _quiz_one_question(["short", "a much longer option than the rest"], 1)
    # No preceding heading either -- still exempt, because the block itself is
    # unchanged from its base counterpart.
    assert check_house_style([quiz], [quiz]) == []


# rule 5: the correct index must vary across a quiz's questions


def test_house_style_identical_correct_index_in_a_changed_quiz_is_caught() -> None:
    quiz = _quiz_two_questions((0, 0))
    errors = check_house_style([], [_HEADING_CHECK, quiz])
    assert any("identical across every question" in e for e in errors)


def test_house_style_identical_correct_index_in_an_unchanged_quiz_is_not_caught() -> None:
    quiz = _quiz_two_questions((0, 0))
    assert check_house_style([quiz], [quiz]) == []


# rule 6: a quiz must be immediately preceded by a "Check your understanding" heading


def test_house_style_quiz_without_a_preceding_heading_is_caught_when_changed() -> None:
    quiz = _quiz_two_questions((0, 1))
    paragraph = {"id": "p1", "type": "paragraph", "text": "Some text."}
    errors = check_house_style([], [paragraph, quiz])
    assert any("must be immediately preceded" in e for e in errors)


def test_house_style_quiz_without_a_preceding_heading_is_not_caught_when_unchanged() -> None:
    # A genuinely untouched legacy pairing: neither the quiz nor its neighbour
    # changed, and the quiz never had the required heading before it. The
    # rule 6 invariant belongs to the (heading, quiz) pair, so it only fires
    # when something in that pair moved -- not on a pairing that was already
    # like this and stays like this.
    paragraph = {"id": "p1", "type": "paragraph", "text": "Some text."}
    quiz = _quiz_two_questions((0, 1))
    legacy = [paragraph, quiz]
    assert check_house_style(legacy, legacy) == []


def test_house_style_editing_the_heading_before_an_unchanged_quiz_is_caught() -> None:
    # The quiz's own dict never changes -- only its neighbour does. Rule 6 is
    # a pair invariant, so this must still be caught.
    heading = {"id": "h1", "type": "heading", "level": 2, "text": _CHECK_UNDERSTANDING_TEXT}
    quiz = _quiz_two_questions((0, 1))
    base = [heading, quiz]
    edited_heading = {**heading, "text": "Let's see what stuck"}
    errors = check_house_style(base, [edited_heading, quiz])
    assert any("must be immediately preceded" in e for e in errors)


def test_house_style_deleting_the_heading_before_an_unchanged_quiz_is_caught() -> None:
    # The quiz's own dict never changes and it has no immediate predecessor
    # left at all in `proposed` -- its predecessor identity goes from "h1" in
    # base to "no predecessor" in proposed, which counts as an adjacency
    # change even though "h1" was never re-inserted anywhere else either.
    heading = {"id": "h1", "type": "heading", "level": 2, "text": _CHECK_UNDERSTANDING_TEXT}
    quiz = _quiz_two_questions((0, 1))
    base = [heading, quiz]
    errors = check_house_style(base, [quiz])
    assert any("must be immediately preceded" in e for e in errors)


def test_house_style_reordering_an_unchanged_quiz_away_from_its_heading_is_caught() -> None:
    # Fix round 2: a pure reorder, zero content edits on either block. Neither
    # the quiz's own dict nor the heading's own dict changed, and "h1" still
    # exists SOMEWHERE in proposed -- but it is no longer adjacent to the
    # quiz, which is exactly what adjacency (not mere existence) must catch.
    heading = {"id": "h1", "type": "heading", "level": 2, "text": _CHECK_UNDERSTANDING_TEXT}
    quiz = _quiz_two_questions((0, 1))
    base = [heading, quiz]
    errors = check_house_style(base, [quiz, heading])
    assert any("must be immediately preceded" in e for e in errors)


def test_house_style_moving_an_unchanged_quiz_to_the_front_is_caught() -> None:
    # The quiz moves to index 0 (no predecessor at all) while its original
    # heading is left later in the array, unchanged and still present -- a
    # "no predecessor" identity is distinct from any real predecessor id, so
    # this is caught rather than treated as vacuously unchanged.
    heading = {"id": "h1", "type": "heading", "level": 2, "text": _CHECK_UNDERSTANDING_TEXT}
    quiz = _quiz_two_questions((0, 1))
    trailer = {"id": "t1", "type": "paragraph", "text": "Some other text."}
    base = [heading, quiz, trailer]
    errors = check_house_style(base, [quiz, heading, trailer])
    assert any("must be immediately preceded" in e for e in errors)


def test_house_style_an_index_shift_with_the_same_unchanged_predecessor_is_not_caught() -> None:
    # A block inserted EARLIER in the array shifts the quiz's own index, but
    # its immediate predecessor is still the same unchanged heading right
    # before it -- an index shift is not an adjacency change, and this must
    # NOT be flagged.
    heading = {"id": "h1", "type": "heading", "level": 2, "text": _CHECK_UNDERSTANDING_TEXT}
    quiz = _quiz_two_questions((0, 1))
    base = [heading, quiz]
    new_intro = {"id": "i1", "type": "paragraph", "text": "A new introduction."}
    assert check_house_style(base, [new_intro, heading, quiz]) == []


# positive tests: fully house-style-compliant changed content passes clean


def test_house_style_compliant_changed_text_block_passes() -> None:
    base = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
    proposed = [
        {
            "id": "b1",
            "type": "paragraph",
            "text": "New text with one **bolded** term and no forbidden words.",
        }
    ]
    assert check_house_style(base, proposed) == []


def test_house_style_compliant_changed_quiz_passes() -> None:
    quiz = _quiz_two_questions((0, 1))
    assert check_house_style([], [_HEADING_CHECK, quiz]) == []


# --- check_link_schemes: reject markdown links / embed-video urls carrying a
# scheme outside the http/https/mailto allowlist. ---


def test_javascript_link_scheme_is_rejected() -> None:
    errors = check_link_schemes(
        [{"id": "b1", "type": "paragraph", "text": "Try [this](javascript:alert(1)) now."}]
    )
    assert len(errors) == 1
    assert "javascript" in errors[0]


def test_data_uri_link_scheme_is_rejected() -> None:
    errors = check_link_schemes(
        [{"id": "b1", "type": "callout", "text": "[open](data:text/html;base64,PHNjcmlwdD4=)"}]
    )
    assert any("data" in e for e in errors)


def test_https_and_mailto_and_relative_links_pass() -> None:
    assert (
        check_link_schemes(
            [
                {"id": "b1", "type": "paragraph", "text": "[docs](https://example.com/a)"},
                {"id": "b2", "type": "paragraph", "text": "[mail](mailto:x@example.com)"},
                {"id": "b3", "type": "paragraph", "text": "[rel](/learning/lesson/1)"},
                {"id": "b4", "type": "paragraph", "text": "[anchor](#section)"},
                {"id": "b5", "type": "paragraph", "text": "[bare](example.com/page)"},
                {"id": "b6", "type": "paragraph", "text": "[host](//example.com/a)"},
            ]
        )
        == []
    )


def test_nested_card_and_quiz_text_is_scanned() -> None:
    errors = check_link_schemes(
        [
            {
                "id": "b1",
                "type": "card_group",
                "cards": [
                    {"id": "c1", "title": "Ok", "body": "[x](vbscript:msgbox)"},
                ],
            },
            {
                "id": "b2",
                "type": "quiz",
                "questions": [
                    {
                        "id": "q1",
                        "q": "Which [one](javascript:0)?",
                        "options": ["a", "b"],
                        "correct": 0,
                        "explanation": "because",
                    }
                ],
            },
        ]
    )
    assert len(errors) == 2


def test_embed_video_must_be_http_or_https() -> None:
    assert (
        check_link_schemes(
            [
                {
                    "id": "b1",
                    "type": "video",
                    "source": "embed",
                    "url": "https://player.vimeo.com/video/1",
                }
            ]
        )
        == []
    )
    errors = check_link_schemes(
        [{"id": "b1", "type": "video", "source": "embed", "url": "javascript:alert(1)"}]
    )
    assert any("javascript" in e for e in errors)


def test_blob_paths_are_not_treated_as_urls() -> None:
    assert (
        check_link_schemes(
            [
                {"id": "b1", "type": "image", "blob_path": "images/abc.png", "alt": "A"},
                {"id": "b2", "type": "video", "source": "blob", "blob_path": "videos/d.mp4"},
            ]
        )
        == []
    )


def test_validate_content_blocks_includes_the_scheme_check() -> None:
    """Wiring assertion: both AI paths call validate_content_blocks, so the
    scheme check must ride along with it, not need a separate call site."""
    errors = validate_content_blocks(
        [{"id": "b1", "type": "paragraph", "text": "[x](javascript:alert(1))"}]
    )
    assert any("javascript" in e for e in errors)


def test_non_list_input_is_tolerated() -> None:
    assert check_link_schemes({"id": "b1"}) == []
    assert check_link_schemes(None) == []


# --- bypass hardening (ruling 1): browsers strip ASCII TAB/LF/CR from
# anywhere in a url, and strip leading C0 controls/spaces, before parsing the
# scheme -- so the scheme check must normalise the same way before judging. ---


def test_tab_split_javascript_scheme_is_rejected() -> None:
    errors = check_link_schemes(
        [{"id": "b1", "type": "paragraph", "text": "[x](java\tscript:alert(1))"}]
    )
    assert any("javascript" in e for e in errors)


def test_mixed_case_javascript_scheme_is_rejected() -> None:
    errors = check_link_schemes(
        [{"id": "b1", "type": "paragraph", "text": "[x](JaVaScRiPt:alert(1))"}]
    )
    assert any("javascript" in e for e in errors)


def test_leading_control_char_javascript_scheme_is_rejected() -> None:
    errors = check_link_schemes(
        [{"id": "b1", "type": "paragraph", "text": "[x](\x01javascript:alert(1))"}]
    )
    assert any("javascript" in e for e in errors)


def test_leading_space_javascript_scheme_is_rejected() -> None:
    errors = check_link_schemes(
        [{"id": "b1", "type": "paragraph", "text": "[x](  javascript:alert(1))"}]
    )
    assert any("javascript" in e for e in errors)


# --- overlapping-scan hardening (review 2026-09-25, Critical 1): renderInline.tsx
# tokenises bold, italic and link together in one alternation, so a bold/italic
# token starting before what looks like a completed link can consume part of it
# and expose a DIFFERENT link -- with a bad scheme -- inside the leftover text.
# A left-to-right, non-overlapping link-only scan (the pre-fix behaviour) misses
# this because it only ever sees the FIRST link-shaped span. ---


def test_link_scheme_bypass_via_italic_overlap_is_rejected() -> None:
    # Reproduction from the review: the renderer's italic token `*a [b](c *`
    # (matching up to the next lone "*") consumes the start of what looks like
    # the first link, exposing "[z](javascript:alert(1))" as a second link that
    # actually renders as <a href="javascript:alert(1">. The pre-fix
    # non-overlapping scan only ever found the first "[...](...)" span, whose
    # target ("c *[z](javascript:alert(1") has no scheme, and returned [].
    text = "*a [b](c *[z](javascript:alert(1))"
    errors = check_link_schemes([{"id": "b1", "type": "paragraph", "text": text}])
    assert any("javascript" in e for e in errors)


def test_link_scheme_bypass_via_bold_overlap_is_rejected() -> None:
    # Same shape, with a "**...**" bold token instead of "*...*" italic one --
    # the review notes this variant "behaves the same".
    text = "**a [b](c **[z](javascript:alert(1))**"
    errors = check_link_schemes([{"id": "b1", "type": "paragraph", "text": text}])
    assert any("javascript" in e for e in errors)


def test_link_scheme_bypass_via_newline_in_text_is_rejected() -> None:
    # Reproduction from re-review round 2: renderInline.tsx's SPLIT step
    # (renderInline.tsx:6) excludes "\n" from the link text class, so a
    # segment like "[x\ny](javascript:alert%281%29)" isn't recognised as a
    # link token there -- but the leftover segment is then tested whole
    # against the PER-PART regex (renderInline.tsx:10,
    # `^\[([^\]]+)\]\(([^)]+)\)$`), which has NO "\n" exclusion at all, so it
    # still renders as a link. Real paragraph text carries embedded newlines
    # (ParagraphBlock.tsx joins wrapped lines with "\n"), so this is reachable.
    # The percent-encoded parens avoid closing the link target early while
    # still decoding to a working alert(1) once the browser un-escapes it.
    text = "[x\ny](javascript:alert%281%29)"
    errors = check_link_schemes([{"id": "b1", "type": "paragraph", "text": text}])
    assert any("javascript" in e for e in errors)


def test_link_scheme_bypass_via_newline_in_target_is_rejected() -> None:
    # Same gap, newline inside the TARGET instead of the text. The renderer's
    # per-part regex allows "\n" in the target too, and a browser deletes
    # embedded LF/CR from a URL before parsing its scheme (the same fact
    # _normalise_target's normalisation already relies on), so
    # "java\nscript:..." executes as a plain javascript: href.
    text = "[x](java\nscript:alert%281%29)"
    errors = check_link_schemes([{"id": "b1", "type": "paragraph", "text": text}])
    assert any("javascript" in e for e in errors)


def test_host_colon_port_target_is_rejected_as_a_scheme() -> None:
    # `localhost:8000/a` parses as an explicit scheme "localhost" under RFC
    # 3986, and a browser's URL parser would read it exactly the same way --
    # the link is already broken as a bare host:port target, so rejecting it
    # here is defensible even though the resulting error text reads oddly
    # ("disallowed url scheme 'localhost'"). Left as-is per review minor 2:
    # a live-corpus census should watch for host:port-shaped targets too.
    errors = check_link_schemes(
        [{"id": "b1", "type": "paragraph", "text": "[x](localhost:8000/a)"}]
    )
    assert any("localhost" in e for e in errors)
