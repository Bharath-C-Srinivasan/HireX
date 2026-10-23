"""Enumerations for HIREX domain."""

from enum import Enum


class UserRole(str, Enum):
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"
    ADMIN = "admin"


class InterviewStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    PROBLEM_SOLVING = "problem_solving"
    FOLLOW_UP = "follow_up"


class EventType(str, Enum):
    INTERVIEW_CREATED = "interview_created"
    INTERVIEW_STARTED = "interview_started"
    QUESTION_SERVED = "question_served"
    ANSWER_SUBMITTED = "answer_submitted"
    EVALUATION_SCHEDULED = "evaluation_scheduled"
    EVALUATION_COMPLETED = "evaluation_completed"
    EVALUATION_FAILED = "evaluation_failed"
    FOLLOW_UP_TRIGGERED = "follow_up_triggered"
    INTERVIEW_COMPLETED = "interview_completed"
    INTERVIEW_RESUMED = "interview_resumed"
    LIVEKIT_SESSION_INITIALIZED = "livekit_session_initialized"
    LIVEKIT_WEBHOOK_EVENT = "livekit_webhook_event"


class NextAction(str, Enum):
    FOLLOW_UP = "follow_up"
    NEXT_COMPETENCY = "next_competency"
    COMPLETE = "complete"
