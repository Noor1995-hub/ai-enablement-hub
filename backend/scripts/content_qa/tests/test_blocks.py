from content_qa.blocks import iter_texts


def test_extracts_simple_text_fields():
    blocks = [
        {"id": "a", "type": "heading", "level": 2, "text": "Hello"},
        {"id": "b", "type": "paragraph", "text": "World"},
    ]
    out = list(iter_texts(blocks))
    assert ("blocks[0].text", "Hello") in out
    assert ("blocks[1].text", "World") in out
    # non-prose keys are never yielded
    assert all("Hello" != t or p.endswith(".text") for p, t in out)
    assert not any(t in ("heading", "paragraph") for _, t in out)


def test_extracts_nested_quiz_and_card_text():
    blocks = [
        {
            "id": "q",
            "type": "quiz",
            "questions": [
                {"id": "q1", "q": "Why?", "options": ["A", "B"], "correct": 0,
                 "explanation": "Because."},
            ],
        },
        {"id": "c", "type": "card_group",
         "cards": [{"id": "c1", "title": "T", "body": "Bod"}]},
    ]
    texts = {t for _, t in iter_texts(blocks)}
    assert {"Why?", "A", "B", "Because.", "T", "Bod"} <= texts


def test_skips_non_prose_locators():
    blocks = [{"id": "i", "type": "image", "blob_path": "images/x.png",
               "alt": "a diagram", "url": "https://sas", "width": 80}]
    texts = {t for _, t in iter_texts(blocks)}
    assert "a diagram" in texts          # alt IS prose
    assert "images/x.png" not in texts   # blob_path is not
    assert "https://sas" not in texts    # url is not
