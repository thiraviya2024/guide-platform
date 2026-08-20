 # utils/logger.py
import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/lipidai.log", rotation="10 MB", level="INFO")

__all__ = ["logger"]