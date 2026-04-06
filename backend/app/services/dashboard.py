import json
from datetime import date
from typing import Any, Optional

import pandas as pd
from fastapi import HTTPException, status

from app.core.api_messages import api_msg
from app.models.dataset import Dataset
from app.repositories.custom_metric import CustomMetricRepository
from app.repositories.dataset import DatasetRepository
from app.services.kpi import (
    build_kpi_list,
    dataframe_for_charts,
    resolve_date_column,
    resolve_value_column,
)
from app.services.bi_engine import (
    compute_bi_insights,
    compute_bi_summary,
    get_bi_charts_payload,
    get_bi_insights_payload,
    get_bi_summary_payload,
    validate_bi,
)
from app.services.dataset_loader import load_user_dataset_dataframe
from app.services.tabular import expand_stale_columns_hint
from app.schemas.bi import BIChartsResponse, BIInsightsResponse, BISummaryResponse, SeriesPointOut
from app.schemas.dashboard import DashboardResponse, KpiValue, SeriesPoint


def _preview_rows_json(df: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    if df.empty:
        return []
    try:
        return json.loads(
            df.head(limit).to_json(orient="records", date_format="iso", date_unit="s", default_handler=str)
        )
    except Exception:
        return []


class DashboardService:
    def __init__(self, dataset_repo: DatasetRepository, metric_repo: CustomMetricRepository):
        self.dataset_repo = dataset_repo
        self.metric_repo = metric_repo

    def _get_dataset_for_user(self, user_id: int, dataset_id: Optional[int]) -> Optional[Dataset]:
        if dataset_id is not None:
            return self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        rows = self.dataset_repo.list_for_user(user_id, limit=1)
        return rows[0] if rows else None

    def _raise_bi_validation(self, missing: list[str], lang: str = "en") -> None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": api_msg("bi_requires_columns", lang),
                "missing_columns": missing,
            },
        )

    def get_bi_report_payload(
        self,
        user_id: int,
        dataset_id: Optional[int],
        language: str = "en",
    ) -> tuple[Optional[Dataset], Optional[dict[str, Any]], Optional[dict[str, Any]]]:
        """For PDF: BI summary + insights dicts, or (ds, None, None) if validation fails."""
        ds = self._get_dataset_for_user(user_id, dataset_id)
        if ds is None:
            return None, None, None
        df = load_user_dataset_dataframe(ds, None, None)
        ok, _missing, cols = validate_bi(df)
        if not ok:
            return ds, None, None
        summary = compute_bi_summary(df, cols)
        insights = compute_bi_insights(df, cols, ds, language=language)
        return ds, summary, insights

    def get_bi_summary(
        self,
        user_id: int,
        dataset_id: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        lang: str = "en",
    ) -> BISummaryResponse:
        ds = self._get_dataset_for_user(user_id, dataset_id)
        if ds is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=api_msg("no_dataset_upload_first", lang),
            )
        df = load_user_dataset_dataframe(ds, date_from, date_to)
        ok, missing, cols = validate_bi(df)
        if not ok:
            self._raise_bi_validation(missing, lang=lang)
        payload = get_bi_summary_payload(df, cols, user_id, ds.id, date_from, date_to)
        return BISummaryResponse(dataset_id=ds.id, **payload)

    def get_bi_charts(
        self,
        user_id: int,
        dataset_id: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        lang: str = "en",
    ) -> BIChartsResponse:
        ds = self._get_dataset_for_user(user_id, dataset_id)
        if ds is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=api_msg("no_dataset_upload_first", lang),
            )
        df = load_user_dataset_dataframe(ds, date_from, date_to)
        ok, missing, cols = validate_bi(df)
        if not ok:
            self._raise_bi_validation(missing, lang=lang)
        raw = get_bi_charts_payload(df, cols, ds, user_id, ds.id, date_from, date_to)
        return BIChartsResponse(
            dataset_id=ds.id,
            sales_by_product=[SeriesPointOut(**x) for x in raw["sales_by_product"]],
            sales_by_region=[SeriesPointOut(**x) for x in raw["sales_by_region"]],
            sales_by_seller=[SeriesPointOut(**x) for x in raw["sales_by_seller"]],
            sales_over_time=[SeriesPointOut(**x) for x in raw["sales_over_time"]],
        )

    def get_bi_insights(
        self,
        user_id: int,
        dataset_id: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        lang: str = "en",
    ) -> BIInsightsResponse:
        ds = self._get_dataset_for_user(user_id, dataset_id)
        if ds is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=api_msg("no_dataset_upload_first", lang),
            )
        df = load_user_dataset_dataframe(ds, date_from, date_to)
        ok, missing, cols = validate_bi(df)
        if not ok:
            self._raise_bi_validation(missing, lang=lang)
        raw = get_bi_insights_payload(
            df, cols, ds, user_id, ds.id, date_from, date_to, language=lang
        )
        return BIInsightsResponse(dataset_id=ds.id, **raw)

    def get_dashboard(
        self,
        user_id: int,
        dataset_id: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        chart_x: Optional[str] = None,
        chart_y: Optional[str] = None,
        lang: str = "en",
    ) -> DashboardResponse:
        ds: Optional[Dataset] = None
        if dataset_id is not None:
            ds = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
            if ds is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=api_msg("dataset_not_found", lang),
                )
        else:
            rows = self.dataset_repo.list_for_user(user_id, limit=1)
            ds = rows[0] if rows else None

        if ds is None:
            return DashboardResponse(
                dataset_id=None,
                kpis=[],
                line_series=[],
                bar_series=[],
                pie_series=[],
                preview_rows=[],
                date_from=date_from,
                date_to=date_to,
                meta={"message": api_msg("upload_dataset_kpis", lang)},
            )

        df = load_user_dataset_dataframe(ds, date_from, date_to)
        cols_expanded = expand_stale_columns_hint(list(ds.columns) if ds.columns else None)
        custom = self.metric_repo.list_for_user(user_id)
        kpi_raw = build_kpi_list(ds, df, custom)
        kpis = [KpiValue(**k) for k in kpi_raw]
        cx = (chart_x or "").strip() or None
        cy = (chart_y or "").strip() or None
        line, bar, pie = dataframe_for_charts(df, ds, chart_x=cx, chart_y=cy)
        preview = _preview_rows_json(df)
        resolved_x = resolve_date_column(ds, df)
        resolved_y = resolve_value_column(ds, df)

        return DashboardResponse(
            dataset_id=ds.id,
            kpis=kpis,
            line_series=[SeriesPoint(**x) for x in line],
            bar_series=[SeriesPoint(**x) for x in bar],
            pie_series=[SeriesPoint(**x) for x in pie],
            preview_rows=preview,
            date_from=date_from,
            date_to=date_to,
            meta={
                "rows_in_view": len(df),
                "columns": list(df.columns) if not df.empty else (cols_expanded or []),
                "measure_column": resolved_y,
                "time_column": resolved_x,
                "date_filter_column": resolved_x,
                "has_charts": bool(line or bar or pie),
                "chart_x_selected": cx,
                "chart_y_selected": cy,
                "chart_x_effective": cx or resolved_x,
                "chart_y_effective": cy or resolved_y,
            },
        )
