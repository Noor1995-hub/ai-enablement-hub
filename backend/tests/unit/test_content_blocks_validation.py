import copy

from src.services.content_blocks_validation import (
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
