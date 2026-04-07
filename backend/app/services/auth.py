import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.api_messages import api_msg
from app.core.config import get_settings
from app.models.user import UserRole
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.services.admin_bootstrap import ensure_config_admin_user
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserOut
from app.services.system_notifications import notify_new_registration

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register(
        self,
        data: RegisterRequest,
        *,
        ip_address: str = "",
        user_agent: str = "",
        lang: str = "en",
    ) -> tuple[UserOut, str]:
        if self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_msg("email_already_registered", lang),
            )
        settings = get_settings()
        email_lower = str(data.email).strip().lower()
        in_admin_list = email_lower in settings.admin_emails_lower
        # Admins are only whoever you list in ADMIN_EMAILS (not “first registrant”).
        role = UserRole.ADMIN if in_admin_list else UserRole.USER
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
        try:
            notify_new_registration(settings, user)
        except Exception:
            logger.exception("Registration notifications failed for %s", user.email)
        token, jti, expires_at = create_access_token(user.id)
        UserSessionRepository(self.repo.db).create(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return UserOut.model_validate(user), token

    def login(
        self,
        data: LoginRequest,
        *,
        ip_address: str = "",
        user_agent: str = "",
        lang: str = "en",
    ) -> tuple[UserOut, str]:
        user = self.repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=api_msg("incorrect_email_or_password", lang),
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=api_msg("account_deactivated", lang),
            )
        user = ensure_config_admin_user(user, self.repo, get_settings())
        token, jti, expires_at = create_access_token(user.id)
        UserSessionRepository(self.repo.db).create(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return UserOut.model_validate(user), token
