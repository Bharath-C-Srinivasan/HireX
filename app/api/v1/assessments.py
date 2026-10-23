"""Assessments API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_recruiter, CurrentUser
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentResponse,
    AssessmentDetailResponse,
)
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create assessment, rubric and question bank",
    description="Authorized recruiter creates an assessment with role, competencies, scoring rubric, and questions."
)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_recruiter)
):
    assessment = AssessmentService.create_assessment(db, payload, current_user)
    return AssessmentResponse(
        id=assessment.id,
        title=assessment.title,
        role=assessment.role,
        job_description=assessment.job_description,
        status=assessment.status,
        scoring_rubric_version=assessment.scoring_rubric_version,
        organization_id=assessment.organization_id,
        created_at=assessment.created_at,
        competencies_count=len(assessment.competencies),
        questions_count=len(assessment.questions),
    )


@router.get(
    "",
    response_model=List[AssessmentResponse],
    summary="List all assessments for recruiter's organization"
)
def list_assessments(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_recruiter)
):
    assessments = AssessmentService.list_assessments(db, current_user.organization_id)
    return [
        AssessmentResponse(
            id=a.id,
            title=a.title,
            role=a.role,
            job_description=a.job_description,
            status=a.status,
            scoring_rubric_version=a.scoring_rubric_version,
            organization_id=a.organization_id,
            created_at=a.created_at,
            competencies_count=len(a.competencies),
            questions_count=len(a.questions),
        )
        for a in assessments
    ]


@router.get(
    "/{assessment_id}",
    response_model=AssessmentDetailResponse,
    summary="Get assessment details by ID"
)
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_recruiter)
):
    assessment = AssessmentService.get_assessment(db, assessment_id)
    return assessment
