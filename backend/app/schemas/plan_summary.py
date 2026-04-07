from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlanFeaturesOut(BaseModel):
    bi_summary: bool
    bi_charts: bool
    bi_insights: bool
    pdf_reports: bool
    alerts: bool


class PlanSummaryResponse(BaseModel):
    """Subscription and usage KPIs (separate from BI summary at GET /dashboard/summary)."""

    plan: str
    is_active: bool
    trial_started_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    trial_days_remaining: Optional[float] = None
    trial_expired: bool
    organization_id: Optional[int] = None
    subscription_status: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    files_total: int
    files_this_month: int
    file_limit: Optional[int] = None
    file_limit_scope: str
    files_toward_limit: int
    can_upload: bool
    can_write: bool
    notifications: list[str]
    features: PlanFeaturesOut
    stripe_checkout_available: bool = False
    stripe_billing_portal_available: bool = False
