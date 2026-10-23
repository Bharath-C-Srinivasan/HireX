"""Test 11: State resumption after browser refresh."""

import pytest
from fastapi.testclient import TestClient
from app.models.entities import Interview


def test_state_resumption_after_refresh(
    client: TestClient,
    sample_interview: Interview,
    candidate_1_token: str
):
    """
    When a candidate refreshes the browser or reconnects mid-interview:
    1. The interview status transitions to 'in_progress'.
    2. Repeated calls to next-question return the exact active question without skipping.
    3. The response flags 'is_resumed: True'.
    4. Progress state is intact.
    """
    # 1. First load: fetch first question
    res1 = client.get(
        f"/api/v1/interviews/{sample_interview.id}/next-question",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res1.status_code == 200
    q1_data = res1.json()
    assert q1_data["interview_status"] == "in_progress"
    active_q_id = q1_data["question"]["id"]

    # 2. Candidate refreshes browser (simulated by repeated GET /next-question)
    res_refresh1 = client.get(
        f"/api/v1/interviews/{sample_interview.id}/next-question",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_refresh1.status_code == 200
    refresh1_data = res_refresh1.json()
    assert refresh1_data["question"]["id"] == active_q_id
    assert refresh1_data["progress"]["is_resumed"] is True

    # 3. Candidate refreshes browser again
    res_refresh2 = client.get(
        f"/api/v1/interviews/{sample_interview.id}/next-question",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_refresh2.status_code == 200
    assert res_refresh2.json()["question"]["id"] == active_q_id

    # 4. Check interview progress endpoint
    res_interview = client.get(
        f"/api/v1/interviews/{sample_interview.id}",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_interview.status_code == 200
    inv_data = res_interview.json()
    assert inv_data["status"] == "in_progress"
    assert inv_data["current_question_id"] == active_q_id
    assert inv_data["answers_count"] == 0
