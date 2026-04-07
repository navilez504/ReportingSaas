from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, field_validator


class AdminSessionOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool
    ip_address: str
    user_agent: str

    @field_validator("created_at", "last_seen_at", "expires_at", "revoked_at", mode="before")
    @classmethod
    def ensure_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if getattr(v, "tzinfo", None) is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class AdminAuditLogOut(BaseModel):
    id: int
    created_at: datetime
    actor_user_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    ip_address: str

    @field_validator("created_at", mode="before")
    @classmethod
    def ensure_tz(cls, v: datetime) -> datetime:
        if getattr(v, "tzinfo", None) is None:
            return v.replace(tzinfo=timezone.utc)
        return v
