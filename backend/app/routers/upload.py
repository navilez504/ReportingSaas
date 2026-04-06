from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.api_messages import api_msg, parse_accept_language
from app.core.deps import get_current_user, get_db, get_locale
from app.models.user import User
from app.repositories.dataset import DatasetRepository
from app.schemas.dataset import DatasetDetailOut, DatasetOut, UploadMetaUpdate
from app.services.upload import UploadService

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
):
    lang = parse_accept_language(accept_language)
    repo = DatasetRepository(db)
    svc = UploadService(repo)
    ds = await svc.process_upload(current.id, file, name, lang=lang)
    return DatasetOut.model_validate(ds)


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    repo = DatasetRepository(db)
    rows = repo.list_for_user(current.id)
    return [DatasetOut.model_validate(r) for r in rows]


@router.get("/datasets/{dataset_id}", response_model=DatasetDetailOut)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    repo = DatasetRepository(db)
    ds = repo.get_by_id_for_user(dataset_id, current.id)
    if ds is None:
        raise HTTPException(status_code=404, detail=api_msg("dataset_not_found", lang))
    sample = ds.cleaned_data[:50] if ds.cleaned_data else []
    base = DatasetOut.model_validate(ds)
    return DatasetDetailOut(**base.model_dump(), sample_rows=sample)


@router.patch("/datasets/{dataset_id}", response_model=DatasetOut)
def update_dataset_meta(
    dataset_id: int,
    data: UploadMetaUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    repo = DatasetRepository(db)
    ds = repo.get_by_id_for_user(dataset_id, current.id)
    if ds is None:
        raise HTTPException(status_code=404, detail=api_msg("dataset_not_found", lang))
    if data.name is not None:
        ds.name = data.name[:255]
    if data.date_column is not None:
        ds.date_column = data.date_column
    if data.value_column is not None:
        ds.value_column = data.value_column
    ds = repo.update(ds)
    return DatasetOut.model_validate(ds)


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    lang: str = Depends(get_locale),
):
    repo = DatasetRepository(db)
    ds = repo.get_by_id_for_user(dataset_id, current.id)
    if ds is None:
        raise HTTPException(status_code=404, detail=api_msg("dataset_not_found", lang))
    if ds.stored_path:
        try:
            import os

            if os.path.isfile(ds.stored_path):
                os.remove(ds.stored_path)
        except OSError:
            pass
    repo.delete(ds)
    return None
