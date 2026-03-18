"""
logger.py
---------
Centralised logging configuration for the WhatsApp Automation Bot.
All modules import `logger` from here so log format is consistent.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os

# Ensure log directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Log format — timestamp | level | module | message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger with both console and rotating-file handlers.

    Args:
        name: Logger name — typically __name__ of the calling module.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated imports
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # ── Console handler ───────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ── Rotating file handler ─────────────────────────────────────────────
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "bot.log"),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Default logger for quick imports
logger = get_logger("whatsapp_bot")
