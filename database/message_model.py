"""
message_model.py
----------------
MongoDB data model and helpers for logging all chat messages.
Collection name: `messages`
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pymongo.collection import Collection
from database.db_connection import get_collection
from utils.logger import get_logger

logger = get_logger(__name__)
COLLECTION = "messages"


def _col() -> Collection:
    return get_collection(COLLECTION)


def log_message(
    phone: str,
    direction: str,      # "inbound" | "outbound"
    message_type: str,   # "text" | "image" | "video" | "audio" | "document"
    body: str = "",
    message_id: str = "",
    campaign_id: Optional[str] = None,
    status: str = "sent",
) -> None:
    """
    Persist a message record in MongoDB.

    Args:
        phone:        Contact phone number.
        direction:    'inbound' (received) or 'outbound' (sent).
        message_type: WhatsApp message type.
        body:         Text body or media caption.
        message_id:   WhatsApp message ID returned by the API.
        campaign_id:  Optional campaign reference.
        status:       Delivery status ('sent', 'delivered', 'read', 'failed').
    """
    try:
        doc = {
            "phone": phone,
            "direction": direction,
            "type": message_type,
            "body": body,
            "message_id": message_id,
            "campaign_id": campaign_id,
            "status": status,
            "timestamp": datetime.now(tz=timezone.utc),
        }
        _col().insert_one(doc)
        logger.debug("Logged %s message for %s.", direction, phone)
    except Exception as exc:
        logger.error("log_message failed: %s", exc)


def get_messages_for_phone(
    phone: str, limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent messages for a contact.

    Args:
        phone: Contact phone number.
        limit: Maximum number of messages to return.

    Returns:
        List of message dicts, newest first.
    """
    return list(
        _col()
        .find({"phone": phone}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )


def get_messages_by_campaign(campaign_id: str) -> List[Dict[str, Any]]:
    """Return all messages associated with a campaign."""
    return list(_col().find({"campaign_id": campaign_id}, {"_id": 0}))


def count_messages(direction: Optional[str] = None) -> int:
    """
    Count total messages, optionally filtered by direction.

    Args:
        direction: 'inbound', 'outbound', or None for all.

    Returns:
        Integer count.
    """
    query: Dict[str, Any] = {}
    if direction:
        query["direction"] = direction
    return _col().count_documents(query)


def update_message_status(message_id: str, status: str) -> None:
    """
    Update delivery status of a specific outbound message.

    Args:
        message_id: WhatsApp message ID.
        status:     New status string.
    """
    _col().update_one(
        {"message_id": message_id},
        {"$set": {"status": status, "updated_at": datetime.now(tz=timezone.utc)}},
    )
