from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user_session import UserSession


class UserSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        jti: str,
        expires_at: datetime,
        ip_address: str,
        user_agent: str,
    ) -> UserSession:
        now = datetime.now(timezone.utc)
        row = UserSession(
            user_id=user_id,
            jti=jti,
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
            ip_address=ip_address or "",
            user_agent=user_agent or "",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_jti(self, jti: str) -> UserSession | None:
        return self.db.query(UserSession).filter(UserSession.jti == jti).first()

    def touch_if_stale(self, row: UserSession, *, min_interval_seconds: int = 60) -> None:
        now = datetime.now(timezone.utc)
        ls = row.last_seen_at
        if ls.tzinfo is None:
            ls = ls.replace(tzinfo=timezone.utc)
        if (now - ls).total_seconds() >= min_interval_seconds:
            row.last_seen_at = now
            self.db.commit()

    def revoke(self, row: UserSession) -> None:
        now = datetime.now(timezone.utc)
        row.revoked_at = now
        self.db.commit()

    def revoke_by_id(self, session_id: int) -> UserSession | None:
        row = self.db.query(UserSession).filter(UserSession.id == session_id).first()
        if row:
            self.revoke(row)
        return row

    def revoke_all_for_user(self, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        n = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .update({UserSession.revoked_at: now}, synchronize_session=False)
        )
        self.db.commit()
        return int(n)

    def list_for_admin(
        self,
        *,
        user_id: int | None,
        active_only: bool,
        skip: int,
        limit: int,
    ) -> list[tuple[UserSession, str]]:
        """Returns (session, user_email) rows."""
        from app.models.user import User

        q = self.db.query(UserSession, User.email).join(User, User.id == UserSession.user_id)
        if user_id is not None:
            q = q.filter(UserSession.user_id == user_id)
        if active_only:
            now = datetime.now(timezone.utc)
            q = q.filter(UserSession.revoked_at.is_(None), UserSession.expires_at > now)
        q = q.order_by(UserSession.last_seen_at.desc())
        rows = q.offset(skip).limit(limit).all()
        return [(s, email) for s, email in rows]
