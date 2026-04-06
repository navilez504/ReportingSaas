from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_locale
from app.repositories.user import UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(
    data: RegisterRequest,
    lang: str = Depends(get_locale),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    svc = AuthService(repo)
    user, token = svc.register(data, lang=lang)
    return AuthResponse(access_token=token, token_type="bearer", user=user)


@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    lang: str = Depends(get_locale),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    svc = AuthService(repo)
    user, token = svc.login(data, lang=lang)
    return AuthResponse(access_token=token, token_type="bearer", user=user)
