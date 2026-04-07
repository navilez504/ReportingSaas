"""Plan limits, trial expiry, and subscription KPIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.api_messages import MsgLang, api_msg
from app.models.user import PlanType, User
from app.repositories.dataset import DatasetRepository

TRIAL_DAYS = 3
TRIAL_MAX_FILES = 1
STARTER_MAX_FILES_PER_MONTH = 3
# In-app "trial ending soon" when remaining time is within this window (days).
TRIAL_EXPIRING_SOON_DAYS = 1
# Email reminder: send when trial ends in <= this many days (≈ last day for a 3-day trial).
TRIAL_EMAIL_REMINDER_MAX_DAYS_REMAINING = 1.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_plan(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {p.value for p in PlanType}:
        return v
    raise ValueError("invalid_plan")


def trial_ends_at(user: User) -> datetime | None:
    if user.plan != PlanType.TRIAL.value or user.trial_started_at is None:
        return None
    ts = user.trial_started_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts + timedelta(days=TRIAL_DAYS)


def is_trial_expired(user: User, now: datetime | None = None) -> bool:
    end = trial_ends_at(user)
    if end is None:
        return False
    n = now or _utcnow()
    if n.tzinfo is None:
        n = n.replace(tzinfo=timezone.utc)
    return n > end


def trial_days_remaining(user: User, now: datetime | None = None) -> float | None:
    end = trial_ends_at(user)
    if end is None:
        return None
    n = now or _utcnow()
    if n.tzinfo is None:
        n = n.replace(tzinfo=timezone.utc)
    return max(0.0, (end - n).total_seconds() / 86400.0)


def month_window_utc(ref: datetime | None = None) -> tuple[datetime, datetime]:
    """Inclusive start, exclusive end (UTC calendar month)."""
    n = ref or _utcnow()
    if n.tzinfo is None:
        n = n.replace(tzinfo=timezone.utc)
    start = n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def file_limit_for_plan(plan: str) -> int | None:
    """None means unlimited."""
    if plan == PlanType.TRIAL.value:
        return TRIAL_MAX_FILES
    if plan == PlanType.STARTER.value:
        return STARTER_MAX_FILES_PER_MONTH
    if plan in (PlanType.PRO.value, PlanType.ENTERPRISE.value):
        return None
    return None


def plan_allows_bi_summary(plan: str) -> bool:
    return True


def plan_allows_bi_charts(plan: str) -> bool:
    return True


def plan_allows_bi_insights(plan: str) -> bool:
    # Starter has no automated insights; trial matches Pro capacity (insights on).
    return plan in (
        PlanType.TRIAL.value,
        PlanType.PRO.value,
        PlanType.ENTERPRISE.value,
    )


def plan_allows_pdf_reports(plan: str) -> bool:
    # Full trial: same as Pro/Starter (PDF); only gate is trial expiry on write paths.
    return True


def plan_allows_alerts(plan: str) -> bool:
    return plan == PlanType.ENTERPRISE.value


def plan_feature_flags(plan: str) -> dict[str, bool]:
    return {
        "bi_summary": plan_allows_bi_summary(plan),
        "bi_charts": plan_allows_bi_charts(plan),
        "bi_insights": plan_allows_bi_insights(plan),
        "pdf_reports": plan_allows_pdf_reports(plan),
        "alerts": plan_allows_alerts(plan),
    }


def limit_scope(plan: str) -> str:
    if plan == PlanType.STARTER.value:
        return "month"
    if plan == PlanType.TRIAL.value:
        return "total"
    return "none"


def count_effective_uploads(repo: DatasetRepository, user: User) -> tuple[int, int]:
    """Returns (total_all_time, count_in_current_utc_month)."""
    total = repo.count_for_user(user.id)
    start, end = month_window_utc()
    month_count = repo.count_for_user_between(user.id, start, end)
    return total, month_count


def at_file_limit(user: User, repo: DatasetRepository) -> bool:
    limit = file_limit_for_plan(user.plan)
    if limit is None:
        return False
    total, month = count_effective_uploads(repo, user)
    if user.plan == PlanType.STARTER.value:
        return month >= limit
    return total >= limit


def can_upload(user: User, repo: DatasetRepository) -> bool:
    if not user.is_active:
        return False
    if user.plan == PlanType.TRIAL.value and is_trial_expired(user):
        return False
    return not at_file_limit(user, repo)


def notifications_for_user(user: User, repo: DatasetRepository, _lang: MsgLang) -> list[str]:
    out: list[str] = []
    if user.plan == PlanType.TRIAL.value:
        if is_trial_expired(user):
            out.append("trial_expired")
        else:
            days = trial_days_remaining(user)
            if days is not None and 0 < days <= TRIAL_EXPIRING_SOON_DAYS:
                out.append("trial_expiring_soon")
    if at_file_limit(user, repo):
        out.append("file_limit_reached")
    return out


def build_plan_summary(user: User, db: Session, lang: MsgLang) -> dict[str, Any]:
    from app.core.config import get_settings

    repo = DatasetRepository(db)
    total, month = count_effective_uploads(repo, user)
    limit = file_limit_for_plan(user.plan)
    scope = limit_scope(user.plan)
    used = total if user.plan == PlanType.TRIAL.value else (month if user.plan == PlanType.STARTER.value else total)
    settings = get_settings()
    stripe_ready = bool(
        settings.stripe_secret_key
        and settings.stripe_price_starter
        and settings.stripe_price_pro
        and settings.stripe_price_enterprise
    )

    return {
        "plan": user.plan,
        "is_active": user.is_active,
        "trial_started_at": user.trial_started_at,
        "trial_ends_at": trial_ends_at(user),
        "trial_days_remaining": trial_days_remaining(user),
        "trial_expired": is_trial_expired(user),
        "organization_id": user.organization_id,
        "subscription_status": user.subscription_status,
        "stripe_customer_id": user.stripe_customer_id,
        "files_total": total,
        "files_this_month": month,
        "file_limit": limit,
        "file_limit_scope": scope,
        "files_toward_limit": used,
        "can_upload": can_upload(user, repo),
        "can_write": user.is_active and not (user.plan == PlanType.TRIAL.value and is_trial_expired(user)),
        "notifications": notifications_for_user(user, repo, lang),
        "features": plan_feature_flags(user.plan),
        "stripe_checkout_available": stripe_ready,
        "stripe_billing_portal_available": stripe_ready and bool(user.stripe_customer_id),
    }


def ensure_account_can_write(user: User, lang: str) -> None:
    from fastapi import HTTPException, status

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=api_msg("account_deactivated", lang))
    if user.plan == PlanType.TRIAL.value and is_trial_expired(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=api_msg("trial_expired", lang))


def ensure_plan_feature(user: User, feature_key: str, lang: str) -> None:
    """Block BI / export endpoints when the current plan does not include the feature."""
    from fastapi import HTTPException, status

    flags = plan_feature_flags(user.plan)
    if flags.get(feature_key):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=api_msg("plan_feature_not_available", lang),
    )


def ensure_upload_allowed(user: User, db: Session, lang: str) -> None:
    from fastapi import HTTPException, status

    ensure_account_can_write(user, lang)
    repo = DatasetRepository(db)
    if not can_upload(user, repo):
        if at_file_limit(user, repo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=api_msg("file_limit_reached", lang),
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=api_msg("upload_not_allowed", lang))
