"""Pydantic schemas for LiveKit Integration and Webhooks."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class LiveKitTokenRequest(BaseModel):
    identity: Optional[str] = Field(None, description="Participant identity, defaults to candidate ID")
    name: Optional[str] = Field(None, description="Participant display name")


class LiveKitTokenResponse(BaseModel):
    token: str
    room_name: str
    server_url: str
    participant_identity: str
    participant_name: str
    expires_in_seconds: int


class LiveKitWebhookPayload(BaseModel):
    id: Optional[str] = None
    event: str  # participant_joined, participant_left, room_started, room_finished, track_published
    created_at: Optional[int] = None
    room: Optional[Dict[str, Any]] = None
    participant: Optional[Dict[str, Any]] = None
    track: Optional[Dict[str, Any]] = None
