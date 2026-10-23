"""Test 7: Concurrent submissions do not advance the interview twice."""

import pytest
import concurrent.futures
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import Interview, Answer


def test_concurrent_submissions_prevent_double_advance(
    client: TestClient,
    db_session: Session,
    sample_interview: Interview,
    candidate_1_token: str
):
    """
    Simulate concurrent answer submissions:
    Verify that:
    1. Exactly one answer record is committed for the question.
    2. Optimistic versioning increments correctly without double-advancement.
    3. No race condition corrupts the interview progression.
    """
    question_id = sample_interview.assessment.questions[0].id
    initial_version = sample_interview.version

    def submit_attempt(key: str, text: str):
        payload = {
            "question_id": question_id,
            "transcript_text": text,
            "idempotency_key": key
        }
        return client.post(
            f"/api/v1/interviews/{sample_interview.id}/answers",
            json=payload,
            headers={
                "Authorization": f"Bearer {candidate_1_token}",
                "Idempotency-Key": key
            }
        )

    # Launch 2 simultaneous concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_attempt, "concurrency-key-A", "First concurrent answer with unique constraint.")
        f2 = executor.submit(submit_attempt, "concurrency-key-A", "First concurrent answer with unique constraint.")
        res1 = f1.result()
        res2 = f2.result()

    # Both return successfully (one processed, one idempotent replay or 409 locked)
    valid_statuses = [200, 409]
    assert res1.status_code in valid_statuses
    assert res2.status_code in valid_statuses

    # Verify that only 1 answer exists for this question in the database
    db_session.expire_all()
    answers = db_session.query(Answer).filter(
        Answer.interview_id == sample_interview.id,
        Answer.question_id == question_id
    ).all()
    assert len(answers) == 1, f"Expected 1 answer, got {len(answers)}"

    # Interview version incremented by exactly 1
    db_session.refresh(sample_interview)
    assert sample_interview.version == initial_version + 1
