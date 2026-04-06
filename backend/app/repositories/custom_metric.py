from typing import Optional

from sqlalchemy.orm import Session

from app.models.custom_metric import CustomMetric


class CustomMetricRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: int) -> list[CustomMetric]:
        return self.db.query(CustomMetric).filter(CustomMetric.user_id == user_id).all()

    def create(self, metric: CustomMetric) -> CustomMetric:
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def delete(self, metric_id: int, user_id: int) -> bool:
        m = (
            self.db.query(CustomMetric)
            .filter(CustomMetric.id == metric_id, CustomMetric.user_id == user_id)
            .first()
        )
        if not m:
            return False
        self.db.delete(m)
        self.db.commit()
        return True
