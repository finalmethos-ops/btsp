from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local", alias="ENVIRONMENT")
    app_name: str = Field(default="BTSP", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    secret_key: str = Field(default="change-me-before-production", alias="SECRET_KEY")
    bootstrap_admin_token: str = Field(
        default="change-me-before-bootstrap", alias="BOOTSTRAP_ADMIN_TOKEN"
    )
    access_token_expire_minutes: int = Field(
        default=60, ge=5, le=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=14, ge=1, le=90, alias="REFRESH_TOKEN_EXPIRE_DAYS"
    )
    password_reset_expire_minutes: int = Field(
        default=30, ge=5, le=240, alias="PASSWORD_RESET_EXPIRE_MINUTES"
    )
    login_lockout_threshold: int = Field(default=5, ge=3, le=20, alias="LOGIN_LOCKOUT_THRESHOLD")
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440, alias="LOGIN_LOCKOUT_MINUTES")
    login_rate_limit_window_seconds: int = Field(
        default=300, ge=60, le=3600, alias="LOGIN_RATE_LIMIT_WINDOW_SECONDS"
    )
    login_rate_limit_email_attempts: int = Field(
        default=8, ge=3, le=100, alias="LOGIN_RATE_LIMIT_EMAIL_ATTEMPTS"
    )
    login_rate_limit_host_attempts: int = Field(
        default=40, ge=10, le=1000, alias="LOGIN_RATE_LIMIT_HOST_ATTEMPTS"
    )
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    brave_search_api_key: str | None = Field(default=None, alias="BRAVE_SEARCH_API_KEY")
    routing_api_url: str = Field(
        default="https://router.project-osrm.org/route/v1/driving",
        alias="ROUTING_API_URL",
    )
    geocoding_api_url: str = Field(
        default="https://nominatim.openstreetmap.org/search",
        alias="GEOCODING_API_URL",
    )
    notification_email_enabled: bool = Field(default=False, alias="NOTIFICATION_EMAIL_ENABLED")
    notification_webhook_enabled: bool = Field(default=False, alias="NOTIFICATION_WEBHOOK_ENABLED")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, ge=1, le=65535, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="no-reply@btsp.local", alias="SMTP_FROM")
    notification_delivery_timeout_seconds: int = Field(
        default=10, ge=1, le=60, alias="NOTIFICATION_DELIVERY_TIMEOUT_SECONDS"
    )
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    attachment_storage_path: str = Field(
        default="/data/attachments", alias="ATTACHMENT_STORAGE_PATH"
    )
    attachment_max_bytes: int = Field(default=20 * 1024 * 1024, alias="ATTACHMENT_MAX_BYTES")
    purchase_order_export_path: str = Field(
        default="/data/purchase-order-exports", alias="PURCHASE_ORDER_EXPORT_PATH"
    )
    analytics_report_path: str = Field(
        default="/data/analytics-reports", alias="ANALYTICS_REPORT_PATH"
    )
    invoice_intake_storage_path: str = Field(
        default="/data/invoice-intake", alias="INVOICE_INTAKE_STORAGE_PATH"
    )
    critical_notification_threshold: int = Field(
        default=100, ge=1, alias="CRITICAL_NOTIFICATION_THRESHOLD"
    )
    critical_operational_threshold: int = Field(
        default=10, ge=1, alias="CRITICAL_OPERATIONAL_THRESHOLD"
    )
    stale_notification_after_minutes: int = Field(
        default=15, ge=1, alias="STALE_NOTIFICATION_AFTER_MINUTES"
    )
    event_task_reminder_interval_seconds: int = Field(
        default=300,
        ge=30,
        le=3600,
        alias="EVENT_TASK_REMINDER_INTERVAL_SECONDS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.environment.lower() == "production":
            # These public sentinel values are rejected configuration, not credentials.
            if self.secret_key == "change-me-before-production":  # nosec B105
                raise ValueError("SECRET_KEY must be changed before production deployment")
            if len(self.secret_key.encode("utf-8")) < 32:
                raise ValueError("SECRET_KEY must be at least 32 bytes in production")
            if self.bootstrap_admin_token == "change-me-before-bootstrap":  # nosec B105
                raise ValueError(
                    "BOOTSTRAP_ADMIN_TOKEN must be changed before production deployment"
                )
            if "localhost" in self.cors_origins_raw:
                raise ValueError("CORS_ORIGINS must not use localhost in production")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS must not allow wildcard origins in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
