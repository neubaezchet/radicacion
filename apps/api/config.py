"""Configuración desde entorno (Railway, local, Docker)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "*"
    """Lista separada por comas, o `*` en desarrollo."""

    radicacion_api_key: str | None = None
    """Si se define, las rutas sensibles exigen header X-Radicacion-Key."""

    mock_radicacion: bool = False
    """Si True, el bot SURA devuelve un resultado simulado (útil sin Playwright)."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
