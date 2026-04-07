from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    plan: str
    trial_started_at: Optional[datetime] = None
    is_active: bool = True
    organization_id: Optional[int] = None
    subscription_status: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role(cls, v):
        if isinstance(v, str):
            return UserRole(v)
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
