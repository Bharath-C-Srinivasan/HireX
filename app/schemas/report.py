"""Pydantic schemas for Recruiter Report."""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class QuestionEvaluationItem(BaseModel):
    question_id: str
    prompt: str
    competency_name: Optional[str] = None
    is_follow_up: bool = False
    follow_up_topic: Optional[str] = None
    candidate_answer: str
    scores: Dict[str, int] = {}
    overall_score: Optional[float] = None
    evidence: List[str] = []
    rationale: Optional[str] = None
    evaluation_status: str
    submitted_at: datetime


class CompetencyReportItem(BaseModel):
    competency_id: str
    competency_name: str
    weight: float
    average_score: Optional[float] = None
    questions_evaluated: int
    rubric_criteria: Optional[str] = None
    key_evidence: List[str] = []
    summary_notes: Optional[str] = None


class RecruiterReportResponse(BaseModel):
    interview_id: str
    status: str
    candidate_id: str
    candidate_name: str
    candidate_email: str
    assessment_id: str
    assessment_title: str
    role: str
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None
    recommendation_summary: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    competency_breakdown: List[CompetencyReportItem] = []
    question_evaluations: List[QuestionEvaluationItem] = []
    rubric_version: str
    adapter_version: str
    total_answers: int
    successful_evaluations: int
    failed_evaluations: int
    generated_at: datetime
