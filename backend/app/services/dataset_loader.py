"""
Load a user's dataset into a cleaned, typed DataFrame (shared by dashboard + BI).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from app.models.dataset import Dataset
from app.services.kpi import (
    add_derived_business_columns,
    filter_by_dates,
    resolve_date_column,
)
from app.services.tabular import (
    coerce_typed_columns,
    expand_stale_columns_hint,
    normalize_records_from_flat_string,
    repair_single_column_dataframe,
)


def load_user_dataset_dataframe(
    ds: Dataset,
    date_from: Optional[date],
    date_to: Optional[date],
) -> pd.DataFrame:
    """Parse stored JSON rows into a filtered DataFrame with derived business columns."""
    raw_records = list(ds.cleaned_data or [])
    cols_hint = list(ds.columns) if ds.columns is not None else None
    cols_expanded = expand_stale_columns_hint(cols_hint)
    raw_records = normalize_records_from_flat_string(raw_records, cols_expanded)
    df_raw = pd.DataFrame(raw_records)
    if df_raw.empty:
        return df_raw
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df_raw = repair_single_column_dataframe(df_raw, columns_hint=cols_expanded)
    df_raw = coerce_typed_columns(df_raw)
    date_for_filter = resolve_date_column(ds, df_raw)
    df = filter_by_dates(df_raw, date_for_filter, date_from, date_to)
    df = add_derived_business_columns(df)
    return df
