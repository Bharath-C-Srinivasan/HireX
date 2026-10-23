"""Pydantic schemas for Assessments, Competencies, Rubrics, and Questions."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ScoringRubricBase(BaseModel):
    min_score: int = Field(default=1, ge=1, le=5)
    max_score: int = Field(default=5, ge=1, le=5)
    criteria: str = Field(..., min_length=5, description="Rubric scoring criteria")
    good_indicators: Optional[List[str]] = None
    poor_indicators: Optional[List[str]] = None


class ScoringRubricCreate(ScoringRubricBase):
    pass


class ScoringRubricResponse(ScoringRubricBase):
    id: str
    competency_id: str

    model_config = ConfigDict(from_attributes=True)


class QuestionBase(BaseModel):
    prompt: str = Field(..., min_length=5)
    difficulty: str = Field(default="medium")
    question_type: str = Field(default="technical")
    order_index: int = Field(default=0)
    is_follow_up: bool = False
    parent_question_id: Optional[str] = None
    follow_up_topic: Optional[str] = None


class QuestionCreate(QuestionBase):
    competency_index: Optional[int] = Field(None, description="0-based index of competency in assessment")


class QuestionResponse(QuestionBase):
    id: str
    assessment_id: str
    competency_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompetencyBase(BaseModel):
    name: str = Field(..., min_length=2)
    description: Optional[str] = None
    weight: float = Field(default=1.0, gt=0)
    order_index: int = Field(default=0)


class CompetencyCreate(CompetencyBase):
    rubric: Optional[ScoringRubricCreate] = None
    questions: Optional[List[QuestionCreate]] = None


class CompetencyResponse(CompetencyBase):
    id: str
    assessment_id: str
    rubric: Optional[ScoringRubricResponse] = None
    questions: Optional[List[QuestionResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentCreate(BaseModel):
    title: str = Field(..., min_length=3)
    role: str = Field(..., min_length=2)
    job_description: str = Field(..., min_length=10)
    organization_id: Optional[str] = None
    competencies: List[CompetencyCreate] = Field(..., min_length=1)
    general_questions: Optional[List[QuestionCreate]] = None


class AssessmentResponse(BaseModel):
    id: str
    title: str
    role: str
    job_description: str
    status: str
    scoring_rubric_version: str
    organization_id: str
    created_at: datetime
    competencies_count: int = 0
    questions_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AssessmentDetailResponse(AssessmentResponse):
    competencies: List[CompetencyResponse] = []
    questions: List[QuestionResponse] = []
