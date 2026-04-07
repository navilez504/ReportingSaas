from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_locale
from app.core.security import decode_access_payload
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth import AuthService
from app.utils.http import client_ip, user_agent_string

router = APIRouter(prefix="/auth", tags=["auth"])

_logout_bearer = HTTPBearer()


@router.post("/register", response_model=AuthResponse)
def register(
    request: Request,
    data: RegisterRequest,
    lang: str = Depends(get_locale),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    svc = AuthService(repo)
    user, token = svc.register(
        data,
        ip_address=client_ip(request),
        user_agent=user_agent_string(request),
        lang=lang,
    )
    return AuthResponse(access_token=token, token_type="bearer", user=user)


@router.post("/login", response_model=AuthResponse)
def login(
    request: Request,
    data: LoginRequest,
    lang: str = Depends(get_locale),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    svc = AuthService(repo)
    user, token = svc.login(
        data,
        ip_address=client_ip(request),
        user_agent=user_agent_string(request),
        lang=lang,
    )
    return AuthResponse(access_token=token, token_type="bearer", user=user)


@router.post("/logout")
def logout(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_logout_bearer)],
    db: Session = Depends(get_db),
):
    payload = decode_access_payload(creds.credentials)
    jti = payload.get("jti") if payload else None
    if jti:
        sess_repo = UserSessionRepository(db)
        row = sess_repo.get_by_jti(str(jti))
        if row:
            sess_repo.revoke(row)
    return {"ok": True}
