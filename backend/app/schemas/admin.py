from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.user import UserRole
from app.schemas.plan_summary import PlanSummaryResponse


class AdminUserListItem(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    plan: str
    trial_started_at: Optional[datetime] = None
    is_active: bool
    organization_id: Optional[int] = None
    files_uploaded: int
    storage_datasets_bytes: int = 0
    storage_reports_bytes: int = 0
    storage_bytes_total: int = 0
    subscription_status: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": False}

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role(cls, v):
        if isinstance(v, str):
            return UserRole(v)
        return v


class AdminUserDetailResponse(AdminUserListItem):
    plan_summary: PlanSummaryResponse


class AdminUpgradeBody(BaseModel):
    plan: str = Field(..., min_length=3, max_length=32)
    organization_name: Optional[str] = Field(None, max_length=255)


class AdminStatusBody(BaseModel):
    active: bool
