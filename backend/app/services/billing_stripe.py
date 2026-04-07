"""Stripe Checkout + subscription sync from webhooks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.api_messages import api_msg
from app.core.config import Settings
from app.models.organization import Organization
from app.models.user import PlanType, User
from app.repositories.user import UserRepository
from app.services.system_notifications import (
    notify_checkout_success,
    notify_subscription_ended,
    notify_subscription_past_due,
    notify_subscription_sync,
)

logger = logging.getLogger(__name__)

_PAID_PLANS = frozenset(
    {
        PlanType.STARTER.value,
        PlanType.PRO.value,
        PlanType.ENTERPRISE.value,
    }
)


def _init_stripe(settings: Settings, lang: str = "en") -> None:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=api_msg("stripe_not_configured", lang),
        )
    stripe.api_key = settings.stripe_secret_key


def price_id_for_plan(settings: Settings, plan: str, lang: str = "en") -> str:
    m = {
        PlanType.STARTER.value: settings.stripe_price_starter,
        PlanType.PRO.value: settings.stripe_price_pro,
        PlanType.ENTERPRISE.value: settings.stripe_price_enterprise,
    }
    pid = m.get(plan)
    if not pid:
        raise HTTPException(status_code=400, detail=api_msg("invalid_plan", lang))
    return pid


def plan_for_price_id(settings: Settings, price_id: str | None) -> str | None:
    if not price_id:
        return None
    if price_id == settings.stripe_price_starter:
        return PlanType.STARTER.value
    if price_id == settings.stripe_price_pro:
        return PlanType.PRO.value
    if price_id == settings.stripe_price_enterprise:
        return PlanType.ENTERPRISE.value
    return None


def create_checkout_session_url(db: Session, user: User, plan: str, settings: Settings, lang: str) -> str:
    if plan == PlanType.TRIAL.value:
        raise HTTPException(status_code=400, detail=api_msg("invalid_plan", lang))
    _init_stripe(settings, lang)
    price_id = price_id_for_plan(settings, plan)
    repo = UserRepository(db)
    customer_id = user.stripe_customer_id
    if not customer_id:
        c = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
        customer_id = c.id
        user.stripe_customer_id = customer_id
        repo.save(user)

    base = settings.public_app_url.rstrip("/")
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{base}/billing?success=1",
        cancel_url=f"{base}/billing?canceled=1",
        metadata={"user_id": str(user.id), "plan": plan},
        subscription_data={"metadata": {"user_id": str(user.id), "plan": plan}},
    )
    if not session.url:
        raise HTTPException(status_code=502, detail="Stripe did not return a checkout URL")
    return session.url


def create_billing_portal_url(user: User, settings: Settings, lang: str) -> str:
    """Return a Stripe Customer Billing Portal URL (payment method, cancel, invoices)."""
    _init_stripe(settings, lang)
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_msg("stripe_customer_required_for_portal", lang),
        )
    base = settings.public_app_url.rstrip("/")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{base}/billing",
    )
    if not session.url:
        raise HTTPException(status_code=502, detail="Stripe did not return a portal URL")
    return session.url


def _ensure_enterprise_org(db: Session, user: User) -> None:
    if user.plan != PlanType.ENTERPRISE.value:
        return
    if user.organization_id is not None:
        return
    name = (user.full_name or user.email).strip()[:255] or "Organization"
    org = Organization(name=name, owner_user_id=user.id)
    db.add(org)
    db.flush()
    user.organization_id = org.id


def apply_subscription_to_user(
    db: Session,
    user: User,
    plan: str,
    customer_id: str | None,
    subscription_id: str | None,
    status_str: str | None,
) -> None:
    repo = UserRepository(db)
    user.plan = plan
    if customer_id:
        user.stripe_customer_id = customer_id
    user.stripe_subscription_id = subscription_id
    user.subscription_status = (status_str or "active").lower() if status_str else "active"
    user.trial_started_at = None
    user.trial_reminder_email_sent_at = None
    user.file_limit_email_sent_at = None
    if plan == PlanType.ENTERPRISE.value:
        _ensure_enterprise_org(db, user)
    elif user.organization_id is not None:
        user.organization_id = None
    repo.save(user)


def downgrade_to_trial_after_cancel(db: Session, user: User) -> None:
    repo = UserRepository(db)
    user.plan = PlanType.TRIAL.value
    user.trial_started_at = datetime.now(timezone.utc)
    user.stripe_subscription_id = None
    user.subscription_status = "canceled"
    user.organization_id = None
    user.trial_reminder_email_sent_at = None
    user.file_limit_email_sent_at = None
    repo.save(user)


def handle_stripe_event(db: Session, event: dict[str, Any], settings: Settings) -> None:
    et = event.get("type")
    obj = event.get("data", {}).get("object") or {}

    if et == "checkout.session.completed":
        session = obj
        if session.get("mode") != "subscription":
            return
        uid = session.get("metadata", {}).get("user_id")
        plan_meta = session.get("metadata", {}).get("plan")
        if not uid:
            logger.warning("checkout.session.completed missing user_id metadata")
            return
        user = UserRepository(db).get_by_id(int(uid))
        if not user:
            return
        customer_id = session.get("customer")
        sub_id = session.get("subscription")
        plan = plan_meta or PlanType.STARTER.value
        apply_subscription_to_user(db, user, plan, customer_id, sub_id, "active")
        db.refresh(user)
        try:
            notify_checkout_success(settings, user, plan)
        except Exception:
            logger.exception("Checkout notification failed for user_id=%s", user.id)
        return

    if et == "customer.subscription.updated":
        sub = obj
        sub_id = sub.get("id")
        customer_id = sub.get("customer")
        status_str = (sub.get("status") or "").lower()
        items = (sub.get("items") or {}).get("data") or []
        price_id = None
        if items:
            price_id = (items[0].get("price") or {}).get("id")
        plan = plan_for_price_id(settings, price_id)
        if not plan:
            plan = (sub.get("metadata") or {}).get("plan")
        uid = (sub.get("metadata") or {}).get("user_id")
        user = None
        if uid:
            user = UserRepository(db).get_by_id(int(uid))
        if user is None and customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if not user:
            logger.warning("subscription.updated: user not found sub=%s", sub_id)
            return

        old_plan = user.plan
        old_status = user.subscription_status

        if status_str in ("canceled", "unpaid", "incomplete_expired"):
            downgrade_to_trial_after_cancel(db, user)
            db.refresh(user)
            try:
                notify_subscription_ended(settings, user, reason=f"Stripe status: {status_str}")
            except Exception:
                logger.exception("Subscription ended notification failed")
            return
        if status_str == "past_due":
            user.stripe_subscription_id = sub_id
            user.subscription_status = "past_due"
            if plan:
                user.plan = plan
            UserRepository(db).save(user)
            db.refresh(user)
            try:
                notify_subscription_past_due(settings, user)
            except Exception:
                logger.exception("Past due notification failed")
            return
        if not plan:
            plan = user.plan
        apply_subscription_to_user(db, user, plan, customer_id, sub_id, status_str)
        db.refresh(user)

        skip_duplicate_trial_to_paid = (
            old_plan == PlanType.TRIAL.value
            and plan in _PAID_PLANS
            and (status_str or "") == "active"
        )
        if not skip_duplicate_trial_to_paid:
            try:
                notify_subscription_sync(
                    settings,
                    user,
                    old_plan=old_plan,
                    new_plan=plan,
                    old_status=old_status,
                    new_status=user.subscription_status or status_str or "",
                    source="Stripe subscription updated",
                )
            except Exception:
                logger.exception("Subscription sync notification failed")
        return

    if et == "customer.subscription.deleted":
        sub = obj
        sub_id = sub.get("id")
        customer_id = sub.get("customer")
        user = db.query(User).filter(User.stripe_subscription_id == sub_id).first()
        if user is None and customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            downgrade_to_trial_after_cancel(db, user)
            db.refresh(user)
            try:
                notify_subscription_ended(settings, user, reason="Subscription deleted in Stripe")
            except Exception:
                logger.exception("Subscription deleted notification failed")
        return
