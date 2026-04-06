from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
