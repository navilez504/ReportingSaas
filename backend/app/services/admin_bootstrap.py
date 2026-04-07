"""Grant admin role to emails listed in settings ADMIN_EMAILS."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


def promote_configured_admins_on_startup(db, settings: Settings) -> None:
    """Set role=admin in DB for every user whose email is in ADMIN_EMAILS."""
    emails = settings.admin_emails_lower
    if not emails:
        return
    changed = False
    for u in db.query(User).filter(User.email.in_(emails)).all():
        if u.role != UserRole.ADMIN.value:
            u.role = UserRole.ADMIN.value
            changed = True
    if changed:
        db.commit()
        logger.info("Admin role applied from ADMIN_EMAILS configuration")


def ensure_config_admin_user(user: User, repo: UserRepository, settings: Settings) -> User:
    """If the account is listed in ADMIN_EMAILS, ensure role is admin (e.g. after login or GET /me)."""
    if not settings.admin_emails_lower:
        return user
    if user.email.lower() not in settings.admin_emails_lower:
        return user
    if user.role == UserRole.ADMIN.value:
        return user
    user.role = UserRole.ADMIN.value
    return repo.save(user)
