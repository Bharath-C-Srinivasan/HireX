"""Middleware for Request Correlation, Structured Logging, and Safe Error Handling."""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import logger, correlation_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request correlation ID and logs execution stats."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check client-supplied request ID or generate UUIDv4
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = correlation_id_ctx.set(request_id)
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # Set response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = str(process_time_ms)
            
            logger.info(
                f"{request.method} {request.url.path} completed with {response.status_code} in {process_time_ms}ms"
            )
            return response
            
        except Exception as exc:
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled exception during {request.method} {request.url.path}: {str(exc)}",
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected server error occurred. Please contact support with the request ID.",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )
        finally:
            correlation_id_ctx.reset(token)
