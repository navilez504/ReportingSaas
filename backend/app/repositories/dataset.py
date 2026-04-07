from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.dataset import Dataset


class DatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_for_user(self, dataset_id: int, user_id: int) -> Optional[Dataset]:
        return (
            self.db.query(Dataset)
            .filter(Dataset.id == dataset_id, Dataset.user_id == user_id)
            .first()
        )

    def list_for_user(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Dataset]:
        return (
            self.db.query(Dataset)
            .filter(Dataset.user_id == user_id)
            .order_by(Dataset.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_for_user(self, user_id: int) -> int:
        return int(self.db.query(func.count(Dataset.id)).filter(Dataset.user_id == user_id).scalar() or 0)

    def count_for_user_between(self, user_id: int, start: datetime, end: datetime) -> int:
        return int(
            self.db.query(func.count(Dataset.id))
            .filter(Dataset.user_id == user_id, Dataset.created_at >= start, Dataset.created_at < end)
            .scalar()
            or 0
        )

    def create(self, dataset: Dataset) -> Dataset:
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def update(self, dataset: Dataset) -> Dataset:
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def delete(self, dataset: Dataset) -> None:
        self.db.delete(dataset)
        self.db.commit()
