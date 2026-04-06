import math
import re
from datetime import date
from typing import Any, Optional

import pandas as pd

from app.models.dataset import Dataset
from app.models.custom_metric import CustomMetric

_VALUE_KEYWORDS = (
    "cantidad",
    "quantity",
    "qty",
    "amount",
    "total",
    "precio",
    "price",
    "ventas",
    "sales",
    "importe",
    "valor",
    "monto",
    "subtotal",
)
_DATE_KEYWORDS = ("fecha", "date", "fecha_", "dia", "timestamp", "time")

# Prefer these for bar-chart categories (not raw date columns when a dimension exists)
_BAR_DIM_PREF = (
    "categoria",
    "category",
    "region",
    "cliente",
    "customer",
    "producto",
    "vendedor",
    "tipo",
    "segmento",
)


def _rank_bar_category_col(name: str) -> tuple[int, str]:
    lc = str(name).lower()
    for i, p in enumerate(_BAR_DIM_PREF):
        if p in lc:
            return (0, f"{i:02d}_{lc}")
    if "fecha" in lc or lc == "date" or lc.endswith("_at"):
        return (2, lc)
    return (1, lc)


def _clean_scalar_number(val: Any) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return float("nan")
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return float("nan")
        return v
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "-", "n/a", "na"):
        return float("nan")
    s = re.sub(r"[\s€$£¥₹]", "", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2 and parts[1].isdigit():
            s = parts[0].replace(".", "") + "." + parts[1]
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _to_numeric_series_robust(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    s = df[col]
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    return s.map(_clean_scalar_number)


def _parse_dates_series(raw: pd.Series) -> pd.Series:
    """ES/LATAM text dates, ISO strings, Excel day serials (do not use pd.to_datetime on raw numbers first)."""
    n = len(raw)
    if n == 0:
        return pd.to_datetime(raw, errors="coerce", dayfirst=True)

    num = pd.to_numeric(raw, errors="coerce")
    if num.notna().any():
        mx = float(num.max())
        mn = float(num.min())
        # Excel serial days are typically ~30000–55000 for 1980–2030
        if 25000 < mx < 120000 and 25000 < mn < 120000:
            d_ex = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
            if int(d_ex.notna().sum()) >= max(1, (n + 1) // 2):
                return d_ex

    d_text = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    n_text = int(d_text.notna().sum())
    if n_text >= max(1, (n + 1) // 2):
        return d_text

    if int(num.notna().sum()) >= max(1, n // 4):
        d_ex = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
        if int(d_ex.notna().sum()) > n_text:
            return d_ex
    return d_text


def resolve_value_column(dataset: Dataset, df: pd.DataFrame) -> Optional[str]:
    """Pick a measure column; prefer sales/qty/price columns over surrogate ids."""
    if df.empty or not len(df.columns):
        return None
    lower_map = {str(c).lower(): c for c in df.columns}
    # 1) Prefer known measure-like names (avoid using row ids as the KPI)
    for kw in _VALUE_KEYWORDS:
        for lc, orig in lower_map.items():
            if kw in lc and lc not in ("id", "idx", "index"):
                if _to_numeric_series_robust(df, orig).notna().any():
                    return orig
    # 2) Use stored metadata if it parses and is not a bare id column
    stored = (dataset.value_column or "").strip() or None
    if stored and stored in df.columns:
        if str(stored).lower() not in ("id", "idx", "index"):
            if _to_numeric_series_robust(df, stored).notna().any():
                return stored
        elif _to_numeric_series_robust(df, stored).notna().any():
            pass  # fall through to find a better column than id
    # 3) First numeric column that is not id
    for c in df.columns:
        if str(c).lower() in ("id", "idx", "index"):
            continue
        if _to_numeric_series_robust(df, c).notna().any():
            return c
    # 4) Last resort: id
    for c in df.columns:
        if str(c).lower() in ("id", "idx", "index"):
            if _to_numeric_series_robust(df, c).notna().any():
                return c
    return None


def _first_matching_column(df: pd.DataFrame, names: tuple[str, ...]) -> Optional[str]:
    """Pick first preferred column name present in df (case-insensitive exact match)."""
    lower = {str(c).lower(): c for c in df.columns}
    for n in names:
        nl = n.lower()
        if nl in lower:
            return lower[nl]
    return None


def add_derived_business_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Row-level metrics when columns exist:
    total_venta = cantidad * precio_unitario (or precio)
    total_costo = cantidad * costo
    ganancia = total_venta - total_costo
    """
    if df.empty:
        return df
    out = df.copy()
    qcol = _first_matching_column(out, ("cantidad", "quantity", "qty"))
    pcol = _first_matching_column(out, ("precio_unitario", "precio", "unit_price", "price_unit", "price"))
    ccol = _first_matching_column(out, ("costo", "cost", "coste", "unit_cost"))

    if qcol and pcol:
        q = _to_numeric_series_robust(out, qcol)
        p = _to_numeric_series_robust(out, pcol)
        out["total_venta"] = q * p
    if qcol and ccol:
        q = _to_numeric_series_robust(out, qcol)
        c = _to_numeric_series_robust(out, ccol)
        out["total_costo"] = q * c
    if "total_venta" in out.columns and "total_costo" in out.columns:
        out["ganancia"] = out["total_venta"] - out["total_costo"]
    return out


def resolve_date_column(dataset: Dataset, df: pd.DataFrame) -> Optional[str]:
    if df.empty:
        return None
    stored = (dataset.date_column or "").strip() or None
    if stored and stored in df.columns:
        s = _parse_dates_series(df[stored])
        if s.notna().any():
            return stored
    lower_map = {str(c).lower(): c for c in df.columns}
    for kw in _DATE_KEYWORDS:
        for lc, orig in lower_map.items():
            if kw in lc:
                s = _parse_dates_series(df[orig])
                if s.notna().any():
                    return orig
    return None


def _finite_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if math.isnan(v) or math.isinf(v):
        return default
    return v


def _finite_or_none(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def _to_numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    return _to_numeric_series_robust(df, col)


def filter_by_dates(
    df: pd.DataFrame,
    date_col: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
) -> pd.DataFrame:
    """Filter rows by date range. If parsing fails or no row matches, returns df unchanged."""
    date_col = (date_col or "").strip() or None
    if not date_col or date_col not in df.columns or (date_from is None and date_to is None):
        return df
    dts = _parse_dates_series(df[date_col])
    mask = dts.notna()
    if mask.sum() == 0:
        return df
    if date_from is not None:
        mask &= dts.dt.date >= date_from
    if date_to is not None:
        mask &= dts.dt.date <= date_to
    out = df.loc[mask].copy()
    if len(out) == 0 and len(df) > 0:
        return df
    return out


def compute_growth_pct(values: pd.Series) -> Optional[float]:
    s = values.dropna().reset_index(drop=True)
    if len(s) < 2:
        return None
    n = len(s)
    a = s.iloc[: n // 2].mean()
    b = s.iloc[n // 2 :].mean()
    if a == 0 or pd.isna(a) or pd.isna(b):
        return None
    return float((b - a) / abs(a) * 100.0)


def growth_value_column(df: pd.DataFrame, date_col: Optional[str], value_col: str) -> Optional[float]:
    num = _to_numeric_series(df, value_col)
    if date_col and date_col in df.columns:
        dts = _parse_dates_series(df[date_col])
        sub = df.assign(_d=dts, _v=num).dropna(subset=["_d", "_v"]).sort_values("_d")
        return compute_growth_pct(sub["_v"])
    return compute_growth_pct(num)


def aggregate_metric(df: pd.DataFrame, col: str, metric_type: str) -> Optional[float]:
    if col not in df.columns:
        return None
    num = _to_numeric_series(df, col)
    if metric_type == "sum":
        return _finite_or_none(float(num.sum()))
    if metric_type == "avg":
        return _finite_or_none(float(num.mean())) if num.notna().any() else None
    if metric_type == "min":
        return _finite_or_none(float(num.min())) if num.notna().any() else None
    if metric_type == "max":
        return _finite_or_none(float(num.max())) if num.notna().any() else None
    if metric_type == "growth_pct":
        return compute_growth_pct(num)
    return None


def build_kpi_list(
    dataset: Dataset,
    df: pd.DataFrame,
    custom_metrics: list[CustomMetric],
) -> list[dict[str, Any]]:
    value_col = resolve_value_column(dataset, df)
    date_col = resolve_date_column(dataset, df)

    kpis: list[dict[str, Any]] = []

    row_count = len(df)
    kpis.append(
        {
            "key": "rows",
            "label": "Rows in view",
            "value": float(row_count),
            "unit": "",
            "change_pct": None,
        }
    )

    if value_col and value_col in df.columns:
        num = _to_numeric_series(df, value_col)
        total = _finite_float(num.sum()) if num.notna().any() else 0.0
        avg = _finite_float(num.mean()) if num.notna().any() else 0.0
        growth = growth_value_column(df, date_col, value_col)
        gp_change = growth if growth is not None and _finite_or_none(growth) is not None else None
        kpis.append(
            {
                "key": "total_sales",
                "label": f"Total ({value_col})",
                "value": total,
                "unit": "",
                "change_pct": gp_change,
            }
        )
        kpis.append({"key": "average", "label": f"Average ({value_col})", "value": avg, "unit": "", "change_pct": None})
        if growth is not None:
            gp = _finite_or_none(growth)
            if gp is not None:
                kpis.append(
                    {
                        "key": "growth_pct",
                        "label": "Growth (period)",
                        "value": gp,
                        "unit": "%",
                        "change_pct": None,
                    }
                )

    for col_key, label in (
        ("total_venta", "Total venta (Σ cantidad × precio)"),
        ("total_costo", "Total costo (Σ cantidad × costo)"),
        ("ganancia", "Ganancia (venta − costo)"),
    ):
        if col_key in df.columns:
            num = _to_numeric_series(df, col_key)
            if num.notna().any():
                kpis.append(
                    {
                        "key": f"kpi_{col_key}",
                        "label": label,
                        "value": _finite_float(num.sum()),
                        "unit": "",
                        "change_pct": None,
                    }
                )

    for m in custom_metrics:
        v = aggregate_metric(df, m.column_name, m.metric_type)
        if v is not None:
            fv = _finite_or_none(v)
            if fv is None:
                continue
            unit = "%" if m.metric_type == "growth_pct" else ""
            kpis.append(
                {
                    "key": f"custom_{m.id}",
                    "label": m.name,
                    "value": fv,
                    "unit": unit,
                    "change_pct": None,
                }
            )

    if not any(k["key"] in ("total_sales", "sum_primary") for k in kpis):
        # fallback: first column with any coercible numeric values
        for col in df.columns:
            num = _to_numeric_series(df, col)
            if num.notna().sum() > 0:
                sm = _finite_float(num.sum())
                ch = compute_growth_pct(num)
                kpis.append(
                    {
                        "key": "sum_primary",
                        "label": f"Sum of {col}",
                        "value": sm,
                        "unit": "",
                        "change_pct": ch,
                    }
                )
                break

    return kpis


def _charts_from_xy(df: pd.DataFrame, x_col: str, y_col: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Build line / bar / pie from user-selected X and Y columns."""
    line_series: list[dict] = []
    bar_series: list[dict] = []
    pie_series: list[dict] = []
    if x_col == y_col or x_col not in df.columns or y_col not in df.columns:
        return line_series, bar_series, pie_series
    num = _to_numeric_series_robust(df, y_col)
    sub = df.assign(_y=num).dropna(subset=["_y"])
    if sub.empty:
        return line_series, bar_series, pie_series

    dts = _parse_dates_series(sub[x_col])
    if int(dts.notna().sum()) >= max(1, len(sub) // 2):
        s2 = sub.assign(_dt=dts).dropna(subset=["_dt"])
        s2["_day"] = s2["_dt"].dt.date
        daily = s2.groupby("_day", as_index=False, sort=True)["_y"].sum()
        for _, row in daily.tail(40).iterrows():
            line_series.append({"name": str(row["_day"]), "value": _finite_float(row["_y"])})
    else:
        capped = sub.head(50)
        for _, row in capped.iterrows():
            xv = row[x_col]
            name = (
                str(xv)[:50]
                if xv is not None and not (isinstance(xv, float) and pd.isna(xv))
                else ""
            )
            line_series.append({"name": name or "—", "value": _finite_float(row["_y"])})

    g = (
        sub.groupby(
            sub[x_col].map(lambda x: str(x) if x is not None and not (isinstance(x, float) and pd.isna(x)) else ""),
            dropna=True,
        )["_y"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
    )
    for name, val in g.items():
        if name == "":
            continue
        bar_series.append({"name": str(name)[:60], "value": _finite_float(val)})
    pie_series = bar_series[:6]
    return line_series, bar_series, pie_series


def dataframe_for_charts(
    df: pd.DataFrame,
    dataset: Dataset,
    chart_x: Optional[str] = None,
    chart_y: Optional[str] = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Line (time series), bar (categories), pie (share) — best-effort from columns."""
    cx = (chart_x or "").strip() or None
    cy = (chart_y or "").strip() or None
    if cx and cy:
        return _charts_from_xy(df, cx, cy)

    value_col = resolve_value_column(dataset, df)
    date_col = resolve_date_column(dataset, df)
    line_series: list[dict] = []
    bar_series: list[dict] = []
    pie_series: list[dict] = []

    if date_col and value_col and date_col in df.columns and value_col in df.columns:
        dts = _parse_dates_series(df[date_col])
        sub = df.assign(_dt=dts).dropna(subset=["_dt"])
        num = _to_numeric_series_robust(sub, value_col)
        sub = sub.assign(_v=num).dropna(subset=["_v"])
        sub = sub.sort_values("_dt")
        sub["_day"] = sub["_dt"].dt.date
        daily = sub.groupby("_day", as_index=False, sort=True)["_v"].sum()
        for _, row in daily.tail(30).iterrows():
            line_series.append({"name": str(row["_day"]), "value": _finite_float(row["_v"])})

    # bar: string-like column with numeric aggregate (prefer business dimensions over date text)
    cat_cols = [
        c
        for c in df.columns
        if c != value_col
        and (df[c].dtype == object or pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_integer_dtype(df[c]))
    ]
    cat_cols.sort(key=_rank_bar_category_col)
    if cat_cols and value_col and value_col in df.columns:
        tmp = df[[cat_cols[0], value_col]].copy()
        tmp["_vn"] = _to_numeric_series_robust(tmp, value_col)
        g = tmp.groupby(cat_cols[0], dropna=True)["_vn"].sum()
        g = g.sort_values(ascending=False).head(10)
        for name, val in g.items():
            bar_series.append({"name": str(name)[:40], "value": _finite_float(val)})

    # pie: same as bar top 6
    if bar_series:
        pie_series = bar_series[:6]

    # Fallback: any non-measure column vs measure (handles numeric "categoria" coded as int, etc.)
    if not bar_series and value_col and value_col in df.columns and len(df) > 0:
        for c in df.columns:
            if c == value_col:
                continue
            tmp = df[[c, value_col]].copy()
            tmp["_vn"] = _to_numeric_series_robust(tmp, value_col)
            if tmp["_vn"].notna().sum() == 0:
                continue
            tmp["_g"] = tmp[c].map(lambda x: str(x) if x is not None and not (isinstance(x, float) and pd.isna(x)) else "")
            g = tmp.groupby("_g", dropna=True)["_vn"].sum().sort_values(ascending=False).head(12)
            for name, val in g.items():
                if name == "":
                    continue
                bar_series.append({"name": str(name)[:60], "value": _finite_float(val)})
            if bar_series:
                pie_series = bar_series[:6]
                break

    # Last resort: index as x, first numeric column y
    if not line_series and not bar_series and len(df.columns) >= 1:
        nums = [c for c in df.columns if _to_numeric_series_robust(df, c).notna().any()]
        if nums:
            nc = nums[0]
            for i, v in enumerate(_to_numeric_series_robust(df, nc).head(25)):
                bar_series.append({"name": f"Row {i + 1}", "value": _finite_float(v)})
            pie_series = bar_series[:6]

    return line_series, bar_series, pie_series
