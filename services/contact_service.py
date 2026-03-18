"""
contact_service.py
------------------
Service layer for contact management.
Handles individual CRUD, tag management, and CSV/Excel imports.
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from database.contact_model import (
    upsert_contact, get_contact, get_contacts_by_tag,
    get_all_contacts, delete_contact, bulk_insert_contacts, build_contact
)
from utils.validators import validate_phone_number
from utils.logger import get_logger

logger = get_logger(__name__)


def add_contact(
    phone: str,
    name: str = "",
    email: str = "",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Add or update a contact.

    Args:
        phone:  Phone number (will be normalised).
        name:   Display name.
        email:  Email address.
        tags:   Segment tags.

    Returns:
        Dict with normalised phone number.
    """
    normalised = validate_phone_number(phone)
    upsert_contact(normalised, name=name, email=email, tags=tags or [])
    logger.info("Contact %s added/updated.", normalised)
    return {"phone": normalised, "name": name}


def remove_contact(phone: str) -> bool:
    """
    Delete a contact.

    Args:
        phone: Phone number.

    Returns:
        True if deleted, False if not found.
    """
    normalised = validate_phone_number(phone)
    deleted = delete_contact(normalised)
    if deleted:
        logger.info("Contact %s deleted.", normalised)
    else:
        logger.warning("Contact %s not found for deletion.", normalised)
    return deleted


def tag_contact(phone: str, tag: str) -> None:
    """
    Add a tag to an existing contact (creates if not found).

    Args:
        phone: Phone number.
        tag:   Tag to add.
    """
    normalised = validate_phone_number(phone)
    contact = get_contact(normalised) or {}
    current_tags: List[str] = contact.get("tags", [])
    if tag not in current_tags:
        current_tags.append(tag)
    upsert_contact(normalised, tags=current_tags)
    logger.debug("Tag '%s' added to %s.", tag, normalised)


def import_from_csv(filepath: str) -> Dict[str, int]:
    """
    Import contacts from a CSV file.

    Expected columns: phone (required), name, email, tags (comma-separated).

    Args:
        filepath: Path to the CSV file.

    Returns:
        Dict with imported and skipped counts.
    """
    return _import_from_file(filepath, file_type="csv")


def import_from_excel(filepath: str) -> Dict[str, int]:
    """
    Import contacts from an Excel (.xlsx) file.

    Expected columns: phone (required), name, email, tags (comma-separated).

    Args:
        filepath: Path to the Excel file.

    Returns:
        Dict with imported and skipped counts.
    """
    return _import_from_file(filepath, file_type="excel")


def _import_from_file(filepath: str, file_type: str = "csv") -> Dict[str, int]:
    """
    Internal helper that reads a CSV or Excel file and bulk-inserts contacts.

    Args:
        filepath:  Path to the file.
        file_type: 'csv' or 'excel'.

    Returns:
        Dict with imported and skipped counts.
    """
    try:
        df = pd.read_csv(filepath) if file_type == "csv" else pd.read_excel(filepath)
    except Exception as exc:
        logger.error("Failed to read %s file '%s': %s", file_type, filepath, exc)
        raise

    if "phone" not in df.columns:
        raise ValueError("File must contain a 'phone' column.")

    contacts = []
    skipped = 0

    for _, row in df.iterrows():
        raw_phone = str(row.get("phone", "")).strip()
        try:
            phone = validate_phone_number(raw_phone)
        except ValueError:
            logger.warning("Skipping invalid phone: '%s'", raw_phone)
            skipped += 1
            continue

        tags_raw = str(row.get("tags", "")).strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        contacts.append(
            build_contact(
                phone=phone,
                name=str(row.get("name", "")).strip(),
                email=str(row.get("email", "")).strip(),
                tags=tags,
            )
        )

    imported = bulk_insert_contacts(contacts)
    logger.info("Import complete — imported=%d, skipped=%d.", imported, skipped)
    return {"imported": imported, "skipped": skipped}


def list_contacts(tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List contacts, optionally filtered by tag.

    Args:
        tag: Optional segment filter.

    Returns:
        List of contact dicts.
    """
    if tag:
        return get_contacts_by_tag(tag)
    return get_all_contacts()
