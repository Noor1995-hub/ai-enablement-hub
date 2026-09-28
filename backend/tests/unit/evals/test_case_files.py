from __future__ import annotations

from evals.interviewer.cases import list_case_ids, load_case
from src.services.interview_context import BARRIERS, FREQ, SETUP, TOOLS

_EXPECTED_IDS = {
    "cfo-food",
    "commercial-director-construction",
    "ops-director-utility",
    "hr-manager-services",
    "compliance-head-food",
    "md-construction",
    "warehouse-planner-food",
    "food-safety-coordinator",
    "field-technician-utility",
    "data-analyst-services",
    "adv-assessment-injection",
    "adv-midinterview-injection",
    "adv-transcript-tag",
    "plant-manager-dutch",
}
_ADVERSARIAL_IDS = {"adv-assessment-injection", "adv-midinterview-injection", "adv-transcript-tag"}
_BANNED_INDUSTRY_WORDS = ("bank", "banking")
_SCORE_LEVELS = {"explore", "practitioner", "integrator"}
_USAGE_BANDS = {"dormant", "occasional", "regular", "embedded"}
_COMPETENCY_CODES = {"MISSING", "PARTIAL", "HAVE", "ADV_D", "ADV_E"}
_C5_CODES = {"PUBLIC_PASTE", "APPROVED_PASTE", "UNSURE", "KEPT_OUT", "NO_USE"}


def test_exactly_the_fourteen_expected_cases_exist() -> None:
    assert set(list_case_ids()) == _EXPECTED_IDS


def test_every_case_file_is_well_formed_and_status_consistent() -> None:
    # R12: status is a transient field once cases start getting simulated/approved, so
    # this validator must not pin "draft"/empty-transcript forever - it only needs to
    # hold for the frozen content shape, and hold across whichever status a case is
    # later moved to (a status this task's own 14 files never use, but a later
    # simulate/approve pass will).
    for case_id in list_case_ids():
        case = load_case(case_id)
        assert case["id"] == case_id
        assert case["status"] in ("draft", "approved"), f"{case_id}: bad status"
        assert isinstance(case["transcript"], list), f"{case_id}: transcript not a list"
        if case["status"] == "approved":
            assert case["transcript"], f"{case_id}: approved but transcript is empty"
            assert case["approval"]["approved_at"], f"{case_id}: approved but approved_at unset"
        assert "stop_after_answers" in case, f"{case_id}: missing stop_after_answers"
        assert case["tags"], f"{case_id}: no tags"
        assert case["industry"], f"{case_id}: no industry"
        assert not any(w in case["industry"].lower() for w in _BANNED_INDUSTRY_WORDS)
        assert case["persona"].strip(), f"{case_id}: empty persona"
        assessment = case["assessment"]
        assert assessment["b_freq"] in FREQ
        for tool in assessment.get("b_tools") or []:
            assert tool in TOOLS
        for setup in assessment.get("b_setup") or []:
            assert setup in SETUP
        for barrier in assessment.get("b_barriers") or []:
            assert barrier in BARRIERS
        for key in ("c1_code", "c2_code", "c3_code", "c4_code", "c6_code"):
            assert assessment[key] in _COMPETENCY_CODES, f"{case_id}: bad {key}"
        for code in assessment.get("c5_codes") or []:
            assert code in _C5_CODES, f"{case_id}: bad c5 code {code}"
        assert assessment["score_level"] in _SCORE_LEVELS
        assert assessment["usage_band"] in _USAGE_BANDS


def test_adversarial_cases_carry_a_distinct_canary() -> None:
    canaries = set()
    for case_id in _ADVERSARIAL_IDS:
        adversarial = load_case(case_id)["adversarial"]
        assert adversarial["where"] in ("assessment", "transcript")
        assert adversarial["canary"]
        canaries.add(adversarial["canary"])
    assert len(canaries) == len(_ADVERSARIAL_IDS), "adversarial canaries must be distinct"


def test_non_adversarial_cases_have_no_adversarial_block() -> None:
    for case_id in _EXPECTED_IDS - _ADVERSARIAL_IDS:
        assert load_case(case_id)["adversarial"] is None


def test_only_the_delegating_director_has_a_stop_cap() -> None:
    for case_id in _EXPECTED_IDS:
        expected = 4 if case_id == "ops-director-utility" else None
        assert load_case(case_id)["stop_after_answers"] == expected, case_id
