"""Transactional emails: user confirmations + admin alerts (registration, admin actions, billing)."""

from __future__ import annotations

import logging
from app.core.config import Settings
from app.models.user import User
from app.services.email_service import send_email

logger = logging.getLogger(__name__)


def _admin_recipients(settings: Settings) -> list[str]:
    return [e.strip() for e in (settings.admin_emails or "").split(",") if e.strip()]


def notify_admins(
    settings: Settings,
    subject: str,
    body: str,
    *,
    exclude_email: str | None = None,
) -> None:
    """Send the same message to every address in ADMIN_EMAILS (optional dedupe for self-actions)."""
    ex = (exclude_email or "").strip().lower()
    for addr in _admin_recipients(settings):
        if ex and addr.lower() == ex:
            continue
        try:
            send_email(settings, addr, subject, body)
        except Exception:
            logger.exception("Admin notification failed for %s", addr)


def notify_new_registration(settings: Settings, user: User) -> None:
    """Welcome email to the new user; admins get an alert (except the registrant if they are admin)."""
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    subj_user = f"Welcome to {app}"
    body_user = (
        f"Hi {name},\n\n"
        f"Your account was created successfully.\n"
        f"Email: {user.email}\n"
        f"Plan: {user.plan}\n\n"
        f"Sign in: {base}/login\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj_user, body_user)
    except Exception:
        logger.exception("Registration welcome email failed for %s", user.email)

    subj_adm = f"[{app}] New user registration"
    body_adm = (
        f"A new account was created.\n\n"
        f"Email: {user.email}\n"
        f"Name: {user.full_name or '—'}\n"
        f"Plan: {user.plan}\n"
        f"Role: {user.role}\n"
        f"User ID: {user.id}\n"
    )
    notify_admins(settings, subj_adm, body_adm, exclude_email=user.email)


def notify_admin_plan_change(
    settings: Settings,
    target: User,
    old_plan: str,
    new_plan: str,
    *,
    actor_email: str | None,
    action: str,
) -> None:
    """Alert admins when an admin changes a user's plan or related settings."""
    app = settings.app_name
    subj = f"[{app}] User account updated ({action})"
    actor_line = f"Changed by: {actor_email}\n" if actor_email else ""
    body = (
        f"{actor_line}"
        f"Target user: {target.email} (ID {target.id})\n"
        f"Name: {target.full_name or '—'}\n"
        f"Previous plan: {old_plan}\n"
        f"New plan: {new_plan}\n"
        f"Action: {action}\n"
    )
    notify_admins(settings, subj, body)


def notify_user_plan_change(
    settings: Settings,
    user: User,
    old_plan: str,
    new_plan: str,
    *,
    action: str,
) -> None:
    """Email the affected user about an admin-driven plan change."""
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    subj = f"Your {app} plan was updated"
    body = (
        f"Hi {name},\n\n"
        f"Your subscription details were changed ({action}).\n"
        f"Previous plan: {old_plan}\n"
        f"Current plan: {new_plan}\n\n"
        f"Billing & account: {base}/billing\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj, body)
    except Exception:
        logger.exception("User plan-change email failed for %s", user.email)


def notify_trial_renewed(
    settings: Settings,
    user: User,
    *,
    actor_email: str | None,
) -> None:
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    subj_user = f"Your {app} trial was renewed"
    body_user = (
        f"Hi {name},\n\n"
        f"Your trial period was restarted. You can continue using the product under the trial rules.\n\n"
        f"Account: {base}/billing\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj_user, body_user)
    except Exception:
        logger.exception("Trial renew email failed for %s", user.email)

    subj_adm = f"[{app}] Trial renewed for user"
    prefix = f"By: {actor_email}\n\n" if actor_email else ""
    body_adm = (
        f"{prefix}"
        f"User: {user.email} (ID {user.id})\n"
        f"Trial started at: {user.trial_started_at}\n"
    )
    notify_admins(settings, subj_adm, body_adm)


def notify_account_status_change(
    settings: Settings,
    user: User,
    *,
    active: bool,
    actor_email: str | None,
) -> None:
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    state = "activated" if active else "deactivated"
    subj_user = f"Your {app} account was {state}"
    body_user = (
        f"Hi {name},\n\n"
        f"Your account has been {state}.\n\n"
        f"If you did not expect this, contact support.\n"
        f"Sign in: {base}/login\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj_user, body_user)
    except Exception:
        logger.exception("Account status email failed for %s", user.email)

    subj_adm = f"[{app}] User account {state}"
    prefix = f"By: {actor_email}\n\n" if actor_email else ""
    body_adm = (
        f"{prefix}"
        f"User: {user.email} (ID {user.id})\n"
        f"Status: {'active' if active else 'inactive'}\n"
    )
    notify_admins(settings, subj_adm, body_adm)


def notify_checkout_success(
    settings: Settings,
    user: User,
    plan: str,
) -> None:
    """User payment confirmation + admin alert (Stripe checkout.session.completed)."""
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    subj_user = f"Payment confirmed — {plan} is active"
    body_user = (
        f"Hi {name},\n\n"
        f"Thank you. Your plan is now: {plan}.\n\n"
        f"Manage billing: {base}/billing\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj_user, body_user)
    except Exception:
        logger.exception("Checkout user email failed for %s", user.email)

    subj_adm = f"[{app}] New subscription / payment"
    body_adm = (
        f"User: {user.email} (ID {user.id})\n"
        f"Plan: {plan}\n"
        f"Subscription status: {user.subscription_status or 'active'}\n"
    )
    notify_admins(settings, subj_adm, body_adm)


def notify_subscription_sync(
    settings: Settings,
    user: User,
    *,
    old_plan: str,
    new_plan: str,
    old_status: str | None,
    new_status: str,
    source: str,
) -> None:
    """Stripe subscription.updated — plan or status change from portal or Stripe."""
    if old_plan == new_plan and (old_status or "") == (new_status or ""):
        return
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    subj = f"Your {app} subscription was updated"
    body = (
        f"Hi {name},\n\n"
        f"Your subscription details changed ({source}).\n"
        f"Plan: {old_plan} → {new_plan}\n"
        f"Status: {(old_status or '—')} → {new_status}\n\n"
        f"Billing: {base}/billing\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj, body)
    except Exception:
        logger.exception("Subscription sync user email failed for %s", user.email)

    subj_adm = f"[{app}] Subscription updated"
    body_adm = (
        f"User: {user.email} (ID {user.id})\n"
        f"Plan: {old_plan} → {new_plan}\n"
        f"Status: {(old_status or '—')} → {new_status}\n"
        f"Source: {source}\n"
    )
    notify_admins(settings, subj_adm, body_adm)


def notify_subscription_past_due(settings: Settings, user: User) -> None:
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    subj = f"Action needed: payment issue on your {app} subscription"
    body = (
        f"Hi {name},\n\n"
        f"Your subscription payment could not be completed (past due).\n"
        f"Please update your payment method in the billing portal.\n\n"
        f"{base}/billing\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj, body)
    except Exception:
        logger.exception("Past due email failed for %s", user.email)

    notify_admins(
        settings,
        f"[{app}] Subscription past due",
        f"User: {user.email} (ID {user.id})\nPlan: {user.plan}\n",
    )


def notify_subscription_ended(
    settings: Settings,
    user: User,
    *,
    reason: str,
) -> None:
    """Cancellation / subscription deleted / downgrade to trial."""
    app = settings.app_name
    base = settings.public_app_url.rstrip("/")
    name = (user.full_name or "").strip() or user.email
    subj = f"Your {app} subscription ended"
    body = (
        f"Hi {name},\n\n"
        f"Your paid subscription is no longer active ({reason}).\n"
        f"Your account is now on the trial rules until you subscribe again.\n\n"
        f"{base}/billing\n\n"
        f"— {app}"
    )
    try:
        send_email(settings, user.email, subj, body)
    except Exception:
        logger.exception("Subscription ended email failed for %s", user.email)

    notify_admins(
        settings,
        f"[{app}] Subscription ended / downgraded",
        f"User: {user.email} (ID {user.id})\nReason: {reason}\nCurrent plan: {user.plan}\n",
    )
