from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="BEACH_API_")

    supabase_url: str = ""
    supabase_key: str = ""
    noaa_http_timeout_seconds: float = 10.0


settings = Settings()
