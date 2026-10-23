"""API v1 router assembly."""

from fastapi import APIRouter

from app.api.v1.assessments import router as assessments_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.auth import router as auth_router

api_router = APIRouter()

api_router.include_router(assessments_router)
api_router.include_router(candidates_router)
api_router.include_router(interviews_router)
api_router.include_router(integrations_router)
api_router.include_router(auth_router)
