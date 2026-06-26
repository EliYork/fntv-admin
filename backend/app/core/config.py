from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "fntv-admin"
    app_env: str = "production"
    app_secret_key: str = Field(default="change-me")
    fntv_db_path: Path = Path("/fntv/trimmedia.db")
    admin_db_path: Path = Path("/data/admin.db")
    log_dir: Path = Path("/data/logs")
    cache_dir: Path = Path("/data/cache")
    backup_dir: Path = Path("/data/backup")
    database_snapshot_enabled: bool = True
    database_snapshot_interval_seconds: int = 60
    default_page_size: int = 20
    log_retention_days: int = 14
    access_token_expire_minutes: int = 60 * 24

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def data_dir(self) -> Path:
        return self.admin_db_path.parent

    @property
    def sqlite_admin_url(self) -> str:
        return f"sqlite:///{self.admin_db_path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

