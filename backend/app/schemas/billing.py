from pydantic import BaseModel, Field


class PlanCardOut(BaseModel):
    id: str = Field(..., description="starter | pro | enterprise")
    name: str
    price_usd_month: int
    description: str
    currency: str = "usd"


class BillingPlansResponse(BaseModel):
    plans: list[PlanCardOut]
    pricing_source: str = "default"


class CheckoutSessionBody(BaseModel):
    plan: str = Field(..., min_length=3, max_length=32, description="starter | pro | enterprise")


class CheckoutSessionResponse(BaseModel):
    url: str


class PortalSessionResponse(BaseModel):
    url: str
