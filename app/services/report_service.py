"""Service for generating comprehensive Recruiter Reports."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.entities import Interview, Competency, Answer, Evaluation, Question
from app.schemas.report import (
    RecruiterReportResponse,
    CompetencyReportItem,
    QuestionEvaluationItem,
)
from app.core.security import CurrentUser
from app.core.logging import logger


class ReportService:
    """Generates structured recruiter evaluation reports from persisted data."""

    @staticmethod
    def generate_report(
        db: Session,
        interview_id: str,
        current_user: CurrentUser
    ) -> RecruiterReportResponse:
        """
        Generate authorized recruiter report.
        Security: Candidates are strictly FORBIDDEN from viewing reports (403).
        Resource ownership: Recruiter's organization must match assessment's organization.
        """
        # Strict RBAC: Recruiters & Admins ONLY
        if current_user.role not in ["recruiter", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only authorized recruiters may access candidate evaluation reports."
            )

        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

        # Organization boundary check
        if current_user.organization_id and interview.assessment:
            if interview.assessment.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot view reports outside your organization."
                )

        assessment = interview.assessment
        candidate = interview.candidate

        # Gather all answers and evaluations
        answers = db.query(Answer).filter(Answer.interview_id == interview.id).order_by(Answer.submitted_at).all()
        
        question_eval_items: List[QuestionEvaluationItem] = []
        competency_scores_map: Dict[str, List[float]] = {}
        competency_evidence_map: Dict[str, List[str]] = {}
        successful_evals = 0
        failed_evals = 0

        for ans in answers:
            q = ans.question
            ev = ans.evaluation
            
            comp_name = q.competency.name if (q and q.competency) else "General"
            comp_id = q.competency_id if q else "general"

            if ev and ev.status == "completed":
                successful_evals += 1
                scores_dict = ev.scores or {}
                evidence_list = ev.evidence or []
                rationale_text = ev.rationale
                eval_status = "completed"
                score_val = ev.overall_score

                if comp_id not in competency_scores_map:
                    competency_scores_map[comp_id] = []
                    competency_evidence_map[comp_id] = []

                if score_val is not None:
                    competency_scores_map[comp_id].append(score_val)
                competency_evidence_map[comp_id].extend(evidence_list)
            else:
                failed_evals += 1
                scores_dict = {}
                evidence_list = []
                rationale_text = ev.error_message if ev else "Evaluation pending or not executed"
                eval_status = ev.status if ev else "missing"
                score_val = None

            question_eval_items.append(
                QuestionEvaluationItem(
                    question_id=ans.question_id,
                    prompt=q.prompt if q else "Unknown question",
                    competency_name=comp_name,
                    is_follow_up=q.is_follow_up if q else False,
                    follow_up_topic=q.follow_up_topic if q else None,
                    candidate_answer=ans.transcript_text,
                    scores=scores_dict,
                    overall_score=score_val,
                    evidence=evidence_list,
                    rationale=rationale_text,
                    evaluation_status=eval_status,
                    submitted_at=ans.submitted_at
                )
            )

        # Build competency report breakdown
        competency_items: List[CompetencyReportItem] = []
        all_comp_scores: List[float] = []

        if assessment and assessment.competencies:
            for comp in assessment.competencies:
                scores = competency_scores_map.get(comp.id, [])
                avg = round(sum(scores) / len(scores), 2) if scores else None
                if avg is not None:
                    all_comp_scores.append(avg)

                competency_items.append(
                    CompetencyReportItem(
                        competency_id=comp.id,
                        competency_name=comp.name,
                        weight=comp.weight,
                        average_score=avg,
                        questions_evaluated=len(scores),
                        rubric_criteria=comp.rubric.criteria if comp.rubric else None,
                        key_evidence=competency_evidence_map.get(comp.id, [])[:5],
                        summary_notes=f"Evaluated across {len(scores)} questions with weight {comp.weight}."
                    )
                )

        # Compute overall score and recommendation
        if all_comp_scores:
            overall_score = round(sum(all_comp_scores) / len(all_comp_scores), 2)
        elif interview.summary_score:
            overall_score = interview.summary_score
        else:
            overall_score = None

        if overall_score is not None:
            if overall_score >= 4.0:
                rec = "Strong Hire"
                rec_summary = "Candidate exceeded rubric expectations with robust evidence of technical depth."
            elif overall_score >= 3.2:
                rec = "Hire"
                rec_summary = "Candidate met rubric expectations and demonstrated sound problem-solving."
            elif overall_score >= 2.5:
                rec = "Lean Hire"
                rec_summary = "Candidate met some criteria but exhibited gaps in data integrity or edge-case handling."
            else:
                rec = "No Hire"
                rec_summary = "Candidate did not meet basic rubric thresholds for the intern role."
        else:
            rec = "Pending Evaluation"
            rec_summary = "Interview has incomplete evaluations."

        # Calculate duration if timestamps exist
        duration_sec = None
        if interview.started_at and interview.completed_at:
            duration_sec = int((interview.completed_at - interview.started_at).total_seconds())

        adapter_version = "hirex-adapter-v1.2.0"
        if answers and answers[0].evaluation:
            adapter_version = answers[0].evaluation.adapter_version

        report = RecruiterReportResponse(
            interview_id=interview.id,
            status=interview.status,
            candidate_id=candidate.id if candidate else "unknown",
            candidate_name=candidate.full_name if candidate else "Unknown Candidate",
            candidate_email=candidate.email if candidate else "",
            assessment_id=assessment.id if assessment else "",
            assessment_title=assessment.title if assessment else "",
            role=assessment.role if assessment else "",
            overall_score=overall_score,
            recommendation=rec,
            recommendation_summary=rec_summary,
            started_at=interview.started_at,
            completed_at=interview.completed_at,
            duration_seconds=duration_sec,
            competency_breakdown=competency_items,
            question_evaluations=question_eval_items,
            rubric_version=assessment.scoring_rubric_version if assessment else "v1.0.0",
            adapter_version=adapter_version,
            total_answers=len(answers),
            successful_evaluations=successful_evals,
            failed_evaluations=failed_evals,
            generated_at=datetime.now(timezone.utc)
        )

        logger.info(f"Generated recruiter report for interview {interview_id}. Overall score: {overall_score}")
        return report
