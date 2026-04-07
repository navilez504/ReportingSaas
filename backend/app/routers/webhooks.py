"""Stripe webhooks — signature verification and subscription sync."""

import logging

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db import SessionLocal
from app.models.stripe_webhook_event import StripeWebhookEvent
from app.services.billing_stripe import handle_stripe_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
):
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=501,
            detail="Stripe webhooks not configured (set STRIPE_WEBHOOK_SECRET).",
        )
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=501, detail="Stripe secret key not configured.")
    body = await request.body()
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature")

    stripe.api_key = settings.stripe_secret_key
    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, settings.stripe_webhook_secret)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from e
    except Exception as e:
        err = str(e).lower()
        if "signature" in err or "no signatures" in err:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature") from e
        raise HTTPException(status_code=400, detail=str(e)) from e

    if isinstance(event, dict):
        ev = event
    elif hasattr(event, "to_dict"):
        ev = event.to_dict()
    else:
        ev = dict(event)
    eid = ev.get("id")
    etype = str(ev.get("type") or "")
    if not eid:
        raise HTTPException(status_code=400, detail="Missing Stripe event id")

    db = SessionLocal()
    try:
        db.add(StripeWebhookEvent(event_id=str(eid), event_type=etype))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return {"received": True, "duplicate": True}
        try:
            handle_stripe_event(db, ev, settings)
            db.commit()
        except Exception:
            db.rollback()
            raise
    except HTTPException:
        raise
    except Exception:
        logger.exception("Stripe webhook handler failed event=%s", etype)
        raise HTTPException(status_code=500, detail="Webhook handler error") from None
    finally:
        db.close()

    return {"received": True}
