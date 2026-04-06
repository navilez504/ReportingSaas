from typing import Annotated, Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.api_messages import api_msg, parse_accept_language
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.db import SessionLocal

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_locale(request: Request) -> str:
    """BCP 47 / Accept-Language → 'en' | 'es' for API messages."""
    return parse_accept_language(request.headers.get("accept-language"))


def get_current_user_id(
    request: Request,
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> int:
    lang = parse_accept_language(request.headers.get("accept-language"))
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_msg("not_authenticated", lang),
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str = decode_token(creds.credentials)
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_msg("invalid_or_expired_token", lang),
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_msg("invalid_token_subject", lang),
        )
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_msg("user_not_found", lang),
        )
    return user_id


def get_current_user(
    request: Request,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    lang = parse_accept_language(request.headers.get("accept-language"))
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_msg("user_not_found", lang),
        )
    return user


def require_admin(
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
) -> User:
    lang = parse_accept_language(request.headers.get("accept-language"))
    if current.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_msg("admin_role_required", lang),
        )
    return current
