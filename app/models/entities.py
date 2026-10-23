"""SQLAlchemy database models for HIREX."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    users = relationship("User", back_populates="organization")
    assessments = relationship("Assessment", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="candidate")  # recruiter, candidate, admin
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="users")
    assessments_created = relationship("Assessment", back_populates="created_by")
    candidate_profile = relationship("Candidate", back_populates="user", uselist=False)


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    resume_text = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="candidate_profile")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    job_description = Column(Text, nullable=False)
    status = Column(String(50), default="active", nullable=False)
    scoring_rubric_version = Column(String(50), default="v1.0.0", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="assessments")
    created_by = relationship("User", back_populates="assessments_created")
    competencies = relationship("Competency", back_populates="assessment", cascade="all, delete-orphan", order_by="Competency.order_index")
    questions = relationship("Question", back_populates="assessment", cascade="all, delete-orphan", order_by="Question.order_index")
    interviews = relationship("Interview", back_populates="assessment")


class Competency(Base):
    __tablename__ = "competencies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    weight = Column(Float, default=1.0, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    assessment = relationship("Assessment", back_populates="competencies")
    rubric = relationship("ScoringRubric", back_populates="competency", uselist=False, cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="competency")


class ScoringRubric(Base):
    __tablename__ = "scoring_rubrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    competency_id = Column(String(36), ForeignKey("competencies.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_score = Column(Integer, default=1, nullable=False)
    max_score = Column(Integer, default=5, nullable=False)
    criteria = Column(Text, nullable=False)
    good_indicators = Column(JSON, nullable=True)
    poor_indicators = Column(JSON, nullable=True)

    competency = relationship("Competency", back_populates="rubric")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    competency_id = Column(String(36), ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True)
    prompt = Column(Text, nullable=False)
    difficulty = Column(String(50), default="medium", nullable=False)
    question_type = Column(String(50), default="technical", nullable=False)  # technical, behavioral, follow_up
    order_index = Column(Integer, default=0, nullable=False)
    is_follow_up = Column(Boolean, default=False, nullable=False)
    parent_question_id = Column(String(36), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    follow_up_topic = Column(String(255), nullable=True)

    assessment = relationship("Assessment", back_populates="questions")
    competency = relationship("Competency", back_populates="questions")
    answers = relationship("Answer", back_populates="question")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="created", nullable=False)  # created, in_progress, completed, failed, cancelled
    current_question_id = Column(String(36), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    current_competency_index = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)  # Optimistic concurrency lock
    livekit_room_sid = Column(String(255), nullable=True)
    summary_score = Column(Float, nullable=True)
    recommendation = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    assessment = relationship("Assessment", back_populates="interviews")
    candidate = relationship("Candidate", back_populates="interviews")
    answers = relationship("Answer", back_populates="interview", cascade="all, delete-orphan", order_by="Answer.submitted_at")
    evaluations = relationship("Evaluation", back_populates="interview", cascade="all, delete-orphan")
    events = relationship("ConversationEvent", back_populates="interview", cascade="all, delete-orphan", order_by="ConversationEvent.created_at")

    __table_args__ = (
        Index("idx_interview_candidate_assessment", "candidate_id", "assessment_id"),
    )


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    interview_id = Column(String(36), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    transcript_text = Column(Text, nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    audio_metadata = Column(JSON, nullable=True)

    interview = relationship("Interview", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("interview_id", "question_id", "idempotency_key", name="uq_interview_question_idempotency"),
        Index("idx_answer_interview_idempotency", "interview_id", "idempotency_key"),
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    answer_id = Column(String(36), ForeignKey("answers.id", ondelete="CASCADE"), unique=True, nullable=False)
    interview_id = Column(String(36), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, in_progress, completed, failed
    scores = Column(JSON, nullable=True)  # e.g. {"api_design": 4, "data_integrity": 3}
    overall_score = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)  # ["Candidate described a unique constraint"]
    rationale = Column(Text, nullable=True)
    follow_up_needed = Column(Boolean, default=False, nullable=False)
    follow_up_topic = Column(String(255), nullable=True)
    recommended_next_action = Column(String(50), nullable=True)  # follow_up, next_competency, complete
    adapter_version = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    answer = relationship("Answer", back_populates="evaluation")
    interview = relationship("Interview", back_populates="evaluations")


class ConversationEvent(Base):
    __tablename__ = "conversation_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    interview_id = Column(String(36), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    interview = relationship("Interview", back_populates="events")

    __table_args__ = (
        Index("idx_event_interview_type", "interview_id", "event_type"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(36), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class IdempotencyRecord(Base):
    """Stores idempotent request states and responses."""
    __tablename__ = "idempotency_records"

    idempotency_key = Column(String(128), primary_key=True)
    resource_type = Column(String(100), nullable=False)
    request_hash = Column(String(64), nullable=False)
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
