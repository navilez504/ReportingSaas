from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    dataset_id: Optional[int] = None
    language: Literal["en", "es"] = "en"


class ReportOut(BaseModel):
    id: int
    user_id: int
    dataset_id: Optional[int]
    title: str
    file_size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}
