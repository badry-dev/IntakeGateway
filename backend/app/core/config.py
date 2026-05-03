from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "intake-gateway"
    APP_DATABASE_URL: str = "sqlite:///./intakegateway_app.db"
    APP_ENV: str = "dev"
    APP_LOG_LEVEL: str = "INFO"
    APP_TIMEZONE: str = "Asia/Riyadh"

    ORACLE_USER: str = ""
    ORACLE_PASSWORD: str = ""
    ORACLE_HOST: str = ""
    ORACLE_PORT: int = 1521
    ORACLE_SERVICE_NAME: str = ""
    ORACLE_DSN: str | None = None  # host:port/service_name

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    HTTP_TIMEOUT_SECONDS: int = 30
    HTTP_MAX_RESPONSE_MB: int = 10

    OAUTH_TOKEN_REFRESH_SKEW_SECONDS: int = 60
    OAUTH_REFRESH_LOCK_TIMEOUT_SECONDS: int = 30
    HTTP_RETRY_AFTER_MAX_SECONDS: int = 120
    HTTP_RATE_LIMIT_DEFAULT_RETRIES: int = 5
    BACKFILL_MAX_WINDOW_DAYS: int = 366

    SECRET_KEY: str = "dev-secret"
    FRONTEND_URL: str = "http://localhost:3000"
    ENCRYPTION_KEY: str | None = None
    CONNECTIONS_FILE_PATH: str = "connections.enc"

    @property
    def destination_sqlalchemy_url(self) -> str:
        # Using oracledb with thin mode
        # For older Oracle versions, Oracle Instant Client (thick mode) may be required

        # Check if Oracle credentials are configured
        if not self.ORACLE_USER or not self.ORACLE_PASSWORD:
            raise ValueError(
                "Oracle database credentials not configured. "
                "Please set ORACLE_USER and ORACLE_PASSWORD in .env file or environment variables."
            )

        if self.ORACLE_DSN:
            # Parse DSN to extract host, port, and service name
            # Format: host:port/service_name or just host/service_name
            if "/" in self.ORACLE_DSN:
                host_port, service = self.ORACLE_DSN.rsplit("/", 1)
                if ":" in host_port:
                    host, port = host_port.rsplit(":", 1)
                else:
                    host, port = host_port, "1521"
                return f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{host}:{port}/?service_name={service}"
            else:
                return (
                    f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_DSN}"
                )

        if not self.ORACLE_HOST or not self.ORACLE_SERVICE_NAME:
            raise ValueError(
                "Oracle database connection not configured. "
                "Please set ORACLE_HOST and ORACLE_SERVICE_NAME (or ORACLE_DSN) in .env file or environment variables."
            )

        return f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_HOST}:{self.ORACLE_PORT}/?service_name={self.ORACLE_SERVICE_NAME}"

    @property
    def sqlalchemy_url(self) -> str:
        """Backward-compatible alias for the destination DB URL."""
        return self.destination_sqlalchemy_url

    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @field_validator("APP_LOG_LEVEL")
    @classmethod
    def normalize_level(cls, v: str) -> str:
        return v.upper()

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
