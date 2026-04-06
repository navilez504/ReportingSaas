from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DatasetOut(BaseModel):
    id: int
    user_id: int
    name: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    row_count: int
    columns: list[str]
    date_column: Optional[str]
    value_column: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetDetailOut(DatasetOut):
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)


class UploadMetaUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date_column: Optional[str] = None
    value_column: Optional[str] = None
