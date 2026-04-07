"""Append-only audit log for admin accountability."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.utils.http import client_ip, user_agent_string

logger = logging.getLogger(__name__)


def record_audit(
    db: Session,
    request: Request | None,
    *,
    actor: User | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    ip = client_ip(request) if request else ""
    ua = user_agent_string(request) if request else ""
    try:
        AuditLogRepository(db).add(
            actor_user_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        logger.exception("Failed to write audit log action=%s", action)
