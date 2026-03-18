"""
analytics_model.py
------------------
MongoDB data model for tracking bot analytics events.
Collection name: `analytics`
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database.db_connection import get_collection
from utils.logger import get_logger

logger = get_logger(__name__)
COLLECTION = "analytics"


def _col():
    return get_collection(COLLECTION)


def record_event(
    event_type: str,
    phone: Optional[str] = None,
    campaign_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record a single analytics event.

    Args:
        event_type:  e.g. 'message_sent', 'message_received', 'command_used'.
        phone:       Contact phone number (optional).
        campaign_id: Associated campaign (optional).
        extra:       Any additional payload to store.
    """
    try:
        doc = {
            "event": event_type,
            "phone": phone,
            "campaign_id": campaign_id,
            "extra": extra or {},
            "timestamp": datetime.now(tz=timezone.utc),
        }
        _col().insert_one(doc)
    except Exception as exc:
        logger.error("record_event failed: %s", exc)


def get_event_counts(days: int = 30) -> Dict[str, int]:
    """
    Aggregate event counts for the last N days.

    Args:
        days: Lookback window.

    Returns:
        Dict mapping event_type → count.
    """
    from datetime import timedelta

    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {"_id": "$event", "count": {"$sum": 1}}},
    ]
    results = list(_col().aggregate(pipeline))
    return {r["_id"]: r["count"] for r in results}


def get_active_users(days: int = 7) -> int:
    """
    Count distinct phone numbers that sent a message in the last N days.

    Args:
        days: Lookback window.

    Returns:
        Count of unique active users.
    """
    from datetime import timedelta

    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    return len(
        _col().distinct(
            "phone",
            {"event": "message_received", "timestamp": {"$gte": since}},
        )
    )


def get_campaign_performance(campaign_id: str) -> Dict[str, Any]:
    """
    Return analytics summary for a specific campaign.

    Args:
        campaign_id: Campaign identifier.

    Returns:
        Dict with sent, delivered, read counts.
    """
    pipeline = [
        {"$match": {"campaign_id": campaign_id}},
        {"$group": {"_id": "$event", "count": {"$sum": 1}}},
    ]
    results = list(_col().aggregate(pipeline))
    return {r["_id"]: r["count"] for r in results}
