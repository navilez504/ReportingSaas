"""Periodic sync of Stripe subscription state into the users table."""

from __future__ import annotations

import logging

import stripe
from stripe import error as stripe_error
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.user import PlanType, User
from app.services.billing_stripe import (
    apply_subscription_to_user,
    downgrade_to_trial_after_cancel,
    plan_for_price_id,
)

logger = logging.getLogger(__name__)


def reconcile_stripe_subscriptions(db: Session, settings: Settings) -> int:
    """Return count of user rows updated to match Stripe."""
    if not settings.stripe_secret_key:
        return 0
    stripe.api_key = settings.stripe_secret_key
    changed = 0
    rows = (
        db.query(User)
        .filter(User.stripe_subscription_id.isnot(None), User.stripe_subscription_id != "")
        .all()
    )
    for user in rows:
        sub_id = user.stripe_subscription_id
        if not sub_id:
            continue
        try:
            sub = stripe.Subscription.retrieve(sub_id)
        except stripe_error.InvalidRequestError:
            logger.warning("Reconcile: subscription %s missing in Stripe for user %s", sub_id, user.id)
            downgrade_to_trial_after_cancel(db, user)
            changed += 1
            continue
        except Exception:
            logger.exception("Reconcile: error fetching subscription %s", sub_id)
            continue

        sd = sub.to_dict() if hasattr(sub, "to_dict") else dict(sub)
        status_str = str(sd.get("status") or "").lower()
        items = (sd.get("items") or {}).get("data") or []
        price_id = None
        if items:
            price_id = (items[0].get("price") or {}).get("id")
        plan = plan_for_price_id(settings, price_id)
        if not plan:
            plan = (sd.get("metadata") or {}).get("plan") or user.plan
        customer_id = sd.get("customer") or user.stripe_customer_id

        if status_str in ("canceled", "unpaid", "incomplete_expired"):
            downgrade_to_trial_after_cancel(db, user)
            changed += 1
            continue

        if status_str == "past_due":
            if user.subscription_status != "past_due" or (plan and user.plan != plan):
                user.stripe_subscription_id = sub_id
                user.subscription_status = "past_due"
                if plan:
                    user.plan = plan
                if customer_id:
                    user.stripe_customer_id = customer_id
                from app.repositories.user import UserRepository

                UserRepository(db).save(user)
                changed += 1
            continue

        norm_status = status_str or "active"
        if user.plan != plan or (user.subscription_status or "") != norm_status:
            apply_subscription_to_user(db, user, plan, customer_id, sub_id, norm_status)
            changed += 1

    return changed
