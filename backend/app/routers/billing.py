from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db, get_locale
from app.models.user import User
from app.schemas.billing import (
    BillingPlansResponse,
    CheckoutSessionBody,
    CheckoutSessionResponse,
    PortalSessionResponse,
)
from app.services.billing_plans import build_billing_plans_response
from app.services.billing_stripe import create_billing_portal_url, create_checkout_session_url

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=BillingPlansResponse)
def list_public_plans():
    """Display pricing; amounts come from Stripe Prices when configured, else static fallback."""
    return build_billing_plans_response(get_settings())


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout(
    body: CheckoutSessionBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    """Redirect the browser to the returned `url` to complete Stripe Checkout."""
    settings = get_settings()
    url = create_checkout_session_url(db, current, body.plan.strip().lower(), settings, lang)
    return CheckoutSessionResponse(url=url)


@router.post("/portal-session", response_model=PortalSessionResponse)
def create_portal_session(
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    """Redirect the browser to Stripe Customer Billing Portal (payment method, cancel, invoices)."""
    settings = get_settings()
    url = create_billing_portal_url(current, settings, lang)
    return PortalSessionResponse(url=url)
