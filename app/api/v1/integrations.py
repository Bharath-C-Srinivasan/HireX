"""Integrations API router for LiveKit webhooks and external services."""

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.livekit_service import LiveKitService

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post(
    "/livekit/webhook",
    status_code=status.HTTP_200_OK,
    summary="LiveKit Webhook Receiver with HMAC-SHA256 signature and replay protection"
)
async def livekit_webhook(
    request: Request,
    db: Session = Depends(get_db),
    livekit_signature: str = Header(..., alias="LiveKit-Signature"),
    livekit_timestamp: str = Header(..., alias="LiveKit-Timestamp"),
):
    body_bytes = await request.body()
    # 1. Verify HMAC-SHA256 and replay window
    LiveKitService.verify_webhook_signature(
        body_bytes=body_bytes,
        signature_header=livekit_signature,
        timestamp_str=livekit_timestamp
    )

    # 2. Ingest payload
    payload = await request.json()
    result = LiveKitService.process_webhook_event(db, payload)
    return result
