"""Pydantic models for BI API responses."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SeriesPointOut(BaseModel):
    name: str
    value: float


class BISummaryResponse(BaseModel):
    total_sales: float
    total_orders: int
    average_order_value: float
    total_quantity: float
    total_cost: Optional[float] = None
    profit: Optional[float] = None
    profit_margin: Optional[float] = None
    dataset_id: Optional[int] = None


class BIChartsResponse(BaseModel):
    sales_by_product: list[SeriesPointOut] = Field(default_factory=list)
    sales_by_region: list[SeriesPointOut] = Field(default_factory=list)
    sales_by_seller: list[SeriesPointOut] = Field(default_factory=list)
    sales_over_time: list[SeriesPointOut] = Field(default_factory=list)
    dataset_id: Optional[int] = None


class BIInsightsResponse(BaseModel):
    top_seller: Optional[str] = None
    top_product: Optional[str] = None
    top_region: Optional[str] = None
    trend: str = ""
    messages: list[str] = Field(default_factory=list)
    dataset_id: Optional[int] = None


class BIErrorDetail(BaseModel):
    detail: str
    missing_columns: list[str] = Field(default_factory=list)
    hint: str = "Upload a CSV with columns: fecha, cantidad, precio_unitario (and optional producto, region, vendedor, costo)."
