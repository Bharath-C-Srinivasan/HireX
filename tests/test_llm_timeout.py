"""Test 5: LLM timeout leaves a recoverable state and does not falsely complete the interview."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import Interview, Answer, Evaluation


def test_llm_timeout_leaves_recoverable_state(
    client: TestClient,
    db_session: Session,
    sample_interview: Interview,
    candidate_1_token: str
):
    """
    When LLM evaluation times out:
    1. Answer is preserved in the database.
    2. Evaluation record reflects failure/timeout.
    3. Interview is NOT falsely marked as 'completed' (remains 'in_progress').
    4. State is recoverable.
    """
    question_id = sample_interview.assessment.questions[0].id
    idempotency_key = "idemp-timeout-test-001"

    payload = {
        "question_id": question_id,
        "transcript_text": "To prevent duplicate evaluation, we use atomic operations and distributed locks.",
        "idempotency_key": idempotency_key
    }
    headers = {
        "Authorization": f"Bearer {candidate_1_token}",
        "Idempotency-Key": idempotency_key,
        "X-Simulation-Mode": "timeout"
    }

    res = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "evaluation_failed"
    assert data["evaluation"]["status"] == "failed"
    assert "Timeout" in data["evaluation"]["error_message"]

    # Verify interview was NOT falsely completed!
    db_session.refresh(sample_interview)
    assert sample_interview.status != "completed", "Interview must NOT be falsely completed on LLM timeout"
    assert sample_interview.status == "in_progress"
    assert sample_interview.completed_at is None

    # Verify the answer was persisted
    persisted_answer = db_session.query(Answer).filter(Answer.id == data["answer_id"]).first()
    assert persisted_answer is not None
    assert persisted_answer.transcript_text == payload["transcript_text"]
