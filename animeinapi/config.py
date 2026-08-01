from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANIMEIN_", env_file=".env", extra="ignore")

    base_url: str = "https://animeinweb.com"
    proxy_secret: str = "animein-secure-proxy-key-123"
    timeout: float = 15.0
    retries: int = 2
    log_level: str = "INFO"

    @property
    def proxy_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/api/proxy"


@lru_cache
def get_settings() -> Settings:
    return Settings()
