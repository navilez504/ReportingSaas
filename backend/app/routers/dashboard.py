from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.api_messages import api_msg
from app.core.deps import get_current_user, get_db, get_locale
from app.models.user import User
from app.repositories.custom_metric import CustomMetricRepository
from app.repositories.dataset import DatasetRepository
from app.schemas.bi import BIChartsResponse, BIInsightsResponse, BISummaryResponse
from app.schemas.dashboard import CustomMetricCreate, CustomMetricOut, DashboardResponse
from app.schemas.plan_summary import PlanSummaryResponse
from app.services.plan import build_plan_summary, ensure_plan_feature
from app.models.custom_metric import CustomMetric
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _dash_service(db: Session) -> DashboardService:
    return DashboardService(DatasetRepository(db), CustomMetricRepository(db))


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
    dataset_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    chart_x: Optional[str] = Query(None, description="Column for chart X (time or categories)"),
    chart_y: Optional[str] = Query(None, description="Numeric column for chart Y"),
):
    svc = _dash_service(db)
    return svc.get_dashboard(
        current.id, dataset_id, date_from, date_to, chart_x=chart_x, chart_y=chart_y, lang=lang
    )


@router.get("/plan-summary", response_model=PlanSummaryResponse)
def get_plan_summary(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    """Subscription and upload-limit KPIs (BI metrics remain at GET /dashboard/summary)."""
    return PlanSummaryResponse.model_validate(build_plan_summary(current, db, lang))


@router.get("/summary", response_model=BISummaryResponse)
def get_bi_summary(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
    dataset_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    ensure_plan_feature(current, "bi_summary", lang)
    return _dash_service(db).get_bi_summary(current.id, dataset_id, date_from, date_to, lang=lang)


@router.get("/charts", response_model=BIChartsResponse)
def get_bi_charts(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
    dataset_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    ensure_plan_feature(current, "bi_charts", lang)
    return _dash_service(db).get_bi_charts(current.id, dataset_id, date_from, date_to, lang=lang)


@router.get("/insights", response_model=BIInsightsResponse)
def get_bi_insights(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
    dataset_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    ensure_plan_feature(current, "bi_insights", lang)
    return _dash_service(db).get_bi_insights(current.id, dataset_id, date_from, date_to, lang=lang)


@router.post("/metrics", response_model=CustomMetricOut, status_code=201)
def create_metric(
    data: CustomMetricCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    repo = CustomMetricRepository(db)
    m = CustomMetric(
        user_id=current.id,
        name=data.name,
        metric_type=data.metric_type,
        column_name=data.column_name,
    )
    m = repo.create(m)
    return CustomMetricOut.model_validate(m)


@router.get("/metrics", response_model=list[CustomMetricOut])
def list_metrics(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    repo = CustomMetricRepository(db)
    rows = repo.list_for_user(current.id)
    return [CustomMetricOut.model_validate(r) for r in rows]


@router.delete("/metrics/{metric_id}", status_code=204)
def delete_metric(
    metric_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    repo = CustomMetricRepository(db)
    if not repo.delete(metric_id, current.id):
        raise HTTPException(status_code=404, detail=api_msg("metric_not_found", lang))
    return None
