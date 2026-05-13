from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class _Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://elbil:secret@localhost:5432/elbilspriser"


settings = _Settings()
