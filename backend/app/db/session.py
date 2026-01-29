
import oracledb
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize oracledb in THICK mode for older Oracle database versions
# Thick mode requires Oracle Instant Client to be installed
try:
    oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_23_0")
    logger.info("Oracle client initialized in THICK mode with Instant Client 23")
except Exception as e:
    logger.warning(f"Could not initialize Oracle thick mode: {e}")
    logger.info("Continuing with thin mode (may not work with older Oracle versions)")

class Base(DeclarativeBase):
    pass

# Create engine - will use thick mode if initialized successfully
engine = create_engine(
    settings.sqlalchemy_url, 
    pool_size=5, 
    max_overflow=5, 
    future=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
