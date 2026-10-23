"""Test 4: Malformed model output is rejected or safely retried."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import Interview, Answer, Evaluation


def test_malformed_llm_output_is_handled_safely(
    client: TestClient,
    db_session: Session,
    sample_interview: Interview,
    candidate_1_token: str
):
    """
    When LLM returns malformed JSON or unparseable output:
    1. Answer is safely persisted.
    2. Evaluation record captures failure with error details.
    3. Interview does not crash or corrupt.
    4. Next action guides to retry.
    """
    question_id = sample_interview.assessment.questions[1].id
    idempotency_key = "idemp-malformed-test-001"

    payload = {
        "question_id": question_id,
        "transcript_text": "I would normalize tables and add B-tree indexes.",
        "idempotency_key": idempotency_key
    }
    headers = {
        "Authorization": f"Bearer {candidate_1_token}",
        "Idempotency-Key": idempotency_key,
        "X-Simulation-Mode": "malformed"
    }

    res = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "evaluation_failed"
    assert data["next_action"] == "retry_evaluation"
    assert data["evaluation"]["status"] == "failed"
    assert "MalformedOutput" in data["evaluation"]["error_message"]

    # Verify answer is safely persisted in DB
    ans = db_session.query(Answer).filter(Answer.id == data["answer_id"]).first()
    assert ans is not None
    assert ans.transcript_text == payload["transcript_text"]

    # Verify evaluation status in DB
    ev = db_session.query(Evaluation).filter(Evaluation.answer_id == ans.id).first()
    assert ev is not None
    assert ev.status == "failed"
