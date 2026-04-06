import math
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class KpiValue(BaseModel):
    key: str
    label: str
    value: float
    unit: str = ""
    change_pct: Optional[float] = None

    @field_validator("value", mode="before")
    @classmethod
    def value_finite(cls, v: Any) -> float:
        try:
            x = float(v)
        except (TypeError, ValueError):
            return 0.0
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x

    @field_validator("change_pct", mode="before")
    @classmethod
    def change_finite(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        if math.isnan(x) or math.isinf(x):
            return None
        return x


class SeriesPoint(BaseModel):
    name: str
    value: float

    @field_validator("value", mode="before")
    @classmethod
    def value_finite(cls, v: Any) -> float:
        try:
            x = float(v)
        except (TypeError, ValueError):
            return 0.0
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x


class DashboardResponse(BaseModel):
    dataset_id: Optional[int]
    kpis: list[KpiValue]
    line_series: list[SeriesPoint] = Field(default_factory=list)
    bar_series: list[SeriesPoint] = Field(default_factory=list)
    pie_series: list[SeriesPoint] = Field(default_factory=list)
    preview_rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sample rows from the filtered dataset for table preview",
    )
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CustomMetricCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    metric_type: str = Field(pattern="^(sum|avg|min|max|growth_pct)$")
    column_name: str = Field(min_length=1, max_length=255)


class CustomMetricOut(BaseModel):
    id: int
    name: str
    metric_type: str
    column_name: str

    model_config = {"from_attributes": True}
