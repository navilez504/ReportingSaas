import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.db import SessionLocal
from app.services.admin_bootstrap import promote_configured_admins_on_startup
from app.services.reminder_jobs import run_usage_and_trial_emails
from app.services.stripe_reconcile import reconcile_stripe_subscriptions
from app.routers import admin, auth, billing, dashboard, reports, upload, users, webhooks

logger = logging.getLogger(__name__)

_last_stripe_reconcile_at: float = time.time()


async def _reminder_loop() -> None:
    global _last_stripe_reconcile_at
    while True:
        db = SessionLocal()
        try:
            run_usage_and_trial_emails(db)
        except Exception:
            logger.exception("Reminder email job failed")
        finally:
            db.close()

        now = time.time()
        if now - _last_stripe_reconcile_at >= 86400:
            db_r = SessionLocal()
            try:
                n = reconcile_stripe_subscriptions(db_r, get_settings())
                _last_stripe_reconcile_at = now
                if n:
                    logger.info("Stripe reconciliation updated %s user(s)", n)
            except Exception:
                logger.exception("Stripe reconciliation job failed")
            finally:
                db_r.close()

        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.smtp_ready:
        logger.info("SMTP is configured (host=%s port=%s)", settings.smtp_host, settings.smtp_port)
    else:
        logger.warning(
            "SMTP is not fully configured (need SMTP_HOST, SMTP_USER, SMTP_PASSWORD). "
            "Outbound emails will not be sent until those are set."
        )
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        promote_configured_admins_on_startup(db, settings)
    except Exception:
        logger.exception("Could not apply ADMIN_EMAILS promotions on startup")
        db.rollback()
    finally:
        db.close()

    reminder_task = asyncio.create_task(_reminder_loop())
    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.debug)
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(billing.router, prefix="/api")
    app.include_router(upload.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(webhooks.router, prefix="/api")

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    if not settings.debug:
        @app.exception_handler(Exception)
        async def unhandled(_: Request, exc: Exception):
            logger.exception("Unhandled error: %s", exc)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

    @app.get("/health")
    def health():
        s = get_settings()
        return {
            "status": "ok",
            "smtp_configured": s.smtp_ready,
        }

    return app


app = create_app()
