import re
import uuid
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile, status

from app.core.api_messages import api_msg
from app.core.config import get_settings
from app.models.dataset import Dataset
from app.models.user import User
from app.repositories.dataset import DatasetRepository
from app.services.plan import ensure_upload_allowed
from app.services.tabular import (
    coerce_typed_columns,
    read_csv_bytes,
    repair_single_column_dataframe,
)


ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
ALLOWED_MIME = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _sanitize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:200] or "upload"


def _read_dataframe(content: bytes, filename: str, lang: str = "en") -> pd.DataFrame:
    lower = filename.lower()
    if lower.endswith(".csv"):
        df = read_csv_bytes(content)
        return repair_single_column_dataframe(df)
    if lower.endswith(".xlsx"):
        df = pd.read_excel(BytesIO(content), engine="openpyxl")
        return repair_single_column_dataframe(df)
    raise HTTPException(status_code=400, detail=api_msg("unsupported_file_type", lang))


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    df = df.reset_index(drop=True)
    return df


def _detect_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    date_col = None
    value_col = None
    for col in df.columns:
        if date_col is None:
            try:
                s = pd.to_datetime(df[col], errors="coerce")
                if s.notna().sum() >= max(1, len(df) // 2):
                    date_col = col
            except Exception:
                pass
        if value_col is None and pd.api.types.is_numeric_dtype(df[col]):
            value_col = col
    if value_col is None:
        for col in df.columns:
            if col == date_col:
                continue
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().sum() >= max(1, len(df) // 2):
                value_col = col
                df[col] = coerced
                break
    # small tables: accept at least one numeric cell
    if value_col is None:
        for col in df.columns:
            if col == date_col:
                continue
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().any():
                value_col = col
                df[col] = coerced
                break
    return date_col, value_col


class UploadService:
    def __init__(self, repo: DatasetRepository):
        self.repo = repo

    async def process_upload(
        self,
        user: User,
        file: UploadFile,
        display_name: str | None,
        lang: str = "en",
    ) -> Dataset:
        settings = get_settings()
        ensure_upload_allowed(user, self.repo.db, lang)
        user_id = user.id
        if not file.filename:
            raise HTTPException(status_code=400, detail=api_msg("filename_required", lang))
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=api_msg(
                    "invalid_extension",
                    lang,
                    allowed=", ".join(sorted(ALLOWED_EXTENSIONS)),
                ),
            )
        content = await file.read()
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=api_msg("file_too_large", lang, max_mb=str(settings.max_upload_mb)),
            )
        mime = file.content_type or "application/octet-stream"
        if mime not in ALLOWED_MIME and mime != "application/octet-stream":
            # allow octet-stream for some clients
            pass

        try:
            df = _read_dataframe(content, file.filename, lang=lang)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=api_msg("could_not_parse_file", lang, error=str(e)),
            ) from e

        df = _clean_dataframe(df)
        df = repair_single_column_dataframe(df)
        df = coerce_typed_columns(df)
        if df.empty:
            raise HTTPException(status_code=400, detail=api_msg("no_data_rows", lang))

        date_col, value_col = _detect_columns(df)
        # Convert records — limit rows for DB safety
        max_rows = 50_000
        if len(df) > max_rows:
            df = df.head(max_rows)
        records = df.replace({pd.NA: None}).to_dict(orient="records")
        # JSON-serialize friendly
        for row in records:
            for k, v in list(row.items()):
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                elif pd.isna(v):
                    row[k] = None

        upload_root = Path(settings.upload_dir) / str(user_id)
        upload_root.mkdir(parents=True, exist_ok=True)
        uid = uuid.uuid4().hex
        stored_name = f"{uid}{ext}"
        stored_path = str(upload_root / stored_name)
        with open(stored_path, "wb") as f:
            f.write(content)

        name = display_name.strip() if display_name else Path(file.filename).stem
        dataset = Dataset(
            user_id=user_id,
            name=name[:255],
            original_filename=_sanitize_name(file.filename),
            stored_path=stored_path,
            mime_type=mime,
            file_size_bytes=len(content),
            row_count=len(df),
            columns=[str(c) for c in df.columns.tolist()],
            date_column=date_col,
            value_column=value_col,
            cleaned_data=records,
        )
        return self.repo.create(dataset)
