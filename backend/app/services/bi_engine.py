"""
Business Intelligence: KPIs, grouped metrics, and automatic insights from tabular data.
"""

from __future__ import annotations

import math
import time
from typing import Any, Callable, Optional, TypeVar

import pandas as pd

from app.models.dataset import Dataset
from app.services.kpi import (
    _first_matching_column,
    _parse_dates_series,
    _to_numeric_series_robust,
    resolve_date_column,
)

T = TypeVar("T")

_CACHE_TTL_SEC = 45
_cache: dict[str, tuple[float, Any]] = {}


def _cache_key(prefix: str, user_id: int, dataset_id: int | None, date_from: Any, date_to: Any) -> str:
    return f"{prefix}:{user_id}:{dataset_id}:{date_from}:{date_to}"


def _cached(key: str, factory: Callable[[], T]) -> T:
    now = time.time()
    if key in _cache:
        ts, val = _cache[key]
        if now - ts < _CACHE_TTL_SEC:
            return val  # type: ignore[return-value]
    val = factory()
    _cache[key] = (now, val)
    return val


def resolve_bi_columns(df: pd.DataFrame) -> dict[str, Optional[str]]:
    """Map logical BI roles to actual column names."""
    return {
        "fecha": _first_matching_column(df, ("fecha", "date", "fecha_venta", "order_date", "dia")),
        "cantidad": _first_matching_column(df, ("cantidad", "quantity", "qty")),
        "precio_unitario": _first_matching_column(
            df, ("precio_unitario", "precio", "unit_price", "price_unit", "price")
        ),
        "producto": _first_matching_column(df, ("producto", "product", "sku", "item", "articulo")),
        "region": _first_matching_column(
            df, ("region", "zona", "area", "pais", "country", "país", "territorio", "territory")
        ),
        "vendedor": _first_matching_column(df, ("vendedor", "seller", "sales_rep", "empleado", "representante")),
    }


def validate_bi(df: pd.DataFrame) -> tuple[bool, list[str], dict[str, Optional[str]]]:
    """
    Require fecha, cantidad, precio_unitario (or recognized aliases) for the BI API.
    Returns (ok, missing_required, columns).
    """
    cols = resolve_bi_columns(df)
    missing: list[str] = []
    if cols["fecha"] is None:
        missing.append("fecha")
    if cols["cantidad"] is None:
        missing.append("cantidad")
    if cols["precio_unitario"] is None:
        missing.append("precio_unitario")
    ok = len(missing) == 0
    return ok, missing, cols


