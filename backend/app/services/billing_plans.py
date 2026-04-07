"""Public pricing cards: prefer live Stripe Prices, fallback to static copy."""

from __future__ import annotations

import logging
from typing import Any

import stripe

from app.core.config import Settings
from app.models.user import PlanType
from app.schemas.billing import BillingPlansResponse, PlanCardOut

logger = logging.getLogger(__name__)

_FALLBACK_PLANS: list[dict[str, Any]] = [
    {
        "id": "starter",
        "name": "Starter",
        "price_usd_month": 49,
        "description": "Up to 3 file uploads per month, business analytics (no automated insights).",
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_usd_month": 99,
        "description": "Unlimited files, full analytics and automated insights, PDF reports.",
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_usd_month": 199,
        "description": "Unlimited files, full analytics, multi-tenant organization, alerts.",
    },
]


def _stripe_ready(settings: Settings) -> bool:
    return bool(
        settings.stripe_secret_key
        and settings.stripe_price_starter
        and settings.stripe_price_pro
        and settings.stripe_price_enterprise
    )


def build_billing_plans_response(settings: Settings) -> BillingPlansResponse:
    if not _stripe_ready(settings):
        return BillingPlansResponse(
            plans=[PlanCardOut(**p) for p in _FALLBACK_PLANS],
            pricing_source="default",
        )

    stripe.api_key = settings.stripe_secret_key
    out: list[PlanCardOut] = []
    try:
        for plan_id, price_id in (
            (PlanType.STARTER.value, settings.stripe_price_starter),
            (PlanType.PRO.value, settings.stripe_price_pro),
            (PlanType.ENTERPRISE.value, settings.stripe_price_enterprise),
        ):
            price = stripe.Price.retrieve(price_id, expand=["product"])
            product = price.get("product")
            prod_obj: dict = product if isinstance(product, dict) else {}
            name = (prod_obj.get("name") or plan_id.title()).strip() or plan_id.title()
            desc_fb = next((x["description"] for x in _FALLBACK_PLANS if x["id"] == plan_id), "")
            description = (prod_obj.get("description") or desc_fb or "").strip() or desc_fb
            cents = int(price.unit_amount or 0)
            currency = (price.currency or "usd").lower()
            if currency != "usd":
                raise ValueError(f"Unsupported currency {currency!r}; use USD Prices or rely on fallback copy")
            price_month = max(0, cents // 100)
            out.append(
                PlanCardOut(
                    id=plan_id,
                    name=name,
                    price_usd_month=price_month,
                    description=description,
                    currency=currency,
                )
            )
        if len(out) == 3:
            return BillingPlansResponse(plans=out, pricing_source="stripe")
    except Exception:
        logger.exception("Falling back to static plan cards; Stripe Price API failed")

    return BillingPlansResponse(
        plans=[PlanCardOut(**p, currency="usd") for p in _FALLBACK_PLANS],
        pricing_source="default",
    )
