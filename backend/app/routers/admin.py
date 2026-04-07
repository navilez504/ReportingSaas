import csv
import html as html_lib
import io
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.core.api_messages import api_msg
from app.core.deps import get_db, get_locale, require_admin
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.audit_log import AuditLogRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.admin import AdminStatusBody, AdminUpgradeBody, AdminUserDetailResponse, AdminUserListItem
from app.schemas.admin_sessions import AdminAuditLogOut, AdminSessionOut
from app.services.admin_users import AdminUserService
from app.services.audit_service import record_audit
from app.utils.session_active import session_row_is_active

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserListItem])
def list_users(
    db: Session = Depends(get_db),
    __admin: User = Depends(require_admin),
    lang: str = Depends(get_locale),
    plan: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return AdminUserService(db).list_users(lang, plan, is_active, skip, limit)


@router.get("/users/export")
def export_users(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    plan: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    format: Literal["csv", "pdf"] = Query("csv"),
):
    svc = AdminUserService(db)
    rows = svc.list_users("en", plan, is_active, 0, 50_000)
    record_audit(
        db,
        request,
        actor=admin,
        action="admin.users.export",
        resource_type="user",
        details={"format": format, "plan": plan, "is_active": is_active, "row_count": len(rows)},
    )
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "id",
                "email",
                "full_name",
                "plan",
                "trial_started_at",
                "is_active",
                "organization_id",
                "files_uploaded",
                "storage_datasets_bytes",
                "storage_reports_bytes",
                "storage_bytes_total",
                "subscription_status",
                "stripe_customer_id",
                "stripe_subscription_id",
                "created_at",
            ],
        )
        for r in rows:
            w.writerow(
                [
                    r.id,
                    r.email,
                    r.full_name,
                    r.plan,
                    r.trial_started_at.isoformat() if r.trial_started_at else "",
                    r.is_active,
                    r.organization_id or "",
                    r.files_uploaded,
                    r.storage_datasets_bytes,
                    r.storage_reports_bytes,
                    r.storage_bytes_total,
                    r.subscription_status or "",
                    r.stripe_customer_id or "",
                    r.stripe_subscription_id or "",
                    r.created_at.isoformat(),
                ],
            )
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="users_export.csv"'},
        )

    rows_html = "".join(
        "<tr>"
        f"<td>{r.id}</td><td>{html_lib.escape(r.email)}</td><td>{html_lib.escape(r.full_name)}</td>"
        f"<td>{html_lib.escape(r.plan)}</td><td>{r.is_active}</td><td>{r.files_uploaded}</td>"
        f"<td>{r.storage_bytes_total}</td>"
        "</tr>"
        for r in rows
    )
    html_doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Users</title>
    <style>body{{font-family:sans-serif}} table{{border-collapse:collapse;width:100%}}
    th,td{{border:1px solid #ccc;padding:6px;text-align:left}} th{{background:#f4f4f4}}</style>
    </head><body><h1>Users export</h1><table>
    <thead><tr><th>ID</th><th>Email</th><th>Name</th><th>Plan</th><th>Active</th><th>Files</th><th>Storage (bytes)</th></tr></thead>
    <tbody>{rows_html}</tbody></table></body></html>"""
    pdf = HTML(string=html_doc).write_pdf()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="users_export.pdf"'},
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    __admin: User = Depends(require_admin),
    lang: str = Depends(get_locale),
):
    return AdminUserService(db).get_user(user_id, lang)


@router.post("/users/{user_id}/upgrade", response_model=AdminUserDetailResponse)
def upgrade_user(
    user_id: int,
    body: AdminUpgradeBody,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    lang: str = Depends(get_locale),
):
    svc = AdminUserService(db)
    svc.upgrade_plan(user_id, body.plan, body.organization_name, lang, actor_email=admin.email)
    record_audit(
        db,
        request,
        actor=admin,
        action="admin.user.plan_change",
        resource_type="user",
        resource_id=str(user_id),
        details={"plan": body.plan, "organization_name": body.organization_name},
    )
    return svc.get_user(user_id, lang)


@router.post("/users/{user_id}/renew", response_model=AdminUserDetailResponse)
def renew_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    lang: str = Depends(get_locale),
):
    svc = AdminUserService(db)
    svc.renew_subscription(user_id, lang, actor_email=admin.email)
    record_audit(
        db,
        request,
        actor=admin,
        action="admin.user.renew",
        resource_type="user",
        resource_id=str(user_id),
        details={},
    )
    return svc.get_user(user_id, lang)


@router.post("/users/{user_id}/status", response_model=AdminUserDetailResponse)
def set_user_status(
    user_id: int,
    body: AdminStatusBody,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    lang: str = Depends(get_locale),
):
    svc = AdminUserService(db)
    svc.set_active(user_id, body.active, lang, actor_email=admin.email)
    record_audit(
        db,
        request,
        actor=admin,
        action="admin.user.status",
        resource_type="user",
        resource_id=str(user_id),
        details={"active": body.active},
    )
    return svc.get_user(user_id, lang)


@router.get("/sessions", response_model=list[AdminSessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    __admin: User = Depends(require_admin),
    user_id: Optional[int] = Query(None),
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    rows = UserSessionRepository(db).list_for_admin(
        user_id=user_id,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )
    return [
        AdminSessionOut(
            id=s.id,
            user_id=s.user_id,
            user_email=email,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            expires_at=s.expires_at,
            revoked_at=s.revoked_at,
            is_active=session_row_is_active(s),
            ip_address=s.ip_address or "",
            user_agent=s.user_agent or "",
        )
        for s, email in rows
    ]


@router.post("/sessions/{session_id}/revoke")
def admin_revoke_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    lang: str = Depends(get_locale),
):
    row = db.query(UserSession).filter(UserSession.id == session_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=api_msg("session_not_found", lang))
    sess_repo = UserSessionRepository(db)
    if row.revoked_at is None:
        sess_repo.revoke(row)
    record_audit(
        db,
        request,
        actor=admin,
        action="admin.session.revoke",
        resource_type="user_session",
        resource_id=str(session_id),
        details={"target_user_id": row.user_id},
    )
    return {"ok": True}


@router.get("/audit", response_model=list[AdminAuditLogOut])
def list_audit(
    db: Session = Depends(get_db),
    __admin: User = Depends(require_admin),
    actor_id: Optional[int] = Query(None),
    action_prefix: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    rows = AuditLogRepository(db).list_for_admin(
        actor_id=actor_id,
        action_prefix=action_prefix,
        skip=skip,
        limit=limit,
    )
    return [
        AdminAuditLogOut(
            id=log.id,
            created_at=log.created_at,
            actor_user_id=log.actor_user_id,
            actor_email=email,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address or "",
        )
        for log, email in rows
    ]
