from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")

    data_dir: Path = PROJECT_DIR / "data"
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("data_dir")
    @classmethod
    def _resolve_relative_to_project(cls, value: Path) -> Path:
        return value if value.is_absolute() else (PROJECT_DIR / value).resolve()

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "app.sqlite"

    @property
    def duckdb_path(self) -> Path:
        return self.data_dir / "warehouse.duckdb"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
