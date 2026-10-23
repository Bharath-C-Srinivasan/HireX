"""Test 8: Report scores/evidence match persisted evaluation records."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import Interview, Evaluation, Answer


def test_report_matches_persisted_evaluation_records(
    client: TestClient,
    db_session: Session,
    sample_interview: Interview,
    candidate_1_token: str,
    recruiter_token: str
):
    """
    Verify that the generated Recruiter Report matches the exact persisted
    evaluation records, scores, evidence quotes, and rubric metadata.
    """
    question = sample_interview.assessment.questions[0]
    idempotency_key = "report-integrity-key-101"

    # 1. Candidate submits answer
    answer_text = "Two identical answer submissions arrive after a client timeout. I use an idempotency key with a unique constraint in PostgreSQL and wrap it in a transaction."
    payload = {
        "question_id": question.id,
        "transcript_text": answer_text,
        "idempotency_key": idempotency_key
    }
    submit_res = client.post(
        f"/api/v1/interviews/{sample_interview.id}/answers",
        json=payload,
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert submit_res.status_code == 200
    answer_id = submit_res.json()["answer_id"]

    # 2. Fetch evaluation directly from DB
    db_session.expire_all()
    evaluation = db_session.query(Evaluation).filter(Evaluation.answer_id == answer_id).first()
    assert evaluation is not None
    assert evaluation.status == "completed"

    # 3. Recruiter requests report
    report_res = client.get(
        f"/api/v1/interviews/{sample_interview.id}/report",
        headers={"Authorization": f"Bearer {recruiter_token}"}
    )
    assert report_res.status_code == 200
    report_data = report_res.json()

    # 4. Verify report matches persisted evaluation record
    assert report_data["interview_id"] == sample_interview.id
    assert report_data["candidate_id"] == sample_interview.candidate_id
    assert report_data["adapter_version"] == evaluation.adapter_version
    assert report_data["total_answers"] == 1
    assert report_data["successful_evaluations"] == 1

    # Verify question evaluation item
    q_eval_item = report_data["question_evaluations"][0]
    assert q_eval_item["question_id"] == question.id
    assert q_eval_item["candidate_answer"] == answer_text
    assert q_eval_item["scores"] == evaluation.scores
    assert q_eval_item["evidence"] == evaluation.evidence
    assert q_eval_item["rationale"] == evaluation.rationale
    assert q_eval_item["overall_score"] == evaluation.overall_score
