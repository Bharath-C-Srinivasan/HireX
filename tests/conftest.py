"""Pytest fixtures and test database setup."""

import pytest
import os
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.entities import (
    Organization,
    User,
    Candidate,
    Assessment,
    Competency,
    ScoringRubric,
    Question,
    Interview,
)

# Use isolated test SQLite database
TEST_DB_FILE = "./test_hirex.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create test tables before each test and drop at end."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_org(db_session: Session) -> Organization:
    """Create a sample organization."""
    org = Organization(name="HireX Test Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def recruiter_user(db_session: Session, sample_org: Organization) -> User:
    """Create recruiter user with JWT token."""
    user = User(
        email="recruiter_test@hirex.ai",
        full_name="Rachel Recruiter",
        role="recruiter",
        organization_id=sample_org.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def recruiter_token(recruiter_user: User) -> str:
    """Generate JWT token for recruiter."""
    return create_access_token({
        "sub": recruiter_user.id,
        "email": recruiter_user.email,
        "role": recruiter_user.role,
        "org_id": recruiter_user.organization_id
    })


@pytest.fixture
def candidate_1(db_session: Session, sample_org: Organization) -> Candidate:
    """Create candidate 1."""
    user = User(
        email="candidate1@example.com",
        full_name="Candidate One",
        role="candidate",
        organization_id=sample_org.id
    )
    db_session.add(user)
    db_session.flush()

    cand = Candidate(
        id=user.id,
        user_id=user.id,
        organization_id=sample_org.id,
        email=user.email,
        full_name=user.full_name,
        resume_text="FastAPI backend experience"
    )
    db_session.add(cand)
    db_session.commit()
    db_session.refresh(cand)
    return cand


@pytest.fixture
def candidate_1_token(candidate_1: Candidate) -> str:
    """Generate JWT token for candidate 1."""
    return create_access_token({
        "sub": candidate_1.id,
        "email": candidate_1.email,
        "role": "candidate",
        "org_id": candidate_1.organization_id,
        "candidate_id": candidate_1.id
    })


@pytest.fixture
def candidate_2(db_session: Session, sample_org: Organization) -> Candidate:
    """Create candidate 2."""
    user = User(
        email="candidate2@example.com",
        full_name="Candidate Two",
        role="candidate",
        organization_id=sample_org.id
    )
    db_session.add(user)
    db_session.flush()

    cand = Candidate(
        id=user.id,
        user_id=user.id,
        organization_id=sample_org.id,
        email=user.email,
        full_name=user.full_name,
        resume_text="Frontend React experience"
    )
    db_session.add(cand)
    db_session.commit()
    db_session.refresh(cand)
    return cand


@pytest.fixture
def candidate_2_token(candidate_2: Candidate) -> str:
    """Generate JWT token for candidate 2."""
    return create_access_token({
        "sub": candidate_2.id,
        "email": candidate_2.email,
        "role": "candidate",
        "org_id": candidate_2.organization_id,
        "candidate_id": candidate_2.id
    })


@pytest.fixture
def sample_assessment(db_session: Session, sample_org: Organization, recruiter_user: User) -> Assessment:
    """Create sample assessment with 2 competencies, rubrics, and 2 questions."""
    assessment = Assessment(
        organization_id=sample_org.id,
        created_by_user_id=recruiter_user.id,
        title="Backend Engineering Intern",
        role="Backend Engineering Intern",
        job_description="Intern assessment",
        status="active"
    )
    db_session.add(assessment)
    db_session.flush()

    # Competency 1
    c1 = Competency(
        assessment_id=assessment.id,
        name="Python/FastAPI",
        weight=1.0,
        order_index=0
    )
    db_session.add(c1)
    db_session.flush()

    r1 = ScoringRubric(
        competency_id=c1.id,
        min_score=1,
        max_score=5,
        criteria="Evaluates idempotency and transaction handling"
    )
    db_session.add(r1)

    q1 = Question(
        assessment_id=assessment.id,
        competency_id=c1.id,
        prompt="Two identical answer submissions arrive after a client timeout. How do you prevent duplicate evaluation?",
        difficulty="medium",
        question_type="technical",
        order_index=0
    )
    db_session.add(q1)

    # Competency 2
    c2 = Competency(
        assessment_id=assessment.id,
        name="SQL/data modeling",
        weight=1.0,
        order_index=1
    )
    db_session.add(c2)
    db_session.flush()

    r2 = ScoringRubric(
        competency_id=c2.id,
        min_score=1,
        max_score=5,
        criteria="Evaluates relational schema design and indexing"
    )
    db_session.add(r2)

    q2 = Question(
        assessment_id=assessment.id,
        competency_id=c2.id,
        prompt="How do you index an audit log table for fast timestamp range queries?",
        difficulty="medium",
        question_type="technical",
        order_index=1
    )
    db_session.add(q2)

    db_session.commit()
    db_session.refresh(assessment)
    return assessment


@pytest.fixture
def sample_interview(db_session: Session, sample_assessment: Assessment, candidate_1: Candidate) -> Interview:
    """Create sample interview for candidate 1."""
    first_q = sample_assessment.questions[0]
    interview = Interview(
        assessment_id=sample_assessment.id,
        candidate_id=candidate_1.id,
        status="created",
        current_question_id=first_q.id,
        version=1
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    return interview
