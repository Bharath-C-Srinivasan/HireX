"""Test 10: LiveKit adapter, token generation, webhook HMAC signature, and replay protection."""

import time
import json
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.models.entities import Interview


def test_livekit_token_generation(
    client: TestClient,
    sample_interview: Interview,
    candidate_1_token: str
):
    """Candidate can obtain a valid signed LiveKit room token."""
    res = client.post(
        f"/api/v1/interviews/{sample_interview.id}/livekit-token",
        headers={"Authorization": f"Bearer {candidate_1_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert f"hirex-interview-{sample_interview.id}" == data["room_name"]
    assert data["participant_identity"] == sample_interview.candidate_id


def test_livekit_webhook_valid_signature_accepted(client: TestClient):
    """Webhook with authentic HMAC-SHA256 signature is accepted."""
    now_ts = str(int(time.time()))
    payload = {
        "event": "participant_joined",
        "room": {"name": "hirex-interview-demo"},
        "participant": {"identity": "cand_123", "name": "Candidate"}
    }
    body_bytes = json.dumps(payload).encode("utf-8")

    # Generate valid signature
    signed_payload = f"{now_ts}.".encode("utf-8") + body_bytes
    valid_sig = hmac.new(
        settings.LIVEKIT_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "LiveKit-Signature": valid_sig,
        "LiveKit-Timestamp": now_ts,
        "Content-Type": "application/json"
    }
    res = client.post("/api/v1/integrations/livekit/webhook", content=body_bytes, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "processed"


def test_livekit_webhook_invalid_signature_rejected(client: TestClient):
    """Webhook with tampered signature is rejected with 401."""
    now_ts = str(int(time.time()))
    body_bytes = b'{"event": "participant_joined"}'
    headers = {
        "LiveKit-Signature": "tampered_invalid_signature_hex_12345",
        "LiveKit-Timestamp": now_ts,
        "Content-Type": "application/json"
    }
    res = client.post("/api/v1/integrations/livekit/webhook", content=body_bytes, headers=headers)
    assert res.status_code == 401
    assert "Invalid webhook signature" in res.json()["detail"]


def test_livekit_webhook_replay_attack_rejected(client: TestClient):
    """Webhook with expired timestamp (> 300s old) is rejected to prevent replay attacks."""
    expired_ts = str(int(time.time()) - 600)  # 10 minutes ago
    body_bytes = b'{"event": "participant_joined"}'
    signed_payload = f"{expired_ts}.".encode("utf-8") + body_bytes
    valid_sig_for_old_ts = hmac.new(
        settings.LIVEKIT_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "LiveKit-Signature": valid_sig_for_old_ts,
        "LiveKit-Timestamp": expired_ts,
        "Content-Type": "application/json"
    }
    res = client.post("/api/v1/integrations/livekit/webhook", content=body_bytes, headers=headers)
    assert res.status_code == 401
    assert "replay attack" in res.json()["detail"].lower()
