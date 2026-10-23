"""Seed script populating initial organization, recruiter, candidate, and Backend Engineering Intern assessment."""

import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.entities import (
    Organization,
    User,
    Candidate,
    Assessment,
    Competency,
    ScoringRubric,
    Question,
)
from app.core.logging import logger


def seed_database():
    """Populate sample dataset according to scenario specifications."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        existing_org = db.query(Organization).filter(Organization.name == "Acme Engineering").first()
        if existing_org:
            logger.info("Database already seeded.")
            return

        logger.info("Seeding database with sample assessment and competencies...")

        # 1. Organization
        org = Organization(name="Acme Engineering")
        db.add(org)
        db.flush()

        # 2. Recruiter User
        recruiter = User(
            organization_id=org.id,
            email="recruiter@acme.com",
            full_name="Jane Recruiter",
            role="recruiter"
        )
        db.add(recruiter)
        db.flush()

        # 3. Candidate
        candidate = Candidate(
            organization_id=org.id,
            email="alex.chen@example.com",
            full_name="Alex Chen",
            resume_text="CS sophomore with experience in Python, FastAPI, and PostgreSQL. Built REST APIs and hobby apps."
        )
        db.add(candidate)
        db.flush()

        # 4. Assessment: Backend Engineering Intern
        assessment = Assessment(
            organization_id=org.id,
            created_by_user_id=recruiter.id,
            title="Backend Engineering Intern",
            role="Backend Engineering Intern",
            job_description=(
                "Evaluation for Backend Engineering Intern candidates. Tests proficiency in "
                "Python/FastAPI, SQL & data modeling, API security, testing & debugging, and problem-solving."
            ),
            status="active",
            scoring_rubric_version="v1.0.0"
        )
        db.add(assessment)
        db.flush()

        # 5. Competencies, Rubrics, and Questions
        competency_data = [
            {
                "name": "Python/FastAPI",
                "description": "Proficiency with async Python, FastAPI dependency injection, and REST API conventions.",
                "weight": 1.2,
                "rubric": {
                    "min_score": 1,
                    "max_score": 5,
                    "criteria": "Evaluates knowledge of FastAPI lifecycle, Pydantic validation, dependency injection, and async I/O.",
                    "good_indicators": ["Uses Depends", "Mentions async/await non-blocking I/O", "Applies Pydantic v2 validators"],
                    "poor_indicators": ["Uses blocking calls in async def", "Ignores schema validation"]
                },
                "questions": [
                    {
                        "prompt": "Two identical answer submissions arrive after a client timeout. How do you prevent duplicate evaluation?",
                        "difficulty": "medium",
                        "question_type": "technical"
                    }
                ]
            },
            {
                "name": "SQL/data modeling",
                "description": "Relational schema design, constraints, indexing, and transaction boundaries.",
                "weight": 1.0,
                "rubric": {
                    "min_score": 1,
                    "max_score": 5,
                    "criteria": "Evaluates understanding of ACID transactions, foreign keys, uniqueness constraints, and index trade-offs.",
                    "good_indicators": ["Proposes unique constraint on idempotency key", "Defines transaction rollback semantics"],
                    "poor_indicators": ["Does not consider race conditions", "Omits database constraints"]
                },
                "questions": [
                    {
                        "prompt": "How would you model an audit logging table that tracks millions of interview events with fast lookups by candidate and timestamp without degrading write performance?",
                        "difficulty": "medium",
                        "question_type": "technical"
                    }
                ]
            },
            {
                "name": "API security",
                "description": "Authentication, authorization, prompt injection defense, and credential hygiene.",
                "weight": 1.0,
                "rubric": {
                    "min_score": 1,
                    "max_score": 5,
                    "criteria": "Evaluates defensive programming, token validation, RBAC, and untrusted input sanitization.",
                    "good_indicators": ["Enforces RBAC on endpoints", "Sanitizes candidate input before prompt inclusion", "Never exposes API keys in frontend"],
                    "poor_indicators": ["Concatenates raw candidate text into prompts without delimiters", "Relies solely on client-side security"]
                },
                "questions": [
                    {
                        "prompt": "How do you ensure that candidate answers cannot perform prompt injection to manipulate the LLM evaluation scores?",
                        "difficulty": "hard",
                        "question_type": "technical"
                    }
                ]
            },
            {
                "name": "testing/debugging",
                "description": "Unit testing, integration testing, and failure mode simulation.",
                "weight": 1.0,
                "rubric": {
                    "min_score": 1,
                    "max_score": 5,
                    "criteria": "Evaluates testing strategies for timeout resilience, concurrent requests, and malformed LLM responses.",
                    "good_indicators": ["Mocks external services with timeout exceptions", "Tests idempotency with identical payloads"],
                    "poor_indicators": ["Only tests happy path", "Does not test error recovery"]
                },
                "questions": [
                    {
                        "prompt": "How would you write automated tests to verify that an external LLM timeout does not leave the interview in a broken or falsely completed state?",
                        "difficulty": "medium",
                        "question_type": "technical"
                    }
                ]
            },
            {
                "name": "problem-solving",
                "description": "Architectural reasoning, latency optimization, and graceful degradation.",
                "weight": 1.0,
                "rubric": {
                    "min_score": 1,
                    "max_score": 5,
                    "criteria": "Evaluates reasoning about async background workers, event queues, and user experience.",
                    "good_indicators": ["Proposes decoupling evaluation to background queue", "Uses polling or WebSockets for status"],
                    "poor_indicators": ["Holds HTTP request open indefinitely"]
                },
                "questions": [
                    {
                        "prompt": "If the LLM evaluation takes 10 seconds per answer, how would you design the architecture to prevent client timeouts and ensure reliable background completion?",
                        "difficulty": "medium",
                        "question_type": "technical"
                    }
                ]
            }
        ]

        q_counter = 0
        for comp_idx, c_data in enumerate(competency_data):
            comp = Competency(
                assessment_id=assessment.id,
                name=c_data["name"],
                description=c_data["description"],
                weight=c_data["weight"],
                order_index=comp_idx
            )
            db.add(comp)
            db.flush()

            # Rubric
            r_data = c_data["rubric"]
            rubric = ScoringRubric(
                competency_id=comp.id,
                min_score=r_data["min_score"],
                max_score=r_data["max_score"],
                criteria=r_data["criteria"],
                good_indicators=r_data["good_indicators"],
                poor_indicators=r_data["poor_indicators"]
            )
            db.add(rubric)

            # Questions
            for q_data in c_data["questions"]:
                q = Question(
                    assessment_id=assessment.id,
                    competency_id=comp.id,
                    prompt=q_data["prompt"],
                    difficulty=q_data["difficulty"],
                    question_type=q_data["question_type"],
                    order_index=q_counter,
                    is_follow_up=False
                )
                db.add(q)
                q_counter += 1

        db.commit()
        logger.info(f"Seed complete. Assessment ID: {assessment.id}, Candidate ID: {candidate.id}, Recruiter ID: {recruiter.id}")
        return assessment.id, candidate.id, recruiter.id

    except Exception as e:
        db.rollback()
        logger.error(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
