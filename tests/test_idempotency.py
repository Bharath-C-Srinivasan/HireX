"""Test 3: Duplicate submissions do not create duplicate answers or evaluations."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import Interview, Answer, Evaluation


def test_duplicate_submissions_are_idempotent(
    client: TestClient,
    db_session: Session,
    sample_interview: Interview,
    candidate_1_token: str
):
    """
    Submitting duplicate answers with the same idempotency key:
    1. Returns identical responses.
    2. Persists exactly one Answer record in the database.
    3. Triggers exactly one Evaluation record in the database.
    """
    question_id = sample_interview.assessment.questions[0].id
    idempotency_key = "idemp-unique-test-key-001"

    payload = {
        "question_id": question_id,
        "transcript_text": "To prevent duplicate evaluation after a timeout, I implement an idempotency key with a unique constraint in the database.",
        "idempotency_key": idempotency_key
    }
    headers = {
        "Authorization": f"Bearer {candidate_1_token}",
        "Idempotency-Key": idempotency_key
    }

    # 1. First submission
    res1 = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers=headers
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] in ["success", "already_submitted"]
    answer_id_1 = data1["answer_id"]
    eval_1 = data1["evaluation"]
    assert eval_1 is not None

    # 2. Second submission with identical idempotency key
    res2 = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers=headers
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["answer_id"] == answer_id_1

    # 3. Assert exact single persistence in database
    answers_in_db = db_session.query(Answer).filter(
        Answer.interview_id == sample_interview.id,
        Answer.question_id == question_id
    ).all()
    assert len(answers_in_db) == 1, f"Expected exactly 1 answer in DB, found {len(answers_in_db)}"

    evaluations_in_db = db_session.query(Evaluation).filter(
        Evaluation.interview_id == sample_interview.id
    ).all()
    assert len(evaluations_in_db) == 1, f"Expected exactly 1 evaluation in DB, found {len(evaluations_in_db)}"
