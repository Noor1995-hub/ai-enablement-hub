from src.services.prompt_service import missing_tokens, KNOWN_PROMPTS

def test_missing_tokens_flags_dropped_playbook_slot():
    body = "no slots here"
    assert set(missing_tokens("interview_playbook", body)) == {
        "{first_name}", "{assessment_json}", "{company_context}", "{transcript}"}

def test_missing_tokens_ok_when_all_present():
    body = "{first_name} {assessment_json} {company_context} {transcript}"
    assert missing_tokens("interview_playbook", body) == []

def test_verbatim_prompt_has_no_required_tokens():
    assert missing_tokens("house_style", "anything") == []

def test_known_prompts_covers_the_nine():
    kinds = {p.kind for p in KNOWN_PROMPTS}
    assert kinds == {"interview","interview_playbook","chatbot","assessment","lesson",
        "content_improvement","content_improvement_critique","house_style","feedback_triage"}
