"""Interview Service for managing lifecycle, adaptive questions, answers, and idempotency."""

from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.models.entities import (
    Interview,
    Assessment,
    Candidate,
    Question,
    Answer,
    Evaluation,
    ConversationEvent,
    AuditEvent,
    Competency,
)
from app.schemas.interview import (
    InterviewCreate,
    AnswerSubmissionRequest,
    AnswerSubmissionResponse,
    NextQuestionResponse,
    QuestionResponse,
    EvaluationResponse,
)
from app.services.idempotency_service import IdempotencyService
from app.services.evaluation_service import EvaluationService
from app.core.security import CurrentUser


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InterviewService:
    """Core domain service for interview execution and state transitions."""

    @staticmethod
    def _verify_interview_access(
        interview: Interview,
        current_user: CurrentUser,
        allow_candidate: bool = True
    ) -> None:
        """
        Enforce strict authorization and resource ownership.
        Candidates may only view their own interview.
        Recruiters may view interviews within their organization.
        """
        if current_user.role in ["recruiter", "admin"]:
            if current_user.organization_id and interview.assessment:
                if interview.assessment.organization_id != current_user.organization_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access forbidden: You do not have permission for this interview's organization."
                    )
            return

        if current_user.role == "candidate":
            if not allow_candidate:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Candidate not authorized for this resource."
                )
            # Match candidate by ID or email
            matches_candidate_id = current_user.candidate_id and current_user.candidate_id == interview.candidate_id
            matches_user_id = interview.candidate and interview.candidate.user_id == current_user.id
            matches_email = interview.candidate and interview.candidate.email == current_user.email
            matches_test_id = current_user.id == interview.candidate_id

            if not (matches_candidate_id or matches_user_id or matches_email or matches_test_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot access another candidate's interview."
                )
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized role."
        )

    @staticmethod
    def create_interview(
        db: Session,
        data: InterviewCreate,
        current_user: CurrentUser
    ) -> Interview:
        """Create a new interview record."""
        assessment = db.query(Assessment).filter(Assessment.id == data.assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        candidate = db.query(Candidate).filter(Candidate.id == data.candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

        # Find first question if available
        first_q = db.query(Question).filter(
            Question.assessment_id == assessment.id,
            Question.is_follow_up == False
        ).order_by(Question.order_index).first()

        interview = Interview(
            assessment_id=assessment.id,
            candidate_id=candidate.id,
            status="created",
            current_question_id=first_q.id if first_q else None,
            version=1
        )
        db.add(interview)
        db.flush()

        # Emit interview_created event
        event = ConversationEvent(
            interview_id=interview.id,
            event_type="interview_created",
            payload={"candidate_id": candidate.id, "assessment_id": assessment.id}
        )
        db.add(event)

        audit = AuditEvent(
            organization_id=assessment.organization_id,
            user_id=current_user.id,
            action="create_interview",
            resource_type="interview",
            resource_id=interview.id,
            details={"candidate_email": candidate.email, "assessment_title": assessment.title}
        )
        db.add(audit)

        db.commit()
        db.refresh(interview)
        logger.info(f"Created interview {interview.id} for candidate {candidate.id}")
        return interview

    @staticmethod
    def get_interview(
        db: Session,
        interview_id: str,
        current_user: CurrentUser
    ) -> Interview:
        """Get interview with authorization and progress counts."""
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

        InterviewService._verify_interview_access(interview, current_user, allow_candidate=True)
        return interview

    @staticmethod
    def get_next_question(
        db: Session,
        interview_id: str,
        current_user: CurrentUser
    ) -> NextQuestionResponse:
        """
        Return the next valid question based on persisted state.
        Handles:
        - Refresh/resume: returns current pending question if one is already active.
        - Adaptive follow-up: serves adaptive follow-up if last answer required follow-up.
        - Sequenced question bank progression.
        - Completion: marks completed when all questions answered.
        - Rejection if interview is already completed/cancelled.
        """
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

        InterviewService._verify_interview_access(interview, current_user, allow_candidate=True)

        # 1. Reject advancing a completed or cancelled interview
        if interview.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Interview is already {interview.status}. Cannot request further questions."
            )

        # 2. Transition created -> in_progress on first question request
        if interview.status == "created":
            interview.status = "in_progress"
            interview.started_at = utc_now()
            db.add(ConversationEvent(
                interview_id=interview.id,
                event_type="interview_started",
                payload={"started_at": interview.started_at.isoformat()}
            ))
            db.commit()

        # 3. Check if current question is unanswered (Supports Browser Refresh / Resume!)
        answered_question_ids = [
            ans.question_id for ans in db.query(Answer.question_id).filter(Answer.interview_id == interview.id).all()
        ]

        if interview.current_question_id and interview.current_question_id not in answered_question_ids:
            # Resuming current question!
            q = db.query(Question).filter(Question.id == interview.current_question_id).first()
            if q:
                comp_name = q.competency.name if q.competency else None
                return NextQuestionResponse(
                    interview_id=interview.id,
                    interview_status=interview.status,
                    question=QuestionResponse.model_validate(q),
                    competency_name=comp_name,
                    is_follow_up=q.is_follow_up,
                    follow_up_topic=q.follow_up_topic,
                    progress={
                        "answers_submitted": len(answered_question_ids),
                        "is_resumed": True
                    },
                    message="Resuming active question."
                )

        # 4. Check if the latest answer requires an adaptive follow-up
        last_answer = db.query(Answer).filter(
            Answer.interview_id == interview.id
        ).order_by(Answer.submitted_at.desc()).first()

        if last_answer and last_answer.evaluation and last_answer.evaluation.follow_up_needed:
            parent_q = db.query(Question).filter(Question.id == last_answer.question_id).first()
            # Follow-up questions have a max depth of 1 (prevent infinite follow-up loops)
            if parent_q and not parent_q.is_follow_up:
                existing_follow_up = db.query(Question).filter(
                    Question.assessment_id == interview.assessment_id,
                    Question.parent_question_id == last_answer.question_id
                ).first()

                if not existing_follow_up:
                    topic = last_answer.evaluation.follow_up_topic or "system architecture"
                    prompt_text = f"Following up on your previous response regarding {topic}: Could you elaborate on how you handle this under high concurrency or failure conditions?"

                    follow_up_q = Question(
                        assessment_id=interview.assessment_id,
                        competency_id=parent_q.competency_id if parent_q else None,
                        prompt=prompt_text,
                        difficulty="hard",
                        question_type="follow_up",
                        order_index=999,
                        is_follow_up=True,
                        parent_question_id=last_answer.question_id,
                        follow_up_topic=topic
                    )
                    db.add(follow_up_q)
                    db.flush()
                else:
                    follow_up_q = existing_follow_up

                # If this follow-up has not been answered yet in this interview, serve it
                if follow_up_q.id not in answered_question_ids:
                    interview.current_question_id = follow_up_q.id
                    db.add(ConversationEvent(
                        interview_id=interview.id,
                        event_type="follow_up_triggered",
                        payload={"topic": follow_up_q.follow_up_topic, "parent_question_id": last_answer.question_id, "question_id": follow_up_q.id}
                    ))
                    db.commit()

                    return NextQuestionResponse(
                        interview_id=interview.id,
                        interview_status=interview.status,
                        question=QuestionResponse.model_validate(follow_up_q),
                        competency_name=parent_q.competency.name if (parent_q and parent_q.competency) else None,
                        is_follow_up=True,
                        follow_up_topic=follow_up_q.follow_up_topic,
                        progress={"answers_submitted": len(answered_question_ids)},
                        message="Adaptive follow-up question triggered based on previous evaluation."
                    )

        # 5. Serve next standard question from Assessment Question Bank
        next_q = db.query(Question).filter(
            Question.assessment_id == interview.assessment_id,
            Question.is_follow_up == False,
            ~Question.id.in_(answered_question_ids) if answered_question_ids else True
        ).order_by(Question.order_index).first()

        if next_q:
            interview.current_question_id = next_q.id
            db.add(ConversationEvent(
                interview_id=interview.id,
                event_type="question_served",
                payload={"question_id": next_q.id, "prompt": next_q.prompt[:80]}
            ))
            db.commit()

            return NextQuestionResponse(
                interview_id=interview.id,
                interview_status=interview.status,
                question=QuestionResponse.model_validate(next_q),
                competency_name=next_q.competency.name if next_q.competency else None,
                is_follow_up=False,
                progress={"answers_submitted": len(answered_question_ids)},
                message="Next question in sequence."
            )

        # 6. No more questions -> Complete interview!
        interview.status = "completed"
        interview.completed_at = utc_now()
        interview.current_question_id = None

        # Compute summary scores across completed evaluations
        eval_scores = [
            ev.overall_score for ev in interview.evaluations
            if ev.status == "completed" and ev.overall_score is not None
        ]
        if eval_scores:
            avg_score = round(sum(eval_scores) / len(eval_scores), 2)
            interview.summary_score = avg_score
            if avg_score >= 4.0:
                interview.recommendation = "strong_hire"
            elif avg_score >= 3.2:
                interview.recommendation = "hire"
            elif avg_score >= 2.5:
                interview.recommendation = "lean_hire"
            else:
                interview.recommendation = "no_hire"

        db.add(ConversationEvent(
            interview_id=interview.id,
            event_type="interview_completed",
            payload={"summary_score": interview.summary_score, "recommendation": interview.recommendation}
        ))
        db.commit()

        return NextQuestionResponse(
            interview_id=interview.id,
            interview_status="completed",
            question=None,
            progress={"answers_submitted": len(answered_question_ids), "all_completed": True},
            message="Interview successfully completed! All questions have been evaluated."
        )

    @staticmethod
    async def submit_answer(
        db: Session,
        interview_id: str,
        request: AnswerSubmissionRequest,
        current_user: CurrentUser,
        idempotency_key_header: Optional[str] = None,
        simulation_mode: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Submit and persist candidate answer before triggering evaluation.
        Ensures idempotency, concurrency protection, and error recovery.
        """
        # Determine idempotency key (header takes precedence, then body)
        idempotency_key = idempotency_key_header or request.idempotency_key
        if not idempotency_key:
            # Generate deterministic fallback if neither provided
            idempotency_key = f"key_{interview_id}_{request.question_id}"

        # 1. Check idempotency record
        is_cached, cached_body, cached_status = IdempotencyService.start_idempotent_operation(
            db=db,
            idempotency_key=idempotency_key,
            resource_type="submit_answer",
            request_payload={"interview_id": interview_id, "question_id": request.question_id, "text": request.transcript_text}
        )
        if is_cached and cached_body:
            logger.info(f"Returning cached idempotent response for key {idempotency_key}")
            return cached_body, cached_status or 200

        try:
            # Fetch interview
            interview = db.query(Interview).filter(Interview.id == interview_id).first()
            if not interview:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

            InterviewService._verify_interview_access(interview, current_user, allow_candidate=True)

            # 2. Reject submissions on completed interviews
            if interview.status in ["completed", "failed", "cancelled"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Interview is {interview.status}. Answers cannot be submitted to a closed interview."
                )

            if interview.status == "created":
                interview.status = "in_progress"
                interview.started_at = utc_now()

            # 3. Optimistic Concurrency & Duplicate Check
            # Check if answer already exists for this (interview_id, question_id)
            existing_ans = db.query(Answer).filter(
                Answer.interview_id == interview.id,
                Answer.question_id == request.question_id
            ).first()

            if existing_ans:
                # Answer for this question was already submitted!
                # If evaluation exists, return it
                eval_resp = EvaluationResponse.model_validate(existing_ans.evaluation) if existing_ans.evaluation else None
                response_data = {
                    "status": "already_submitted",
                    "message": "Answer for this question was already submitted.",
                    "answer_id": existing_ans.id,
                    "idempotency_key": idempotency_key,
                    "evaluation": eval_resp.model_dump() if eval_resp else None,
                    "next_action": existing_ans.evaluation.recommended_next_action if existing_ans.evaluation else "next_question"
                }
                IdempotencyService.complete_idempotent_operation(db, idempotency_key, 200, response_data)
                return response_data, 200

            # 4. PERSIST ANSWER BEFORE EVALUATION (Requirement!)
            answer = Answer(
                interview_id=interview.id,
                question_id=request.question_id,
                transcript_text=request.transcript_text,
                idempotency_key=idempotency_key,
                audio_metadata=request.audio_metadata
            )
            db.add(answer)
            db.flush()

            # Emit conversation event
            db.add(ConversationEvent(
                interview_id=interview.id,
                event_type="answer_submitted",
                payload={"answer_id": answer.id, "question_id": request.question_id, "length": len(request.transcript_text)}
            ))
            # Increment interview concurrency version
            interview.version += 1
            db.commit()
            db.refresh(answer)

            # 5. Trigger LLM Evaluation
            evaluation, eval_success = await EvaluationService.evaluate_answer(
                db=db,
                answer=answer,
                interview=interview,
                simulation_mode=simulation_mode
            )

            # Emit evaluation event
            db.add(ConversationEvent(
                interview_id=interview.id,
                event_type="evaluation_completed" if eval_success else "evaluation_failed",
                payload={
                    "evaluation_id": evaluation.id,
                    "status": evaluation.status,
                    "scores": evaluation.scores,
                    "error": evaluation.error_message
                }
            ))
            db.commit()

            # Next step decision
            next_action = evaluation.recommended_next_action or "next_question"
            if not eval_success:
                next_action = "retry_evaluation"

            response_data = {
                "status": "success" if eval_success else "evaluation_failed",
                "message": "Answer persisted and evaluated." if eval_success else "Answer persisted, but evaluation timed out or failed. Can be retried.",
                "answer_id": answer.id,
                "idempotency_key": idempotency_key,
                "evaluation": EvaluationResponse.model_validate(evaluation).model_dump(),
                "next_action": next_action
            }

            # 6. Save in Idempotency Store
            IdempotencyService.complete_idempotent_operation(db, idempotency_key, 200, response_data)
            return response_data, 200

        except HTTPException:
            IdempotencyService.release_lock_on_error(db, idempotency_key)
            raise
        except Exception as exc:
            IdempotencyService.release_lock_on_error(db, idempotency_key)
            logger.error(f"Error processing answer submission: {exc}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process answer submission: {str(exc)}"
            )

    @staticmethod
    def reopen_interview(db: Session, interview_id: str, current_user: CurrentUser) -> Interview:
        """Explicitly reopen a completed interview (Recruiter action)."""
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

        InterviewService._verify_interview_access(interview, current_user, allow_candidate=False)

        interview.status = "in_progress"
        interview.completed_at = None
        db.add(ConversationEvent(
            interview_id=interview.id,
            event_type="interview_resumed",
            payload={"reopened_by": current_user.id}
        ))
        db.commit()
        db.refresh(interview)
        logger.info(f"Interview {interview_id} reopened by recruiter {current_user.id}")
        return interview
