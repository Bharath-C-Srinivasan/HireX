"""Test 2: Candidates cannot access another candidate's interview or report."""

import pytest
from fastapi.testclient import TestClient
from app.models.entities import Interview


def test_candidate_cannot_access_other_interview(
    client: TestClient,
    sample_interview: Interview,
    candidate_1_token: str,
    candidate_2_token: str
):
    """Candidate 1 can access their interview, but Candidate 2 receives 403 Forbidden."""
    # 1. Candidate 1 accesses own interview -> 200 OK
    res_owner = client.get(
        f"/api/v1/interviews/{sample_interview.id}",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == sample_interview.id

    # 2. Candidate 2 attempts to access Candidate 1's interview -> 403 Forbidden
    res_other = client.get(
        f"/api/v1/interviews/{sample_interview.id}",
        headers={"Authorization": f"Bearer {candidate_2_token}"}
    )
    assert res_other.status_code == 403
    assert "cannot access another candidate" in res_other.json()["detail"].lower()


def test_candidate_cannot_access_recruiter_report(
    client: TestClient,
    sample_interview: Interview,
    candidate_1_token: str,
    recruiter_token: str
):
    """Candidates must never be allowed to view recruiter reports (403 Forbidden)."""
    # Candidate attempts to access recruiter report
    res_candidate = client.get(
        f"/api/v1/interviews/{sample_interview.id}/report",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res_candidate.status_code == 403
    assert "Recruiter privileges required" in res_candidate.json()["detail"]

    # Recruiter accesses report -> 200 OK
    res_recruiter = client.get(
        f"/api/v1/interviews/{sample_interview.id}/report",
        headers={"Authorization": f"Bearer {recruiter_token}"}
    )
    assert res_recruiter.status_code == 200
    data = res_recruiter.json()
    assert data["interview_id"] == sample_interview.id
    assert "competency_breakdown" in data
