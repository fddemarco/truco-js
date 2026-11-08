from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")

    data_dir: Path = PROJECT_DIR / "data"
    # The database. Unset: SQLite in DATA_DIR/app.sqlite (local). On Vercel: Postgres (Neon's
    # pooled URL); `postgres://` URLs are taken as they come from the provider.
    database_url: str | None = None
    cors_origins: list[str] = ["http://localhost:5173"]
    # Logging (see app/observability.py): level, console format, and the JSON-lines file in
    # DATA_DIR/logs/app.jsonl.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["console", "json"] = "console"
    log_file: bool = True

    @field_validator("data_dir")
    @classmethod
    def _resolve_relative_to_project(cls, value: Path) -> Path:
        return value if value.is_absolute() else (PROJECT_DIR / value).resolve()

    @field_validator("database_url")
    @classmethod
    def _sqlalchemy_driver(cls, value: str | None) -> str | None:
        if not value:
            return None
        for scheme in ("postgres://", "postgresql://"):
            if value.startswith(scheme):
                return "postgresql+psycopg://" + value.removeprefix(scheme)
        return value

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "app.sqlite"

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{self.sqlite_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
