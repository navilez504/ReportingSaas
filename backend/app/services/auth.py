from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.api_messages import api_msg
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserOut


class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register(self, data: RegisterRequest, lang: str = "en") -> tuple[UserOut, str]:
        if self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_msg("email_already_registered", lang),
            )
        count = self.repo.db.query(User).count()
        role = UserRole.ADMIN if count == 0 else UserRole.USER
        try:
            user = self.repo.create(
                email=str(data.email),
                hashed_password=hash_password(data.password),
                full_name=data.full_name,
                role_value=role.value,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_msg("email_already_registered", lang),
            ) from None
        token = create_access_token(user.id)
        return UserOut.model_validate(user), token

    def login(self, data: LoginRequest, lang: str = "en") -> tuple[UserOut, str]:
        user = self.repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=api_msg("incorrect_email_or_password", lang),
            )
        token = create_access_token(user.id)
        return UserOut.model_validate(user), token
