from content_qa.checks import find_americanisms, find_banned_punctuation


def _para(text):
    return [{"id": "p", "type": "paragraph", "text": text}]


def test_flags_em_en_dash_and_ellipsis():
    found = find_banned_punctuation(_para("A long thought — really … you know – yes"))
    chars = {f["char"] for f in found}
    assert chars == {"em-dash", "en-dash", "ellipsis"}
    assert all(f["snippet"] for f in found)


def test_clean_text_has_no_punctuation_findings():
    assert find_banned_punctuation(_para("A normal sentence, with a comma.")) == []


def test_flags_american_spellings():
    found = find_americanisms(_para("Organize the color of your behavior and analyze it."))
    terms = {f["term"].lower() for f in found}
    assert {"organize", "color", "behavior", "analyze"} <= terms
    for f in found:
        assert f["suggestion"]  # every hit carries a British suggestion


def test_does_not_flag_correct_british_forms():
    found = find_americanisms(_para(
        "Organise the colour of your behaviour, summarise the Artefact, and centre it."
    ))
    assert found == []


def test_americanism_word_boundaries_no_false_positives():
    # 'size', 'prize', 'maize' end in -ize but are not American -ise words;
    # 'parameter' contains 'meter'; none should fire.
    found = find_americanisms(_para("The size of the prize parameter in the maize field."))
    assert found == []


def test_flags_nested_quiz_option_text():
    blocks = [{"id": "q", "type": "quiz", "questions": [
        {"id": "1", "q": "Pick", "options": ["Organize files", "Leave them"],
         "correct": 0, "explanation": "ok"}]}]
    found = find_americanisms(blocks)
    assert any(f["path"].endswith("options[0]") for f in found)
