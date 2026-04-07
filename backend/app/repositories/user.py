from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.report import Report
from app.models.user import PlanType, User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower()).first()

    def create(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        role_value: str = UserRole.USER.value,
        plan: str = PlanType.TRIAL.value,
        trial_started_at: datetime | None = None,
        is_active: bool = True,
        organization_id: int | None = None,
    ) -> User:
        if plan == PlanType.TRIAL.value and trial_started_at is None:
            trial_started_at = datetime.utcnow()
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=role_value,
            plan=plan,
            trial_started_at=trial_started_at,
            is_active=is_active,
            organization_id=organization_id,
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(user)
        return user

    def update(self, user: User, full_name: str | None) -> User:
        if full_name is not None:
            user.full_name = full_name
        self.db.commit()
        self.db.refresh(user)
        return user

    def storage_bytes_breakdown(self, user_id: int) -> tuple[int, int]:
        """Uploaded dataset files + generated report PDFs (DB-tracked sizes)."""
        ds_b = int(
            self.db.query(func.coalesce(func.sum(Dataset.file_size_bytes), 0))
            .filter(Dataset.user_id == user_id)
            .scalar()
            or 0
        )
        rp_b = int(
            self.db.query(func.coalesce(func.sum(Report.file_size_bytes), 0))
            .filter(Report.user_id == user_id)
            .scalar()
            or 0
        )
        return ds_b, rp_b

    def list_for_admin(
        self,
        plan: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[tuple[User, int, int, int]]:
        fc_subq = (
            self.db.query(Dataset.user_id.label("uid"), func.count(Dataset.id).label("fc"))
            .group_by(Dataset.user_id)
            .subquery()
        )
        ds_sum = (
            self.db.query(
                Dataset.user_id.label("uid"),
                func.coalesce(func.sum(Dataset.file_size_bytes), 0).label("ds_bytes"),
            )
            .group_by(Dataset.user_id)
            .subquery()
        )
        rp_sum = (
            self.db.query(
                Report.user_id.label("uid"),
                func.coalesce(func.sum(Report.file_size_bytes), 0).label("rp_bytes"),
            )
            .group_by(Report.user_id)
            .subquery()
        )
        q = (
            self.db.query(
                User,
                func.coalesce(fc_subq.c.fc, 0),
                func.coalesce(ds_sum.c.ds_bytes, 0),
                func.coalesce(rp_sum.c.rp_bytes, 0),
            )
            .outerjoin(fc_subq, User.id == fc_subq.c.uid)
            .outerjoin(ds_sum, User.id == ds_sum.c.uid)
            .outerjoin(rp_sum, User.id == rp_sum.c.uid)
        )
        if plan:
            q = q.filter(User.plan == plan)
        if is_active is not None:
            q = q.filter(User.is_active == is_active)
        q = q.order_by(User.id)
        rows = q.offset(skip).limit(limit).all()
        return [(u, int(fc or 0), int(ds_b or 0), int(rp_b or 0)) for u, fc, ds_b, rp_b in rows]

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
