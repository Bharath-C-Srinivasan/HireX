"""Pydantic schemas for Interview lifecycle, questions, answers, and evaluations."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.assessment import QuestionResponse
from app.schemas.llm import LLMEvaluationResult


class InterviewCreate(BaseModel):
    assessment_id: str
    candidate_id: str


class EvaluationResponse(BaseModel):
    id: str
    answer_id: str
    status: str
    scores: Optional[Dict[str, int]] = None
    overall_score: Optional[float] = None
    evidence: Optional[List[str]] = None
    rationale: Optional[str] = None
    follow_up_needed: bool = False
    follow_up_topic: Optional[str] = None
    recommended_next_action: Optional[str] = None
    adapter_version: str
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerResponse(BaseModel):
    id: str
    question_id: str
    transcript_text: str
    idempotency_key: str
    submitted_at: datetime
    evaluation: Optional[EvaluationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationEventResponse(BaseModel):
    id: str
    event_type: str
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewResponse(BaseModel):
    id: str
    assessment_id: str
    candidate_id: str
    status: str
    current_question_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    summary_score: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: datetime
    answers_count: int = 0
    total_questions: int = 0

    model_config = ConfigDict(from_attributes=True)


class InterviewProgressResponse(BaseModel):
    interview_id: str
    status: str
    current_question_index: int
    total_questions: int
    answers_count: int
    completion_percentage: float
    current_competency: Optional[str] = None
    started_at: Optional[datetime] = None


class NextQuestionResponse(BaseModel):
    interview_id: str
    interview_status: str
    question: Optional[QuestionResponse] = None
    competency_name: Optional[str] = None
    is_follow_up: bool = False
    follow_up_topic: Optional[str] = None
    progress: Dict[str, Any] = {}
    message: Optional[str] = None


class AnswerSubmissionRequest(BaseModel):
    question_id: str
    transcript_text: str = Field(..., min_length=1, description="Candidate voice transcript or text answer")
    idempotency_key: Optional[str] = Field(None, description="Client idempotency key (or via Idempotency-Key header)")
    audio_metadata: Optional[Dict[str, Any]] = Field(None, description="Audio track metadata for LiveKit integration")


class AnswerSubmissionResponse(BaseModel):
    status: str
    message: str
    answer_id: str
    idempotency_key: str
    evaluation: Optional[EvaluationResponse] = None
    next_action: str
    next_question: Optional[NextQuestionResponse] = None
