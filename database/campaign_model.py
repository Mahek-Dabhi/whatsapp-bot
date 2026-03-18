"""
campaign_model.py
-----------------
MongoDB data model for marketing campaigns / broadcast jobs.
Collection name: `campaigns`
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database.db_connection import get_collection
from utils.logger import get_logger

logger = get_logger(__name__)
COLLECTION = "campaigns"


def _col():
    return get_collection(COLLECTION)


def create_campaign(
    name: str,
    message: str,
    target_tag: Optional[str] = None,
    target_phones: Optional[List[str]] = None,
    scheduled_at: Optional[datetime] = None,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None,
) -> str:
    """
    Create a new campaign document.

    Args:
        name:           Human-readable campaign name.
        message:        Message body / caption.
        target_tag:     Segment tag to target (optional).
        target_phones:  Explicit phone list (optional).
        scheduled_at:   When to send (None = immediate).
        media_url:      Optional media URL.
        media_type:     'image' | 'video' | 'audio' | 'document'.

    Returns:
        Inserted document ID as string.
    """
    doc = {
        "name": name,
        "message": message,
        "target_tag": target_tag,
        "target_phones": target_phones or [],
        "scheduled_at": scheduled_at,
        "media_url": media_url,
        "media_type": media_type,
        "status": "pending",       # pending | running | completed | failed
        "sent_count": 0,
        "failed_count": 0,
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
    }
    result = _col().insert_one(doc)
    campaign_id = str(result.inserted_id)
    logger.info("Campaign '%s' created with ID %s.", name, campaign_id)
    return campaign_id


def update_campaign_status(campaign_id: str, status: str, **kwargs) -> None:
    """Update a campaign's status and optional counters."""
    from bson import ObjectId
    _col().update_one(
        {"_id": ObjectId(campaign_id)},
        {
            "$set": {
                "status": status,
                "updated_at": datetime.now(tz=timezone.utc),
                **kwargs,
            }
        },
    )


def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a campaign by its ID."""
    from bson import ObjectId
    doc = _col().find_one({"_id": ObjectId(campaign_id)})
    if doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def get_pending_campaigns() -> List[Dict[str, Any]]:
    """Return all pending campaigns (not yet run)."""
    now = datetime.now(tz=timezone.utc)
    docs = list(
        _col().find(
            {
                "status": "pending",
                "$or": [
                    {"scheduled_at": None},
                    {"scheduled_at": {"$lte": now}},
                ],
            }
        )
    )
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
    return docs


def list_campaigns(limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent campaigns, newest first."""
    docs = list(_col().find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
    return docs
