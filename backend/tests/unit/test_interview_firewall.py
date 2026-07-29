from src.schemas.interview import AdminInterviewResponse, InterviewStateResponse, PlaybookResponse


def test_learner_responses_never_expose_internal():
    assert "internal" not in PlaybookResponse.model_fields
    assert "internal" not in InterviewStateResponse.model_fields


def test_admin_response_carries_internal():
    assert "internal" in AdminInterviewResponse.model_fields
