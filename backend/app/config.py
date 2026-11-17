"""Application configuration management using pydantic-settings."""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Snack Overflow environment settings."""

    DATABASE_URL: str
    TEST_DATABASE_URL: Optional[str] = None
    JWT_SECRET: str = "change-this-in-production-snack-overflow-secret"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Allow comma-separated strings or existing lists for CORS origins; disallow wildcard '*'."""
        origins: List[str]
        if isinstance(v, str):
            origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = [str(i).strip() for i in v if str(i).strip()]
        else:
            origins = []
        filtered = [origin for origin in origins if origin != "*"]
        return filtered or ["http://localhost:5173", "http://localhost:3000"]

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Normalize database URL for SQLAlchemy 2.0 with psycopg2.
        Supabase URLs provide 'postgresql://' or 'postgres://'.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def sqlalchemy_test_database_url(self) -> Optional[str]:
        """Normalize test database URL for SQLAlchemy 2.0 with psycopg2."""
        if not self.TEST_DATABASE_URL:
            return None
        url = self.TEST_DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


@lru_cache()
def get_settings() -> Settings:
    """Return cached instance of application settings."""
    return Settings()
