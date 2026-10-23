"""Evaluation Service for executing LLM evaluations with retry, failure recovery, and scoring."""

import time
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import logger
from app.models.entities import Answer, Evaluation, Interview, Question, Competency, ScoringRubric
from app.schemas.llm import LLMEvaluationPayload, LLMEvaluationResult
from app.services.llm.adapter import get_llm_adapter
from app.services.llm.exceptions import (
    LLMTimeoutError,
    LLMMalformedOutputError,
    LLMAdapterError,
)


class EvaluationService:
    """Orchestrates LLM evaluation, retries, and persistence with resilient error handling."""

    @staticmethod
    async def evaluate_answer(
        db: Session,
        answer: Answer,
        interview: Interview,
        simulation_mode: Optional[str] = None
    ) -> Tuple[Evaluation, bool]:
        """
        Evaluate an answer using the LLM adapter.
        Handles timeout and malformed responses safely:
        - If timeout or error occurs: records an evaluation with status='failed' and error_message.
        - Leaves the interview in a recoverable state (does NOT mark interview as completed).
        Returns:
            (Evaluation, success_boolean)
        """
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        competency = None
        rubric_criteria = "Evaluate answer based on clarity, correctness, and technical depth."
        
        if question and question.competency_id:
            competency = db.query(Competency).filter(Competency.id == question.competency_id).first()
            if competency and competency.rubric:
                rubric_criteria = competency.rubric.criteria

        payload = LLMEvaluationPayload(
            assessment_role=interview.assessment.role if interview.assessment else "Software Engineer",
            competency_name=competency.name if competency else "General Engineering",
            competency_description=competency.description if competency else None,
            scoring_criteria=rubric_criteria,
            question_prompt=question.prompt if question else "Technical question",
            candidate_answer=answer.transcript_text,
            previous_follow_up_topic=question.follow_up_topic if question else None
        )

        adapter = get_llm_adapter()
        start_time = time.perf_counter()
        
        # Check if an evaluation record already exists for this answer
        eval_record = db.query(Evaluation).filter(Evaluation.answer_id == answer.id).first()
        if not eval_record:
            eval_record = Evaluation(
                answer_id=answer.id,
                interview_id=interview.id,
                status="in_progress",
                adapter_version=adapter.version,
            )
            db.add(eval_record)
            db.commit()
            db.refresh(eval_record)

        # Attempt evaluation with retries
        max_retries = settings.LLM_MAX_RETRIES
        last_error = None
        result: Optional[LLMEvaluationResult] = None

        for attempt in range(max_retries + 1):
            try:
                result = await adapter.evaluate_answer(payload, simulation_mode=simulation_mode)
                break
            except LLMTimeoutError as exc:
                last_error = f"Timeout: {str(exc)}"
                logger.warning(f"Evaluation timeout on attempt {attempt + 1}: {exc}")
                if attempt == max_retries:
                    break
            except (LLMMalformedOutputError, ValueError) as exc:
                last_error = f"MalformedOutput: {str(exc)}"
                logger.warning(f"Evaluation malformed output on attempt {attempt + 1}: {exc}")
                if attempt == max_retries:
                    break
            except Exception as exc:
                last_error = f"UnexpectedError: {str(exc)}"
                logger.error(f"Unexpected evaluation error on attempt {attempt + 1}: {exc}")
                break

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Handle failure state safely
        if result is None:
            eval_record.status = "failed"
            eval_record.error_message = last_error or "Unknown evaluation failure"
            eval_record.latency_ms = latency_ms
            db.commit()
            db.refresh(eval_record)
            logger.error(f"Evaluation failed for answer {answer.id}. Interview left in recoverable state.")
            return eval_record, False

        # Success: persist structured scores and rationale
        scores = result.scores
        overall_score = round(sum(scores.values()) / max(len(scores), 1), 2)

        eval_record.status = "completed"
        eval_record.scores = scores
        eval_record.overall_score = overall_score
        eval_record.evidence = result.evidence
        eval_record.rationale = result.rationale
        eval_record.follow_up_needed = result.follow_up_needed
        eval_record.follow_up_topic = result.follow_up_topic
        eval_record.recommended_next_action = result.recommended_next_action
        eval_record.latency_ms = latency_ms
        eval_record.error_message = None

        db.commit()
        db.refresh(eval_record)
        logger.info(f"Evaluation {eval_record.id} completed successfully with score {overall_score}")
        return eval_record, True