def _finite(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return v


def line_sales_series(df: pd.DataFrame, cols: dict[str, Optional[str]]) -> pd.Series:
    """Per-row line sales = cantidad * precio (prefer total_venta if present)."""
    if "total_venta" in df.columns:
        s = _to_numeric_series_robust(df, "total_venta")
        if s.notna().any():
            return s.fillna(0.0)
    qcol, pcol = cols.get("cantidad"), cols.get("precio_unitario")
    if not qcol or not pcol:
        return pd.Series(0.0, index=df.index)
    q = _to_numeric_series_robust(df, qcol).fillna(0.0)
    p = _to_numeric_series_robust(df, pcol).fillna(0.0)
    return q * p


def compute_bi_summary(df: pd.DataFrame, cols: dict[str, Optional[str]]) -> dict[str, Any]:
    sales = line_sales_series(df, cols)
    qcol = cols.get("cantidad")
    qty = _to_numeric_series_robust(df, qcol).fillna(0.0) if qcol else pd.Series(0.0, index=df.index)

    total_sales = _finite(sales.sum())
    total_orders = int(len(df))
    total_quantity = _finite(qty.sum())
    average_order_value = total_sales / total_orders if total_orders else 0.0

    out: dict[str, Any] = {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "average_order_value": average_order_value,
        "total_quantity": total_quantity,
    }

    if "total_costo" in df.columns:
        tc = _to_numeric_series_robust(df, "total_costo")
        if tc.notna().any():
            total_cost = _finite(tc.sum())
            profit = total_sales - total_cost
            profit_margin = profit / total_sales if abs(total_sales) > 1e-9 else 0.0
            out["total_cost"] = total_cost
            out["profit"] = profit
            out["profit_margin"] = profit_margin
    return out


def _group_sum_sales(
    df: pd.DataFrame,
    cols: dict[str, Optional[str]],
    dim_col: Optional[str],
    top: int = 15,
) -> list[dict[str, Any]]:
    if not dim_col or dim_col not in df.columns:
        return []
    sales = line_sales_series(df, cols)
    tmp = pd.DataFrame({"_d": df[dim_col].map(lambda x: str(x).strip() if pd.notna(x) and str(x) else ""), "_s": sales})
    tmp = tmp[tmp["_d"] != ""]
    if tmp.empty:
        return []
    g = tmp.groupby("_d", dropna=True)["_s"].sum().sort_values(ascending=False).head(top)
    return [{"name": str(k)[:80], "value": _finite(v)} for k, v in g.items()]


def compute_bi_charts(df: pd.DataFrame, cols: dict[str, Optional[str]], dataset: Dataset) -> dict[str, Any]:
    sales = line_sales_series(df, cols)
    out: dict[str, Any] = {
        "sales_by_product": _group_sum_sales(df, cols, cols.get("producto")),
        "sales_by_region": _group_sum_sales(df, cols, cols.get("region")),
        "sales_by_seller": _group_sum_sales(df, cols, cols.get("vendedor")),
        "sales_over_time": [],
    }

    fecha_col = cols.get("fecha") or resolve_date_column(dataset, df)
    if fecha_col and fecha_col in df.columns:
        dts = _parse_dates_series(df[fecha_col])
        sub = df.assign(_dt=dts, _s=sales).dropna(subset=["_dt"])
        if not sub.empty:
            sub["_day"] = sub["_dt"].dt.date
            daily = sub.groupby("_day", as_index=False, sort=True)["_s"].sum().tail(60)
            out["sales_over_time"] = [
                {"name": str(row["_day"]), "value": _finite(row["_s"])} for _, row in daily.iterrows()
            ]
    return out


def compute_bi_insights(
    df: pd.DataFrame,
    cols: dict[str, Optional[str]],
    dataset: Dataset,
    language: str = "en",
) -> dict[str, Any]:
    charts = compute_bi_charts(df, cols, dataset)
    top_product = ""
    top_region = ""
    top_seller = ""
    if charts["sales_by_product"]:
        top_product = charts["sales_by_product"][0]["name"]
    if charts["sales_by_region"]:
        top_region = charts["sales_by_region"][0]["name"]
    if charts["sales_by_seller"]:
        top_seller = charts["sales_by_seller"][0]["name"]

    trend = _compute_trend_message(df, cols, dataset, language=language)
    no_trend = (
        "Not enough date coverage to compute a trend."
        if language != "es"
        else "No hay cobertura de fechas suficiente para calcular la tendencia."
    )

    es = language == "es"
    messages: list[str] = []
    if top_seller:
        messages.append(
            f"Mejor vendedor: {top_seller}" if es else f"Top seller: {top_seller}"
        )
    if top_product:
        messages.append(
            f"Producto más vendido: {top_product}" if es else f"Best product: {top_product}"
        )
    if top_region:
        messages.append(
            f"Región con más ingresos: {top_region}"
            if es
            else f"Highest revenue region: {top_region}"
        )
    if trend:
        messages.append(trend)

    return {
        "top_seller": top_seller or None,
        "top_product": top_product or None,
        "top_region": top_region or None,
        "trend": trend or no_trend,
        "messages": messages,
    }


def _compute_trend_message(
    df: pd.DataFrame,
    cols: dict[str, Optional[str]],
    dataset: Dataset,
    language: str = "en",
) -> str:
    es = language == "es"
    fecha_col = cols.get("fecha") or resolve_date_column(dataset, df)
    if not fecha_col or fecha_col not in df.columns:
        return (
            "Añada una columna de fecha (p. ej. fecha) para ver la tendencia de ventas frente al periodo anterior."
            if es
            else "Add a date column (e.g. fecha) to see sales trend vs earlier period."
        )
    sales = line_sales_series(df, cols)
    dts = _parse_dates_series(df[fecha_col])
    sub = df.assign(_dt=dts, _s=sales).dropna(subset=["_dt"])
    if len(sub) < 2:
        return (
            "No hay filas con fecha suficientes para comparar periodos."
            if es
            else "Not enough dated rows to compare periods."
        )
    sub = sub.sort_values("_dt")
    mid = sub["_dt"].median()
    first = sub[sub["_dt"] < mid]["_s"].sum()
    second = sub[sub["_dt"] >= mid]["_s"].sum()
    if _finite(first) == 0 and _finite(second) == 0:
        return "No hay ventas en el periodo seleccionado." if es else "No sales in the selected period."
    if _finite(first) == 0:
        return (
            "Las ventas crecieron en la mitad más reciente del periodo seleccionado."
            if es
            else "Sales grew in the more recent half of the selected period."
        )
    pct = (second - first) / abs(first) * 100.0
    if pct > 0.5:
        return (
            f"Las ventas aumentaron un {pct:.1f}% en la mitad más reciente del periodo frente a la mitad anterior."
            if es
            else f"Sales increased by {pct:.1f}% in the more recent half of the selected period vs the earlier half."
        )
    if pct < -0.5:
        return (
            f"Las ventas bajaron un {abs(pct):.1f}% en la mitad más reciente del periodo frente a la mitad anterior."
            if es
            else f"Sales decreased by {abs(pct):.1f}% in the more recent half of the selected period vs the earlier half."
        )
    return (
        "Las ventas se mantuvieron estables entre la primera y la segunda mitad del periodo seleccionado."
        if es
        else "Sales were stable between the first and second half of the selected period."
    )


def get_bi_summary_payload(
    df: pd.DataFrame,
    cols: dict[str, Optional[str]],
    user_id: int,
    dataset_id: int | None,
    date_from: Any,
    date_to: Any,
) -> dict[str, Any]:
    key = _cache_key("summary", user_id, dataset_id, date_from, date_to)
    return _cached(key, lambda: compute_bi_summary(df, cols))


def get_bi_charts_payload(
    df: pd.DataFrame,
    cols: dict[str, Optional[str]],
    dataset: Dataset,
    user_id: int,
    dataset_id: int | None,
    date_from: Any,
    date_to: Any,
) -> dict[str, Any]:
    key = _cache_key("charts", user_id, dataset_id, date_from, date_to)
    return _cached(key, lambda: compute_bi_charts(df, cols, dataset))


def get_bi_insights_payload(
    df: pd.DataFrame,
    cols: dict[str, Optional[str]],
    dataset: Dataset,
    user_id: int,
    dataset_id: int | None,
    date_from: Any,
    date_to: Any,
    language: str = "en",
) -> dict[str, Any]:
    lang = language if language in ("en", "es") else "en"
    key = _cache_key(f"insights:{lang}", user_id, dataset_id, date_from, date_to)
    return _cached(key, lambda: compute_bi_insights(df, cols, dataset, language=lang))
