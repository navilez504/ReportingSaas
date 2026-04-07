from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        *,
        actor_user_id: int | None,
        action: str,
        resource_type: str | None,
        resource_id: str | None,
        details: dict[str, Any] | None,
        ip_address: str,
        user_agent: str,
    ) -> AuditLog:
        row = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address or "",
            user_agent=user_agent or "",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_for_admin(
        self,
        *,
        actor_id: int | None,
        action_prefix: str | None,
        skip: int,
        limit: int,
    ) -> list[tuple[AuditLog, str | None]]:
        q = self.db.query(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_user_id)
        if actor_id is not None:
            q = q.filter(AuditLog.actor_user_id == actor_id)
        if action_prefix:
            q = q.filter(AuditLog.action.startswith(action_prefix))
        q = q.order_by(AuditLog.created_at.desc())
        rows = q.offset(skip).limit(limit).all()
        return [(log, email) for log, email in rows]
