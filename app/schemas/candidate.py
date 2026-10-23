"""Pydantic schemas for Candidate Registration."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CandidateCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2)
    resume_text: Optional[str] = None
    organization_id: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class CandidateResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    full_name: str
    resume_text: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
