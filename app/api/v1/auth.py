"""Auth router for issuing JWT tokens."""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenRequest(BaseModel):
    user_id: str
    email: EmailStr
    role: str  # 'recruiter', 'candidate', 'admin'
    organization_id: Optional[str] = None
    candidate_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


@router.post("/token", response_model=TokenResponse, summary="Mint a signed JWT token")
def mint_token(payload: TokenRequest):
    token = create_access_token({
        "sub": payload.user_id,
        "email": payload.email,
        "role": payload.role,
        "org_id": payload.organization_id,
        "candidate_id": payload.candidate_id or payload.user_id,
    })
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=payload.role,
        user_id=payload.user_id
    )
