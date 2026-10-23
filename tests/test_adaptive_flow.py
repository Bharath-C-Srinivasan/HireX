"""Test 9: Adaptive workflow - follow-up question triggered when follow_up_needed is true."""

import pytest
from fastapi.testclient import TestClient
from app.models.entities import Interview


def test_adaptive_follow_up_generation(
    client: TestClient,
    sample_interview: Interview,
    candidate_1_token: str
):
    """
    When an evaluation identifies follow_up_needed=true (e.g., missing transaction boundaries):
    The next-question endpoint automatically yields an adaptive follow-up question
    tailored to the follow-up topic.
    """
    q1 = sample_interview.assessment.questions[0]

    # Candidate provides an answer that omits transaction boundaries
    # This triggers follow_up_needed=True and topic="transaction boundaries"
    answer_text = "I use an idempotency key with a unique constraint in the database."
    payload = {
        "question_id": q1.id,
        "transcript_text": answer_text,
        "idempotency_key": "adaptive-test-key-001"
    }

    # Submit answer
    submit_res = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["evaluation"]["follow_up_needed"] is True
    assert submit_data["evaluation"]["follow_up_topic"] == "transaction boundaries"

    # Request next question -> should be adaptive follow-up
    next_q_res = client.get(
        f"/api/v1/interviews/{sample_interview.id}/next-question",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert next_q_res.status_code == 200
    next_q_data = next_q_res.json()

    assert next_q_data["is_follow_up"] is True
    assert next_q_data["follow_up_topic"] == "transaction boundaries"
    assert "transaction boundaries" in next_q_data["question"]["prompt"]
    assert next_q_data["question"]["parent_question_id"] == q1.id
