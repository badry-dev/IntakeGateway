
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

    @property
    def sqlalchemy_url(self) -> str:
        if self.ORACLE_DSN:
            return f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_DSN}"
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
