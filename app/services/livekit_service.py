"""LiveKit Audio & Video Session Adapter with Webhook Signature and Replay Attack Protection."""

import hmac
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
import jwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.models.entities import Interview, ConversationEvent


class LiveKitService:
    """Manages LiveKit room token generation and cryptographically verified webhook ingestion."""

    @staticmethod
    def generate_join_token(
        interview_id: str,
        participant_identity: str,
        participant_name: str,
        ttl_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate a cryptographically signed LiveKit Room Join Token (JWT).
        Provides video/audio grants for the interview room.
        """
        now = datetime.now(timezone.utc)
        room_name = f"hirex-interview-{interview_id}"

        payload = {
            "sub": participant_identity,
            "name": participant_name,
            "iss": settings.LIVEKIT_API_KEY,
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
            "video": {
                "room": room_name,
                "roomJoin": True,
                "canPublish": True,
                "canSubscribe": True,
                "canPublishData": True,
            },
            "metadata": {
                "interview_id": interview_id,
                "app": "HIREX"
            }
        }

        token = jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")
        
        return {
            "token": token,
            "room_name": room_name,
            "server_url": "wss://livekit.hirex.ai",
            "participant_identity": participant_identity,
            "participant_name": participant_name,
            "expires_in_seconds": ttl_seconds
        }

    @staticmethod
    def verify_webhook_signature(
        body_bytes: bytes,
        signature_header: str,
        timestamp_str: str,
        tolerance_seconds: int = 300
    ) -> bool:
        """
        Verify incoming LiveKit webhook HMAC-SHA256 signature and prevent replay attacks.
        Checks:
        1. Timestamp freshness within tolerance (default 5 minutes).
        2. Constant-time HMAC-SHA256 comparison against webhook secret.
        """
        if not signature_header or not timestamp_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature or timestamp headers."
            )

        # 1. Replay Attack Protection: verify timestamp within tolerance
        try:
            timestamp = int(timestamp_str)
            now = int(time.time())
            if abs(now - timestamp) > tolerance_seconds:
                logger.warning(f"LiveKit webhook replay attack rejected: timestamp delta {abs(now - timestamp)}s > {tolerance_seconds}s")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Webhook timestamp outside valid window. Possible replay attack."
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp header format."
            )

        # 2. Signature verification
        # LiveKit signature format: HMAC_SHA256(secret, timestamp + "." + body)
        signed_payload = f"{timestamp_str}.".encode("utf-8") + body_bytes
        expected_sig = hmac.new(
            settings.LIVEKIT_WEBHOOK_SECRET.encode("utf-8"),
            signed_payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature_header):
            logger.warning("Invalid LiveKit webhook HMAC signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature."
            )

        return True

    @staticmethod
    def process_webhook_event(db, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Record room and audio track events to interview event history."""
        event_type = payload.get("event", "unknown")
        room = payload.get("room", {})
        room_name = room.get("name", "")
        
        # Parse interview_id from room name: 'hirex-interview-<interview_id>'
        interview_id = None
        if room_name.startswith("hirex-interview-"):
            interview_id = room_name.replace("hirex-interview-", "")

        if interview_id:
            interview = db.query(Interview).filter(Interview.id == interview_id).first()
            if interview:
                db.add(ConversationEvent(
                    interview_id=interview.id,
                    event_type=f"livekit_{event_type}",
                    payload=payload
                ))
                db.commit()
                logger.info(f"Recorded LiveKit event '{event_type}' for interview {interview_id}")

        return {"status": "processed", "event": event_type}
