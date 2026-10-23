"""Test 1: Only authorized recruiters can manage assessments."""

import pytest
from fastapi.testclient import TestClient


def test_recruiter_can_create_assessment(client: TestClient, recruiter_token: str, sample_org):
    """Authorized recruiter can create an assessment."""
    payload = {
        "title": "Senior Backend Engineer",
        "role": "Senior Backend Engineer",
        "job_description": "Building high-throughput microservices in Python.",
        "organization_id": sample_org.id,
        "competencies": [
            {
                "name": "System Architecture",
                "weight": 1.5,
                "rubric": {
                    "min_score": 1,
                    "max_score": 5,
                    "criteria": "Evaluates distributed systems design and trade-offs."
                },
                "questions": [
                    {
                        "prompt": "How do you design a partitioned distributed cache?",
                        "difficulty": "hard",
                        "question_type": "technical"
                    }
                ]
            }
        ]
    }
    response = client.post(
        "/api/v1/assessments",
        json=payload,
        headers={"Authorization": f"Bearer {recruiter_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Senior Backend Engineer"
    assert data["role"] == "Senior Backend Engineer"
    assert data["competencies_count"] == 1
    assert data["questions_count"] == 1


def test_candidate_forbidden_from_managing_assessments(client: TestClient, candidate_1_token: str):
    """Candidate attempting to create an assessment must be rejected with 403 Forbidden."""
    payload = {
        "title": "Hacked Assessment",
        "role": "Intern",
        "job_description": "Unauthorized attempt",
        "competencies": [{"name": "Comp", "weight": 1.0}]
    }
    response = client.post(
        "/api/v1/assessments",
        json=payload,
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert response.status_code == 403
    assert "Recruiter privileges required" in response.json()["detail"]


def test_unauthenticated_request_rejected(client: TestClient):
    """Unauthenticated request must be rejected with 401 Unauthorized."""
    response = client.post(
        "/api/v1/assessments",
        json={"title": "Test", "role": "Test", "job_description": "Test", "competencies": []}
    )
    assert response.status_code == 401
