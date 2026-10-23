"""Interviews API endpoints for lifecycle, questions, answers, evaluations, and reports."""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_recruiter, CurrentUser
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewProgressResponse,
    NextQuestionResponse,
    AnswerSubmissionRequest,
    AnswerSubmissionResponse,
)
from app.schemas.report import RecruiterReportResponse
from app.schemas.livekit import LiveKitTokenResponse
from app.services.interview_service import InterviewService
from app.services.report_service import ReportService
from app.services.livekit_service import LiveKitService

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an interview",
    description="Create an interview linking a candidate to an assessment."
)
def create_interview(
    payload: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    interview = InterviewService.create_interview(db, payload, current_user)
    return InterviewResponse(
        id=interview.id,
        assessment_id=interview.assessment_id,
        candidate_id=interview.candidate_id,
        status=interview.status,
        current_question_id=interview.current_question_id,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
        summary_score=interview.summary_score,
        recommendation=interview.recommendation,
        created_at=interview.created_at,
        answers_count=0,
        total_questions=len(interview.assessment.questions) if interview.assessment else 0
    )


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    summary="Return authorized state and progress",
    description="Returns interview state, timestamps, question counts, and progress."
)
def get_interview(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    interview = InterviewService.get_interview(db, interview_id, current_user)
    total_q = len(interview.assessment.questions) if interview.assessment else 0
    return InterviewResponse(
        id=interview.id,
        assessment_id=interview.assessment_id,
        candidate_id=interview.candidate_id,
        status=interview.status,
        current_question_id=interview.current_question_id,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
        summary_score=interview.summary_score,
        recommendation=interview.recommendation,
        created_at=interview.created_at,
        answers_count=len(interview.answers),
        total_questions=total_q
    )


@router.get(
    "/{interview_id}/next-question",
    response_model=NextQuestionResponse,
    summary="Return the next valid question",
    description="Determines next question based on interview state, adaptive follow-up triggers, or sequence."
)
def get_next_question(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    return InterviewService.get_next_question(db, interview_id, current_user)


@router.post(
    "/{interview_id}/answers",
    response_model=AnswerSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Persist answer and trigger/schedule evaluation",
    description="Submits an answer, persists it before evaluation, checks idempotency, and runs LLM evaluation."
)
async def submit_answer(
    interview_id: str,
    payload: AnswerSubmissionRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_simulation_mode: Optional[str] = Header(None, alias="X-Simulation-Mode"),
):
    result, status_code = await InterviewService.submit_answer(
        db=db,
        interview_id=interview_id,
        request=payload,
        current_user=current_user,
        idempotency_key_header=idempotency_key,
        simulation_mode=x_simulation_mode
    )
    response.status_code = status_code
    return result


@router.get(
    "/{interview_id}/report",
    response_model=RecruiterReportResponse,
    summary="Return authorized recruiter report",
    description="Returns full recruiter report with competency breakdown, evidence, and scores. Candidates cannot access."
)
def get_interview_report(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_recruiter)
):
    return ReportService.generate_report(db, interview_id, current_user)


@router.post(
    "/{interview_id}/reopen",
    response_model=InterviewResponse,
    summary="Explicitly reopen a completed interview (Recruiter only)"
)
def reopen_interview(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_recruiter)
):
    interview = InterviewService.reopen_interview(db, interview_id, current_user)
    return InterviewResponse(
        id=interview.id,
        assessment_id=interview.assessment_id,
        candidate_id=interview.candidate_id,
        status=interview.status,
        current_question_id=interview.current_question_id,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
        summary_score=interview.summary_score,
        recommendation=interview.recommendation,
        created_at=interview.created_at,
        answers_count=len(interview.answers),
        total_questions=len(interview.assessment.questions) if interview.assessment else 0
    )


@router.post(
    "/{interview_id}/livekit-token",
    response_model=LiveKitTokenResponse,
    summary="Generate LiveKit room token for voice/video interview"
)
def get_livekit_token(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    interview = InterviewService.get_interview(db, interview_id, current_user)
    participant_name = interview.candidate.full_name if interview.candidate else "Candidate"
    token_info = LiveKitService.generate_join_token(
        interview_id=interview.id,
        participant_identity=current_user.id,
        participant_name=participant_name
    )
    return LiveKitTokenResponse(**token_info)
