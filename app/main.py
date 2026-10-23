"""HIREX FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import logger
from app.core.middleware import CorrelationIdMiddleware
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info(f"{settings.PROJECT_NAME} startup complete.")
    yield
    logger.info(f"{settings.PROJECT_NAME} shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade AI Interview Workflow & Evaluation API with adaptive questions, idempotency, and recruiter reporting.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Correlation ID and Structured Logging Middleware
app.add_middleware(CorrelationIdMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "adapter_version": settings.LLM_ADAPTER_VERSION
    }
