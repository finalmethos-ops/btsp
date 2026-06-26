from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local", alias="ENVIRONMENT")
    app_name: str = Field(default="BTSP", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    secret_key: str = Field(default="change-me-before-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.environment.lower() == "production":
            if self.secret_key == "change-me-before-production":
                raise ValueError("SECRET_KEY must be changed before production deployment")
            if "localhost" in self.cors_origins_raw:
                raise ValueError("CORS_ORIGINS must not use localhost in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
