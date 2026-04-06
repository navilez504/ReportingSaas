import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.routers import auth, dashboard, reports, upload, users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)
    yield


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
    app.include_router(upload.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")

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
        return {"status": "ok"}

    return app


app = create_app()
