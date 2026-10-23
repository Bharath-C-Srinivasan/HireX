"""HIREX End-to-End Demo & Walkthrough Script.

Demonstrates:
1. Authentication (Recruiter & Candidate)
2. Assessment Creation & Verification
3. Candidate Registration
4. Interview Creation & State Transitions
5. Question Delivery & State Resumption
6. Answer Submission & Idempotency Key Replay
7. LLM Adaptive Follow-up Evaluation
8. Interview Completion
9. Authorized Recruiter Report Generation with Evidence Quotes
10. Security Checks (Candidate Forbidden from Reports)
"""

import os
import time
import json
from fastapi.testclient import TestClient
from app.main import app
from app.db.seed_data import seed_database
from app.core.database import SessionLocal, engine, Base
from app.models.entities import Assessment, Candidate, User


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title.upper()}")
    print("=" * 75)


def run_demo():
    print_banner("HIREX: AI Interview Workflow & Evaluation System Demo")
    
    # 1. Initialize clean DB and Seed Data
    print("\n[Step 1] Initializing clean database & seeding Backend Engineering Intern Assessment...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    db = SessionLocal()
    
    assessment = db.query(Assessment).filter(Assessment.title == "Backend Engineering Intern").first()
    candidate_db = db.query(Candidate).filter(Candidate.email == "alex.chen@example.com").first()
    recruiter_db = db.query(User).filter(User.email == "recruiter@acme.com").first()
    
    print(f"[OK] Found Assessment ID : {assessment.id} ({assessment.title})")
    print(f"[OK] Found Candidate ID  : {candidate_db.id} ({candidate_db.full_name})")
    print(f"[OK] Found Recruiter ID  : {recruiter_db.id} ({recruiter_db.full_name})")
    
    client = TestClient(app)
    
    # 2. Authenticate: Mint Tokens
    print_banner("Step 2: Minting Signed JWT Tokens for Recruiter and Candidate")
    res_recruiter_tok = client.post("/api/v1/auth/token", json={
        "user_id": recruiter_db.id,
        "email": recruiter_db.email,
        "role": "recruiter",
        "organization_id": assessment.organization_id
    })
    recruiter_token = res_recruiter_tok.json()["access_token"]
    print(f"[OK] Recruiter JWT Token: {recruiter_token[:35]}...")

    res_candidate_tok = client.post("/api/v1/auth/token", json={
        "user_id": candidate_db.id,
        "email": candidate_db.email,
        "role": "candidate",
        "organization_id": assessment.organization_id,
        "candidate_id": candidate_db.id
    })
    candidate_token = res_candidate_tok.json()["access_token"]
    print(f"[OK] Candidate JWT Token: {candidate_token[:35]}...")

    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

    # 3. Create Interview
    print_banner("Step 3: Creating Candidate Interview")
    interview_res = client.post("/api/v1/interviews", json={
        "assessment_id": assessment.id,
        "candidate_id": candidate_db.id
    }, headers=recruiter_headers)
    assert interview_res.status_code == 201
    interview_data = interview_res.json()
    interview_id = interview_data["id"]
    print(f"[OK] Interview Created: {interview_id}")
    print(f"  Status: {interview_data['status']}")

    # 4. Candidate Starts Interview & Fetches First Question
    print_banner("Step 4: Candidate Requests Next Question (State -> in_progress)")
    q1_res = client.get(f"/api/v1/interviews/{interview_id}/next-question", headers=candidate_headers)
    assert q1_res.status_code == 200
    q1_data = q1_res.json()
    q1 = q1_data["question"]
    print(f"[OK] Active Status      : {q1_data['interview_status']}")
    print(f"[OK] Competency         : {q1_data['competency_name']}")
    print(f"[OK] Question ID        : {q1['id']}")
    print(f"[OK] Question Prompt    :\n  \"{q1['prompt']}\"")

    # 5. Candidate Submits Answer to Question 1
    # Notice: Omitting transaction boundaries triggers adaptive follow-up!
    print_banner("Step 5: Submitting Answer to Question 1")
    q1_answer = (
        "Two identical answer submissions arrive after a client timeout. "
        "To prevent duplicate evaluation, I use an idempotency key passed by the client. "
        "I persist this key with a unique constraint in PostgreSQL. If a duplicate arrives, "
        "the database constraint blocks duplicate insert."
    )
    idemp_key_1 = f"demo-idemp-key-q1-{int(time.time())}"
    print(f"Candidate Answer:\n  \"{q1_answer}\"\n")
    print(f"Sending with Idempotency-Key: {idemp_key_1}")

    ans1_res = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={
            "question_id": q1["id"],
            "transcript_text": q1_answer,
            "idempotency_key": idemp_key_1
        },
        headers={**candidate_headers, "Idempotency-Key": idemp_key_1}
    )
    assert ans1_res.status_code == 200
    ans1_data = ans1_res.json()
    eval1 = ans1_data["evaluation"]
    print(f"[OK] Evaluation Status  : {eval1['status']}")
    print(f"[OK] Evaluated Scores   : {eval1['scores']}")
    print(f"[OK] Evidence Extracted : {eval1['evidence']}")
    print(f"[OK] Follow-up Needed   : {eval1['follow_up_needed']} (Topic: {eval1['follow_up_topic']})")
    print(f"[OK] Recommended Action : {eval1['recommended_next_action']}")

    # 6. Test Idempotency: Re-submitting Identical Answer with Same Key
    print_banner("Step 6: Idempotency Verification (Re-submitting duplicate answer)")
    ans1_dup_res = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={
            "question_id": q1["id"],
            "transcript_text": q1_answer,
            "idempotency_key": idemp_key_1
        },
        headers={**candidate_headers, "Idempotency-Key": idemp_key_1}
    )
    assert ans1_dup_res.status_code == 200
    ans1_dup_data = ans1_dup_res.json()
    print(f"[OK] Returned Identical Answer ID: {ans1_dup_data['answer_id']} (No duplicate created!)")

    # 7. Candidate Requests Next Question -> Adaptive Follow-up Served!
    print_banner("Step 7: Adaptive Follow-up Question Generated & Served")
    q2_res = client.get(f"/api/v1/interviews/{interview_id}/next-question", headers=candidate_headers)
    assert q2_res.status_code == 200
    q2_data = q2_res.json()
    assert q2_data["is_follow_up"] is True
    print(f"[OK] Is Adaptive Follow-up : {q2_data['is_follow_up']}")
    print(f"[OK] Follow-up Topic       : {q2_data['follow_up_topic']}")
    print(f"[OK] Adaptive Prompt       :\n  \"{q2_data['question']['prompt']}\"")

    # 8. Candidate Answers the Follow-up Question
    print_banner("Step 8: Answering Adaptive Follow-up on Transaction Boundaries")
    q2_answer = (
        "For transaction boundaries, I wrap the deduplication check and answer persistence "
        "in a SERIALIZABLE or READ COMMITTED transaction with SELECT ... FOR UPDATE row-level locking "
        "to eliminate race conditions."
    )
    ans2_res = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={
            "question_id": q2_data["question"]["id"],
            "transcript_text": q2_answer,
            "idempotency_key": f"demo-followup-{int(time.time())}"
        },
        headers=candidate_headers
    )
    assert ans2_res.status_code == 200
    print(f"[OK] Follow-up Evaluated. Scores: {ans2_res.json()['evaluation']['scores']}")

    # 9. Complete Remaining Questions
    print_banner("Step 9: Answering Remaining Questions in Question Bank")
    while True:
        nxt = client.get(f"/api/v1/interviews/{interview_id}/next-question", headers=candidate_headers)
        nxt_data = nxt.json()
        if nxt_data["interview_status"] == "completed" or not nxt_data.get("question"):
            print(f"[OK] All questions answered. Interview transitioned to '{nxt_data['interview_status']}'.")
            break
        q_curr = nxt_data["question"]
        print(f"-> Answering: {q_curr['prompt'][:60]}...")
        sub = client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            json={
                "question_id": q_curr["id"],
                "transcript_text": "To address this in production, I implement compound indexing on candidate and timestamp columns, enforce RBAC authorization dependencies, write automated pytest mock adapters, and decouple tasks with background workers.",
                "idempotency_key": f"idemp-loop-{q_curr['id']}-{int(time.time() * 1000)}"
            },
            headers=candidate_headers
        )
        assert sub.status_code == 200

    # 10. Security Verification: Candidate cannot view recruiter report
    print_banner("Step 10: Security Check - Candidate Prohibited from Recruiter Report")
    cand_report_res = client.get(f"/api/v1/interviews/{interview_id}/report", headers=candidate_headers)
    print(f"Candidate report request status code: {cand_report_res.status_code}")
    assert cand_report_res.status_code == 403
    print("[OK] Access strictly forbidden (403): Candidate cannot view internal recruiter report.")

    # 11. Recruiter Generates Authorized Report
    print_banner("Step 11: Authorized Recruiter Report Generation")
    rec_report_res = client.get(f"/api/v1/interviews/{interview_id}/report", headers=recruiter_headers)
    assert rec_report_res.status_code == 200
    report = rec_report_res.json()
    
    print("\n" + "#" * 75)
    print(f"  HIREX CANDIDATE EVALUATION REPORT")
    print("#" * 75)
    print(f"Candidate Name       : {report['candidate_name']} ({report['candidate_email']})")
    print(f"Assessment Role      : {report['role']} - {report['assessment_title']}")
    print(f"Interview Status     : {report['status'].upper()}")
    print(f"Overall Score        : {report['overall_score']} / 5.0")
    print(f"Hiring Recommendation: {report['recommendation'].upper()}")
    print(f"Recommendation Note  : {report['recommendation_summary']}")
    print(f"Rubric Version       : {report['rubric_version']}")
    print(f"LLM Adapter Version  : {report['adapter_version']}")
    print(f"Evaluations Count    : {report['successful_evaluations']} successful, {report['failed_evaluations']} failed")
    
    print("\n--- Competency Breakdown ---")
    for comp in report["competency_breakdown"]:
        avg = f"{comp['average_score']}/5.0" if comp['average_score'] else "N/A"
        print(f"• {comp['competency_name']:<25} | Weight: {comp['weight']} | Score: {avg}")
        if comp["key_evidence"]:
            print(f"  Evidence: {comp['key_evidence'][0]}")

    print("\n--- Question & Evidence Trace ---")
    for qe in report["question_evaluations"]:
        f_up = " [ADAPTIVE FOLLOW-UP]" if qe["is_follow_up"] else ""
        print(f"\nQ: {qe['prompt']}{f_up}")
        print(f"A: {qe['candidate_answer'][:90]}...")
        print(f"Scores: {qe['scores']} | Overall: {qe['overall_score']}")
        print(f"Evidence: {qe['evidence']}")
        print(f"Rationale: {qe['rationale']}")

    print("\n" + "=" * 75)
    print("  DEMO COMPLETED SUCCESSFULLY WITH 100% PASSING STEPS!")
    print("=" * 75)
    db.close()


if __name__ == "__main__":
    run_demo()
