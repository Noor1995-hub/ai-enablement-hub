from __future__ import annotations

from evals.interviewer.language import detect_language


def test_plain_english_is_english() -> None:
    assert (
        detect_language("Which system do you type the report into, and how long does it take?")
        == "en"
    )


def test_flemish_with_u_is_dutch() -> None:
    text = (
        "Dat is heel duidelijk, dank u. In welk systeem typt u dat rapport, en hoe lang duurt dat?"
    )
    assert detect_language(text) == "nl"


def test_mostly_english_with_a_dutch_slip_is_english() -> None:
    text = (
        "I export it from SAP and then, eigenlijk is het gewoon copy paste, I rebuild the "
        "whole sheet in Excel for the production meeting every week."
    )
    assert detect_language(text) == "en"


def test_mostly_dutch_with_english_system_names_is_dutch() -> None:
    text = (
        "Ik exporteer dat uit SAP en dan maak ik elke week de Excel voor de productievergadering."
    )
    assert detect_language(text) == "nl"


def test_too_little_text_is_unknown() -> None:
    assert detect_language("SAP.") == "unknown"
    assert detect_language("") == "unknown"


def test_short_assessment_answers_can_still_be_called() -> None:
    assert (
        detect_language(
            "Elke maandag hetzelfde rapport opnieuw maken in Excel vanuit de SAP-export"
        )
        == "nl"
    )
    assert (
        detect_language(
            "Re-keying the SAP export into Excel every month before the board deck goes out"
        )
        == "en"
    )


def test_words_both_languages_use_do_not_tip_the_balance() -> None:
    # PR #139 review: "was", "we", "me" are Dutch too; "die", "met", "word" English too.
    assert detect_language("Vorige week was ik ziek, dus we hebben me gebeld.") == "nl"
    assert detect_language("I met the team and we agreed which word to use for it.") == "en"
