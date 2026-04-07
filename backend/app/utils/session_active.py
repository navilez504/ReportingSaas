"""Helpers for interpreting server-side session rows."""

from datetime import datetime, timezone

from app.models.user_session import UserSession


def session_row_is_active(row: UserSession) -> bool:
    if row.revoked_at is not None:
        return False
    now = datetime.now(timezone.utc)
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > now
