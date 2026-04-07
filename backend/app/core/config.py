from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from predictable paths (not only CWD): project root, then backend/ (later file wins on duplicate keys).
# Docker/production still overrides via real environment variables.
_CONFIG_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _CONFIG_DIR.parent.parent
_PROJECT_ROOT = _BACKEND_ROOT.parent


def _env_file_paths() -> tuple[str, ...]:
    paths: list[Path] = []
    # Later files override earlier (pydantic-settings); project root wins over backend/.env.
    for p in (_BACKEND_ROOT / ".env", _PROJECT_ROOT / ".env"):
        if p.is_file():
            paths.append(p)
    return tuple(str(p) for p in paths)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file_paths() or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Reporting SaaS API"
    debug: bool = False
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    database_url: str = "postgresql://reporting:reporting@localhost:5432/reporting_db"

    cors_origins: str = "http://localhost,http://localhost:5173,http://127.0.0.1:5173"

    upload_dir: str = "./uploads"
    reports_dir: str = "./reports"
    max_upload_mb: int = 25

    # Stripe (Checkout + webhooks). Price IDs from Dashboard → Products → Price API IDs.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_enterprise: str = ""

    # Browser-visible app URL for Checkout success/cancel (no trailing slash).
    public_app_url: str = "http://localhost"

    # Outbound email (trial reminders, payment notices). If smtp_host is empty, bodies are logged only.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    # If True, use implicit TLS (e.g. port 465). If False, use STARTTLS on smtp_port (e.g. 587).
    smtp_use_ssl: bool = False

    # Comma-separated emails that receive admin role (Admin API + panel). Case-insensitive.
    admin_emails: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_emails_lower(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def smtp_ready(self) -> bool:
        """True when SMTP is configured enough to attempt a real send (not log-only)."""
        return bool((self.smtp_host or "").strip() and (self.smtp_user or "").strip() and (self.smtp_password or "").strip())

    @field_validator("smtp_host", "smtp_user", "smtp_password", "smtp_from", mode="before")
    @classmethod
    def strip_smtp_strings(cls, v: str) -> str:
        if v is None:
            return ""
        return str(v).strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
