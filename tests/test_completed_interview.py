"""Test 6: Completed interviews reject further answers unless explicitly reopened."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import Interview, Question


def test_completed_interview_rejects_answers_until_reopened(
    client: TestClient,
    db_session: Session,
    sample_interview: Interview,
    candidate_1_token: str,
    recruiter_token: str
):
    """
    1. Mark interview as completed.
    2. Candidate submission must be rejected with 400 Bad Request.
    3. Next-question request must also be rejected with 400 Bad Request.
    4. Recruiter reopens interview.
    5. Candidate can now successfully submit answers.
    """
    # 1. Complete the interview
    sample_interview.status = "completed"
    db_session.commit()

    q = sample_interview.assessment.questions[0]
    payload = {
        "question_id": q.id,
        "transcript_text": "Late answer after completion.",
        "idempotency_key": "late-submission-key-1"
    }

    # 2. Submission rejected
    res_rejected = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_rejected.status_code == 400
    assert "completed" in res_rejected.json()["detail"].lower()

    # 3. Next-question rejected
    res_next_q = client.get(
        f"/api/v1/interviews/{sample_interview.id}/next-question",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_next_q.status_code == 400

    # 4. Recruiter reopens interview
    res_reopen = client.post(
        f"/api/v1/interviews/{sample_interview.id}/reopen",
        headers={"Authorization": f"Bearer {recruiter_token}"}
    )
    assert res_reopen.status_code == 200
    assert res_reopen.json()["status"] == "in_progress"

    # 5. Candidate submits successfully now
    res_allowed = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_allowed.status_code == 200
    assert res_allowed.json()["status"] == "success"
