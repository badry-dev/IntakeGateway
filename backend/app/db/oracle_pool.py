import oracledb
from app.core.config import settings

pool: oracledb.SessionPool | None = None


def get_pool() -> oracledb.SessionPool:
    global pool
    if pool is None:
        dsn = (
            settings.ORACLE_DSN
            or f"{settings.ORACLE_HOST}:{settings.ORACLE_PORT}/{settings.ORACLE_SERVICE_NAME}"
        )
        pool = oracledb.create_pool(
            user=settings.ORACLE_USER,
            password=settings.ORACLE_PASSWORD,
            dsn=dsn,
            min=1,
            max=5,
            increment=1,
        )
    return pool
