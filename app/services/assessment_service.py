"""Service layer for Assessment, Competency, Rubric, and Question management."""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.entities import (
    Assessment,
    Competency,
    ScoringRubric,
    Question,
    Organization,
    AuditEvent,
)
from app.schemas.assessment import AssessmentCreate, AssessmentResponse, AssessmentDetailResponse
from app.core.security import CurrentUser
from app.core.logging import logger


class AssessmentService:
    """Handles assessment setup, competency mapping, and question bank population."""

    @staticmethod
    def create_assessment(
        db: Session,
        data: AssessmentCreate,
        current_user: CurrentUser
    ) -> Assessment:
        """Create assessment, rubrics, competencies, and question bank."""
        # Determine organization ID
        org_id = data.organization_id or current_user.organization_id
        if not org_id:
            # Check if there is an existing organization or create default
            org = db.query(Organization).first()
            if not org:
                org = Organization(name="Default Organization")
                db.add(org)
                db.flush()
            org_id = org.id

        # 1. Create Assessment Header
        assessment = Assessment(
            organization_id=org_id,
            created_by_user_id=current_user.id if current_user.id != "system" else None,
            title=data.title,
            role=data.role,
            job_description=data.job_description,
            status="active",
            scoring_rubric_version="v1.0.0"
        )
        db.add(assessment)
        db.flush()

        total_questions = 0

        # 2. Add Competencies, Rubrics, and Questions
        for comp_idx, comp_in in enumerate(data.competencies):
            competency = Competency(
                assessment_id=assessment.id,
                name=comp_in.name,
                description=comp_in.description,
                weight=comp_in.weight,
                order_index=comp_in.order_index or comp_idx
            )
            db.add(competency)
            db.flush()

            # Create Rubric if provided
            if comp_in.rubric:
                rubric = ScoringRubric(
                    competency_id=competency.id,
                    min_score=comp_in.rubric.min_score,
                    max_score=comp_in.rubric.max_score,
                    criteria=comp_in.rubric.criteria,
                    good_indicators=comp_in.rubric.good_indicators,
                    poor_indicators=comp_in.rubric.poor_indicators
                )
                db.add(rubric)

            # Create Questions under this Competency
            if comp_in.questions:
                for q_idx, q_in in enumerate(comp_in.questions):
                    question = Question(
                        assessment_id=assessment.id,
                        competency_id=competency.id,
                        prompt=q_in.prompt,
                        difficulty=q_in.difficulty,
                        question_type=q_in.question_type,
                        order_index=total_questions,
                        is_follow_up=q_in.is_follow_up,
                        follow_up_topic=q_in.follow_up_topic
                    )
                    db.add(question)
                    total_questions += 1

        # 3. Add General Questions if provided
        if data.general_questions:
            for q_in in data.general_questions:
                question = Question(
                    assessment_id=assessment.id,
                    competency_id=None,
                    prompt=q_in.prompt,
                    difficulty=q_in.difficulty,
                    question_type=q_in.question_type,
                    order_index=total_questions,
                    is_follow_up=q_in.is_follow_up,
                    follow_up_topic=q_in.follow_up_topic
                )
                db.add(question)
                total_questions += 1

        # 4. Create Audit Log
        audit = AuditEvent(
            organization_id=org_id,
            user_id=current_user.id,
            action="create_assessment",
            resource_type="assessment",
            resource_id=assessment.id,
            details={"title": assessment.title, "role": assessment.role, "questions_count": total_questions}
        )
        db.add(audit)

        db.commit()
        db.refresh(assessment)
        logger.info(f"Assessment created successfully: {assessment.id} with {total_questions} questions")
        return assessment

    @staticmethod
    def get_assessment(db: Session, assessment_id: str) -> Assessment:
        """Fetch assessment by ID."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment {assessment_id} not found."
            )
        return assessment

    @staticmethod
    def list_assessments(db: Session, organization_id: Optional[str] = None) -> List[Assessment]:
        """List active assessments."""
        query = db.query(Assessment).filter(Assessment.status == "active")
        if organization_id:
            query = query.filter(Assessment.organization_id == organization_id)
        return query.order_by(Assessment.created_at.desc()).all()
