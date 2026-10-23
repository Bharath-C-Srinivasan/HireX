"""Candidates API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.schemas.candidate import CandidateCreate, CandidateResponse
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post(
    "",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a candidate",
    description="Register a candidate profile with email, full name, resume, and metadata."
)
def register_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    candidate = CandidateService.register_candidate(db, payload, current_user)
    return candidate


@router.get(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="Get candidate profile"
)
def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    candidate = CandidateService.get_candidate(db, candidate_id)
    return candidate
