"""Service layer for Candidate registration and management."""

from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.entities import Candidate, Organization, User
from app.schemas.candidate import CandidateCreate
from app.core.security import CurrentUser
from app.core.logging import logger


class CandidateService:
    """Manages candidate registration and profiles."""

    @staticmethod
    def register_candidate(
        db: Session,
        data: CandidateCreate,
        current_user: Optional[CurrentUser] = None
    ) -> Candidate:
        """Register a new candidate."""
        # Find organization
        org_id = data.organization_id
        if not org_id and current_user:
            org_id = current_user.organization_id
        if not org_id:
            org = db.query(Organization).first()
            if not org:
                org = Organization(name="Default Organization")
                db.add(org)
                db.flush()
            org_id = org.id

        # Check existing candidate under same email & organization
        existing = db.query(Candidate).filter(
            Candidate.email == data.email,
            Candidate.organization_id == org_id
        ).first()
        if existing:
            # Update resume or return existing
            if data.resume_text:
                existing.resume_text = data.resume_text
            db.commit()
            db.refresh(existing)
            return existing

        candidate = Candidate(
            organization_id=org_id,
            email=data.email,
            full_name=data.full_name,
            resume_text=data.resume_text,
            extra_metadata=data.extra_metadata,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        logger.info(f"Registered candidate {candidate.id} ({candidate.email})")
        return candidate

    @staticmethod
    def get_candidate(db: Session, candidate_id: str) -> Candidate:
        """Fetch candidate by ID."""
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found."
            )
        return candidate
