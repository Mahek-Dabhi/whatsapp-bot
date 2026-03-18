"""
db_connection.py
----------------
MongoDB connection management using Motor (async) via PyMongo (sync fallback).
Provides a single shared client instance for the entire application.
"""

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Module-level singleton ────────────────────────────────────────────────────
_client: MongoClient | None = None
_db: Database | None = None


def get_database() -> Database:
    """
    Return the shared MongoDB Database instance, creating it on first call.

    Returns:
        pymongo.database.Database connected to MONGO_DB_NAME.

    Raises:
        ConnectionFailure: If the MongoDB server is unreachable.
    """
    global _client, _db

    if _db is not None:
        return _db

    try:
        logger.info("Connecting to MongoDB at %s …", settings.MONGO_URI)
        _client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,  # 5-second connection timeout
        )
        # Trigger a real connection to catch errors early
        _client.admin.command("ping")
        _db = _client[settings.MONGO_DB_NAME]
        logger.info("Connected to database '%s'.", settings.MONGO_DB_NAME)
        return _db

    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.error("MongoDB connection failed: %s", exc)
        raise


def close_database() -> None:
    """Close the MongoDB connection (call on application shutdown)."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")


def get_collection(name: str):
    """
    Return a named collection from the shared database.

    Args:
        name: Collection name.

    Returns:
        pymongo.collection.Collection instance.
    """
    return get_database()[name]
