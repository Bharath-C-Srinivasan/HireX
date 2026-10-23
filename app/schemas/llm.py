"""Pydantic schemas for LLM adapter inputs and validated outputs."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class LLMEvaluationPayload(BaseModel):
    """Payload provided to LLM for evaluating an answer."""
    assessment_role: str
    competency_name: str
    competency_description: Optional[str] = None
    scoring_criteria: str
    question_prompt: str
    candidate_answer: str
    previous_follow_up_topic: Optional[str] = None


class LLMEvaluationResult(BaseModel):
    """
    Validated structured evaluation returned by LLM adapter.
    Enforces score bounds (1-5), evidence extraction, and recommendation.
    """
    scores: Dict[str, int] = Field(
        ...,
        description="Dictionary mapping competency or sub-criteria names to integer scores (1-5)"
    )
    evidence: List[str] = Field(
        ...,
        description="Verbatim or near-verbatim quotes from the candidate answer demonstrating knowledge or gaps"
    )
    rationale: str = Field(
        ...,
        min_length=10,
        description="Detailed explanation of the score according to rubric criteria"
    )
    follow_up_needed: bool = Field(
        default=False,
        description="Whether an adaptive follow-up is necessary to probe an ambiguous area"
    )
    follow_up_topic: Optional[str] = Field(
        default=None,
        description="Specific topic for follow-up question if follow_up_needed is true"
    )
    recommended_next_action: str = Field(
        default="next_competency",
        description="One of: 'follow_up', 'next_competency', 'complete'"
    )

    @field_validator("scores")
    @classmethod
    def validate_scores_bounds(cls, v: Dict[str, int]) -> Dict[str, int]:
        if not v:
            raise ValueError("Scores dictionary cannot be empty.")
        for criterion, score in v.items():
            if not isinstance(score, int) or score < 1 or score > 5:
                raise ValueError(f"Score for '{criterion}' must be an integer between 1 and 5. Got: {score}")
        return v

    @field_validator("evidence")
    @classmethod
    def validate_evidence(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one piece of evidence is required.")
        return [item.strip() for item in v if item and item.strip()]
