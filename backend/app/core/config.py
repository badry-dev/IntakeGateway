
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    APP_NAME: str = "api-to-db-importer"
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

    SECRET_KEY: str = "dev-secret"
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def sqlalchemy_url(self) -> str:
        # Force thin mode to avoid "bequeath is only supported in thick mode" error
        # Thin mode is pure Python and doesn't require Oracle Instant Client
        
        # Check if Oracle credentials are configured
        if not self.ORACLE_USER or not self.ORACLE_PASSWORD:
            raise ValueError(
                "Oracle database credentials not configured. "
                "Please set ORACLE_USER and ORACLE_PASSWORD in .env file or environment variables."
            )
        
        if self.ORACLE_DSN:
            # Parse DSN to extract host, port, and service name
            # Format: host:port/service_name or just host/service_name
            if '/' in self.ORACLE_DSN:
                host_port, service = self.ORACLE_DSN.rsplit('/', 1)
                if ':' in host_port:
                    host, port = host_port.rsplit(':', 1)
                else:
                    host, port = host_port, "1521"
                return f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{host}:{port}/?service_name={service}"
            else:
                return f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_DSN}"
        
        if not self.ORACLE_HOST or not self.ORACLE_SERVICE_NAME:
            raise ValueError(
                "Oracle database connection not configured. "
                "Please set ORACLE_HOST and ORACLE_SERVICE_NAME (or ORACLE_DSN) in .env file or environment variables."
            )
        
        return f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_HOST}:{self.ORACLE_PORT}/?service_name={self.ORACLE_SERVICE_NAME}"

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
