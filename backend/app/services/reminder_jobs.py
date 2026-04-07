"""Periodic jobs: trial ending email (~1 day left), file-limit notice."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import PlanType, User
from app.repositories.dataset import DatasetRepository
from app.services.email_service import send_email
from app.services.plan import (
    TRIAL_EMAIL_REMINDER_MAX_DAYS_REMAINING,
    at_file_limit,
    is_trial_expired,
    trial_days_remaining,
)

logger = logging.getLogger(__name__)


def run_usage_and_trial_emails(db: Session) -> None:
    settings = get_settings()
    repo = DatasetRepository(db)
    now = datetime.now(timezone.utc)
    users = db.query(User).filter(User.is_active.is_(True)).all()

    for user in users:
        try:
            # File limit notice (once until they drop below limit again)
            if at_file_limit(user, repo):
                if user.file_limit_email_sent_at is None:
                    subj = "Storage limit reached for your plan"
                    body = (
                        f"Hi {user.full_name or user.email},\n\n"
                        f"You have reached the file upload limit for your current plan ({user.plan}). "
                        "Upgrade your subscription to upload more data.\n\n"
                        f"— {settings.app_name}"
                    )
                    if send_email(settings, user.email, subj, body):
                        user.file_limit_email_sent_at = now
                        db.add(user)
            else:
                if user.file_limit_email_sent_at is not None:
                    user.file_limit_email_sent_at = None
                    db.add(user)

            # Trial: email ~1 day before expiry (once)
            if user.plan == PlanType.TRIAL.value and user.trial_started_at and not is_trial_expired(user):
                days = trial_days_remaining(user)
                if (
                    days is not None
                    and 0 < days <= TRIAL_EMAIL_REMINDER_MAX_DAYS_REMAINING
                    and user.trial_reminder_email_sent_at is None
                ):
                    subj = "Your trial ends tomorrow"
                    body = (
                        f"Hi {user.full_name or user.email},\n\n"
                        "Your trial will expire within about 24 hours. "
                        "After that, uploads and paid features will be paused until you subscribe.\n\n"
                        f"— {settings.app_name}"
                    )
                    if send_email(settings, user.email, subj, body):
                        user.trial_reminder_email_sent_at = now
                        db.add(user)

            if user.plan != PlanType.TRIAL.value and user.trial_reminder_email_sent_at is not None:
                user.trial_reminder_email_sent_at = None
                db.add(user)
        except Exception:
            logger.exception("reminder email user_id=%s", user.id)

    db.commit()
