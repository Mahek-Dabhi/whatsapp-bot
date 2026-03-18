"""
analytics_service.py
--------------------
High-level analytics service that aggregates data from multiple collections
and presents it in a structured report format.
"""

from typing import Any, Dict
from database.analytics_model import get_event_counts, get_active_users, get_campaign_performance
from database.message_model import count_messages
from database.contact_model import get_all_contacts
from utils.logger import get_logger

logger = get_logger(__name__)


def get_dashboard_stats() -> Dict[str, Any]:
    """
    Compile a complete analytics dashboard snapshot.

    Returns:
        Dict containing:
          - messages_sent
          - messages_received
          - total_contacts
          - active_users_7d
          - event_counts_30d
    """
    try:
        stats = {
            "messages_sent": count_messages(direction="outbound"),
            "messages_received": count_messages(direction="inbound"),
            "total_contacts": len(get_all_contacts()),
            "active_users_7d": get_active_users(days=7),
            "event_counts_30d": get_event_counts(days=30),
        }
        logger.debug("Dashboard stats computed: %s", stats)
        return stats
    except Exception as exc:
        logger.error("get_dashboard_stats failed: %s", exc)
        return {}


def get_campaign_report(campaign_id: str) -> Dict[str, Any]:
    """
    Return a performance report for a given campaign.

    Args:
        campaign_id: Campaign identifier.

    Returns:
        Dict with event breakdown for the campaign.
    """
    try:
        from database.campaign_model import get_campaign
        campaign = get_campaign(campaign_id)
        if not campaign:
            return {"error": "Campaign not found"}

        performance = get_campaign_performance(campaign_id)
        return {
            "campaign_id": campaign_id,
            "name": campaign.get("name"),
            "status": campaign.get("status"),
            "sent_count": campaign.get("sent_count", 0),
            "failed_count": campaign.get("failed_count", 0),
            "performance_events": performance,
        }
    except Exception as exc:
        logger.error("get_campaign_report failed for %s: %s", campaign_id, exc)
        return {}


def get_message_stats_by_day(days: int = 7) -> Dict[str, Any]:
    """
    Return per-day message volume for the last N days.

    Args:
        days: Lookback window.

    Returns:
        Dict with daily breakdown of sent and received counts.
    """
    from database.db_connection import get_collection
    from datetime import datetime, timedelta, timezone

    col = get_collection("messages")
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {
            "$group": {
                "_id": {
                    "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "direction": "$direction",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.day": 1}},
    ]

    results = list(col.aggregate(pipeline))
    breakdown: Dict[str, Dict[str, int]] = {}
    for r in results:
        day = r["_id"]["day"]
        direction = r["_id"]["direction"]
        breakdown.setdefault(day, {"inbound": 0, "outbound": 0})
        breakdown[day][direction] = r["count"]

    return breakdown
