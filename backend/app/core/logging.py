
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, level="INFO", enqueue=True,
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>")

def get_logger():
    return logger
