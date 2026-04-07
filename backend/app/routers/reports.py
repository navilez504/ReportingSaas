from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.api_messages import api_msg
from app.core.deps import get_current_user, get_db, get_locale
from app.models.user import User
from app.repositories.dataset import DatasetRepository
from app.repositories.custom_metric import CustomMetricRepository
from app.repositories.report import ReportRepository
from app.schemas.report import ReportCreate, ReportOut
from app.services.dashboard import DashboardService
from app.services.plan import ensure_account_can_write, ensure_plan_feature
from app.services.report_pdf import ReportPdfService

router = APIRouter(prefix="/reports", tags=["reports"])


def _pdf_service(db: Session) -> ReportPdfService:
    dash = DashboardService(DatasetRepository(db), CustomMetricRepository(db))
    return ReportPdfService(ReportRepository(db), dash)


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    ensure_account_can_write(current, lang)
    ensure_plan_feature(current, "pdf_reports", lang)
    svc = _pdf_service(db)
    report = svc.generate_pdf(
        current.id,
        data.title,
        data.dataset_id,
        language=data.language,
    )
    return ReportOut.model_validate(report)


@router.get("", response_model=list[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    repo = ReportRepository(db)
    rows = repo.list_for_user(current.id)
    return [ReportOut.model_validate(r) for r in rows]


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    repo = ReportRepository(db)
    r = repo.get_by_id_for_user(report_id, current.id)
    if r is None:
        raise HTTPException(status_code=404, detail=api_msg("report_not_found", lang))
    path = Path(r.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=api_msg("file_missing_server", lang))
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"report_{r.id}.pdf",
    )
