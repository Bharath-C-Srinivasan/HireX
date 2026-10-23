"""Idempotency service to guarantee exactly-once processing of answer submissions."""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.models.entities import IdempotencyRecord


class IdempotencyService:
    """Manages idempotency locking, validation, and cached response replay."""

    @staticmethod
    def compute_request_hash(payload: Any) -> str:
        """Create SHA-256 hash of request payload for validation."""
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    @staticmethod
    def start_idempotent_operation(
        db: Session,
        idempotency_key: str,
        resource_type: str,
        request_payload: Any
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Check if an operation with this idempotency key has already started or completed.
        Returns:
            (is_cached, cached_body, cached_status_code)
        Raises:
            HTTPException 409 if a concurrent execution with same key is currently locked.
        """
        now = datetime.now(timezone.utc)
        request_hash = IdempotencyService.compute_request_hash(request_payload)

        # Check existing record
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == idempotency_key
        ).first()

        if record:
            # 1. Previously completed operation -> Return cached result
            if record.status_code is not None and record.response_body is not None:
                logger.info(f"Idempotency HIT for key {idempotency_key}")
                return True, json.loads(record.response_body), record.status_code

            # 2. In-flight operation under lock -> Concurrency conflict
            if record.locked_until and record.locked_until > now:
                logger.warning(f"Concurrent request detected for idempotency key {idempotency_key}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A request with this idempotency key is currently being processed. Please retry shortly."
                )

            # 3. Lock expired or previous attempt failed -> Reacquire lock
            record.locked_until = now + timedelta(seconds=settings.IDEMPOTENCY_LOCK_SECONDS)
            record.request_hash = request_hash
            db.commit()
            return False, None, None

        # Create new idempotency lock record
        new_record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            resource_type=resource_type,
            request_hash=request_hash,
            locked_until=now + timedelta(seconds=settings.IDEMPOTENCY_LOCK_SECONDS),
        )
        db.add(new_record)
        try:
            db.commit()
        except Exception:
            db.rollback()
            # If concurrent insert raced, fetch it
            record = db.query(IdempotencyRecord).filter(
                IdempotencyRecord.idempotency_key == idempotency_key
            ).first()
            if record and record.status_code is not None:
                return True, json.loads(record.response_body), record.status_code
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent submission detected."
            )

        return False, None, None

    @staticmethod
    def complete_idempotent_operation(
        db: Session,
        idempotency_key: str,
        status_code: int,
        response_body: Dict[str, Any]
    ) -> None:
        """Store the final response for an idempotent operation."""
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == idempotency_key
        ).first()
        if record:
            record.status_code = status_code
            record.response_body = json.dumps(response_body, default=str)
            record.locked_until = None
            db.commit()

    @staticmethod
    def release_lock_on_error(db: Session, idempotency_key: str) -> None:
        """Release lock if an unhandled error occurred during processing."""
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == idempotency_key
        ).first()
        if record and record.status_code is None:
            db.delete(record)
            db.commit()
