from functools import lru_cache
from typing import List

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):   
    database_url: str = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    debug: bool = Field(default=False, alias="DEBUG")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="COSTA_",
        extra="ignore",
    )

    # General
    ENV: str = Field("dev", description="Environment name: dev/stage/prod")
    DEBUG: bool = False
    PROJECT_NAME: str = "costa-backend"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: AnyUrl

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(default_factory=list)

    # Security (example)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SECRET_KEY: str

    # Logging
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

