import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.api_messages import api_msg
from app.core.config import get_settings
from app.models.organization import Organization
from app.models.user import PlanType, User
from app.repositories.dataset import DatasetRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.admin import AdminUserDetailResponse, AdminUserListItem
from app.schemas.plan_summary import PlanSummaryResponse
from app.services.plan import build_plan_summary, normalize_plan
from app.services.system_notifications import (
    notify_account_status_change,
    notify_admin_plan_change,
    notify_trial_renewed,
    notify_user_plan_change,
)

logger = logging.getLogger(__name__)


class AdminUserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def list_users(
        self,
        lang: str,
        plan: str | None,
        is_active: bool | None,
        skip: int,
        limit: int,
    ) -> list[AdminUserListItem]:
        if plan:
            try:
                normalize_plan(plan)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=api_msg("invalid_plan", lang),
                )
        rows = self.users.list_for_admin(plan=plan, is_active=is_active, skip=skip, limit=limit)
        return [
            AdminUserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role_enum,
                plan=u.plan,
                trial_started_at=u.trial_started_at,
                is_active=u.is_active,
                organization_id=u.organization_id,
                files_uploaded=fc,
                storage_datasets_bytes=ds_b,
                storage_reports_bytes=rp_b,
                storage_bytes_total=ds_b + rp_b,
                subscription_status=u.subscription_status,
                stripe_customer_id=u.stripe_customer_id,
                stripe_subscription_id=u.stripe_subscription_id,
                created_at=u.created_at,
            )
            for u, fc, ds_b, rp_b in rows
        ]

    def get_user(self, user_id: int, lang: str) -> AdminUserDetailResponse:
        u = self.users.get_by_id(user_id)
        if u is None:
            raise HTTPException(status_code=404, detail=api_msg("user_not_found", lang))
        fc = DatasetRepository(self.db).count_for_user(u.id)
        ds_b, rp_b = self.users.storage_bytes_breakdown(u.id)
        base = AdminUserListItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role_enum,
            plan=u.plan,
            trial_started_at=u.trial_started_at,
            is_active=u.is_active,
            organization_id=u.organization_id,
            files_uploaded=fc,
            storage_datasets_bytes=ds_b,
            storage_reports_bytes=rp_b,
            storage_bytes_total=ds_b + rp_b,
            subscription_status=u.subscription_status,
            stripe_customer_id=u.stripe_customer_id,
            stripe_subscription_id=u.stripe_subscription_id,
            created_at=u.created_at,
        )
        summary = PlanSummaryResponse.model_validate(build_plan_summary(u, self.db, lang))
        return AdminUserDetailResponse(**base.model_dump(), plan_summary=summary)

    def upgrade_plan(
        self,
        user_id: int,
        body_plan: str,
        organization_name: str | None,
        lang: str,
        actor_email: str | None = None,
    ) -> User:
        try:
            new_plan = normalize_plan(body_plan)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_msg("invalid_plan", lang),
            )
        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail=api_msg("user_not_found", lang))

        old_plan = user.plan

        if new_plan == PlanType.ENTERPRISE.value:
            if user.organization_id is None:
                name = (organization_name or f"{user.full_name or user.email}").strip()[:255] or "Organization"
                org = Organization(name=name, owner_user_id=user.id)
                self.db.add(org)
                self.db.flush()
                user.organization_id = org.id
        elif user.organization_id is not None:
            user.organization_id = None

        user.plan = new_plan
        if new_plan == PlanType.TRIAL.value:
            user.trial_started_at = datetime.utcnow()
        else:
            user.trial_started_at = None

        user = self.users.save(user)
        if old_plan != new_plan:
            settings = get_settings()
            try:
                notify_user_plan_change(settings, user, old_plan, new_plan, action="admin panel")
                notify_admin_plan_change(
                    settings,
                    user,
                    old_plan,
                    new_plan,
                    actor_email=actor_email,
                    action="plan change",
                )
            except Exception:
                logger.exception("Plan change notifications failed for user_id=%s", user_id)
        return user

    def renew_subscription(self, user_id: int, lang: str, actor_email: str | None = None) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail=api_msg("user_not_found", lang))
        if user.plan == PlanType.TRIAL.value:
            user.trial_started_at = datetime.utcnow()
        user = self.users.save(user)
        if user.plan == PlanType.TRIAL.value:
            try:
                notify_trial_renewed(get_settings(), user, actor_email=actor_email)
            except Exception:
                logger.exception("Trial renew notifications failed for user_id=%s", user_id)
        return user

    def set_active(self, user_id: int, active: bool, lang: str, actor_email: str | None = None) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail=api_msg("user_not_found", lang))
        old_active = user.is_active
        user.is_active = active
        user = self.users.save(user)
        if active is False:
            UserSessionRepository(self.db).revoke_all_for_user(user_id)
        if old_active != active:
            try:
                notify_account_status_change(get_settings(), user, active=active, actor_email=actor_email)
            except Exception:
                logger.exception("Account status notifications failed for user_id=%s", user_id)
        return user
