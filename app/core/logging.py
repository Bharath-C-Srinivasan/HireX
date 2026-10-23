"""Structured logging with request correlation and secret masking."""

import json
import logging
import sys
import contextvars
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable for request correlation ID
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="system"
)

SENSITIVE_KEYS = {
    "authorization", "token", "password", "secret", "api_key",
    "secret_key", "livekit_api_secret", "openai_api_key"
}


def mask_sensitive_data(data: Any) -> Any:
    """Recursively mask sensitive values in dicts/lists/strings."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                masked[k] = "******"
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as JSON with correlation ID and ISO timestamp."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": correlation_id_ctx.get(),
        }
        if hasattr(record, "extra_data"):
            log_entry["data"] = mask_sensitive_data(record.extra_data)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def get_logger(name: str = "hirex") -> logging.Logger:
    """Return a configured structured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = get_logger("hirex")
