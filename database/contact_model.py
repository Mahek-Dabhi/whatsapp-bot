"""
contact_model.py
----------------
MongoDB data model and CRUD helpers for contacts.
Collection name: `contacts`
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pymongo.collection import Collection
from database.db_connection import get_collection
from utils.logger import get_logger

logger = get_logger(__name__)
COLLECTION = "contacts"


def _col() -> Collection:
    """Return the contacts collection."""
    return get_collection(COLLECTION)


# ── Schema helpers ────────────────────────────────────────────────────────────

def build_contact(
    phone: str,
    name: str = "",
    email: str = "",
    tags: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a new contact document dict.

    Args:
        phone:  Normalised phone number (digits only).
        name:   Display name.
        email:  Email address (optional).
        tags:   List of segment / group tags.
        extra:  Additional arbitrary key-value pairs.

    Returns:
        Dict representing the contact document.
    """
    return {
        "phone": phone,
        "name": name,
        "email": email,
        "tags": tags or [],
        "extra": extra or {},
        "opted_in": True,
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
    }


# ── CRUD operations ───────────────────────────────────────────────────────────

def upsert_contact(phone: str, **kwargs) -> None:
    """
    Insert or update a contact identified by phone number.

    Args:
        phone:   Phone number (digits only).
        **kwargs: Fields to set/update (name, email, tags, etc.).
    """
    try:
        now = datetime.now(tz=timezone.utc)
        _col().update_one(
            {"phone": phone},
            {
                "$set": {**kwargs, "updated_at": now},
                "$setOnInsert": {"phone": phone, "created_at": now},
            },
            upsert=True,
        )
        logger.debug("Upserted contact %s.", phone)
    except Exception as exc:
        logger.error("upsert_contact failed for %s: %s", phone, exc)
        raise


def get_contact(phone: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single contact by phone number.

    Args:
        phone: Normalised phone number.

    Returns:
        Contact document dict, or None if not found.
    """
    return _col().find_one({"phone": phone}, {"_id": 0})


def get_contacts_by_tag(tag: str) -> List[Dict[str, Any]]:
    """
    Return all contacts that have a specific tag.

    Args:
        tag: Tag/segment label.

    Returns:
        List of contact dicts.
    """
    return list(_col().find({"tags": tag}, {"_id": 0}))


def get_all_contacts() -> List[Dict[str, Any]]:
    """Return all opted-in contacts."""
    return list(_col().find({"opted_in": True}, {"_id": 0}))


def delete_contact(phone: str) -> bool:
    """
    Remove a contact from the database.

    Args:
        phone: Normalised phone number.

    Returns:
        True if a document was deleted, False otherwise.
    """
    result = _col().delete_one({"phone": phone})
    return result.deleted_count > 0


def bulk_insert_contacts(contacts: List[Dict[str, Any]]) -> int:
    """
    Insert multiple contacts, ignoring duplicates.

    Args:
        contacts: List of contact dicts (must include 'phone').

    Returns:
        Number of documents inserted.
    """
    if not contacts:
        return 0
    try:
        result = _col().insert_many(contacts, ordered=False)
        return len(result.inserted_ids)
    except Exception as exc:
        # BulkWriteError fires on duplicates — log and return partial count
        logger.warning("bulk_insert_contacts partial failure: %s", exc)
        return 0
