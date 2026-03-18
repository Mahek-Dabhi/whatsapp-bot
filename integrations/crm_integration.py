"""
crm_integration.py
------------------
Generic CRM integration via REST API.
Syncs WhatsApp contacts/messages with an external CRM system.
Configure CRM_API_URL and CRM_API_KEY in .env.
"""

from typing import Any, Dict, List, Optional
import requests
from app.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Request timeout for CRM API calls (seconds)
TIMEOUT = 10


def _headers() -> Dict[str, str]:
    """Build standard auth headers for CRM API requests."""
    return {
        "Authorization": f"Bearer {settings.CRM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _base_url() -> str:
    """Return the configured CRM base URL (strips trailing slash)."""
    return settings.CRM_API_URL.rstrip("/")


def push_contact(contact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create or update a contact record in the CRM.

    Args:
        contact: Dict with keys: phone, name, email, tags.

    Returns:
        CRM response dict on success, None on failure.
    """
    if not settings.CRM_API_URL:
        logger.warning("CRM_API_URL not configured — skipping push_contact.")
        return None

    payload = {
        "phone": contact.get("phone"),
        "name": contact.get("name", ""),
        "email": contact.get("email", ""),
        "tags": contact.get("tags", []),
        "source": "whatsapp_bot",
    }

    try:
        response = requests.post(
            f"{_base_url()}/contacts",
            headers=_headers(),
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        logger.info("Contact %s pushed to CRM.", contact.get("phone"))
        return response.json()
    except requests.HTTPError as exc:
        logger.error("CRM push_contact HTTP error: %s", exc)
        return None
    except Exception as exc:
        logger.error("CRM push_contact error: %s", exc)
        return None


def log_interaction(
    phone: str,
    direction: str,
    message: str,
    campaign_id: Optional[str] = None,
) -> bool:
    """
    Log a WhatsApp message interaction to the CRM.

    Args:
        phone:       Contact phone number.
        direction:   'inbound' | 'outbound'.
        message:     Message text body.
        campaign_id: Optional campaign reference.

    Returns:
        True on success, False on failure.
    """
    if not settings.CRM_API_URL:
        return False

    from utils.helpers import utc_now

    payload = {
        "phone": phone,
        "channel": "whatsapp",
        "direction": direction,
        "message": message,
        "campaign_id": campaign_id,
        "timestamp": utc_now().isoformat(),
    }

    try:
        response = requests.post(
            f"{_base_url()}/interactions",
            headers=_headers(),
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("CRM log_interaction failed for %s: %s", phone, exc)
        return False


def fetch_crm_contacts() -> List[Dict[str, Any]]:
    """
    Fetch all contacts from the CRM.

    Returns:
        List of contact dicts from CRM.
    """
    if not settings.CRM_API_URL:
        logger.warning("CRM_API_URL not configured.")
        return []

    try:
        response = requests.get(
            f"{_base_url()}/contacts",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        contacts = data if isinstance(data, list) else data.get("contacts", [])
        logger.info("Fetched %d contacts from CRM.", len(contacts))
        return contacts
    except Exception as exc:
        logger.error("fetch_crm_contacts failed: %s", exc)
        return []


def sync_crm_to_mongo() -> Dict[str, int]:
    """
    Pull contacts from CRM and upsert them into MongoDB.

    Returns:
        Dict with synced and failed counts.
    """
    from services.contact_service import add_contact

    crm_contacts = fetch_crm_contacts()
    synced, failed = 0, 0

    for c in crm_contacts:
        phone = str(c.get("phone", "")).strip()
        if not phone:
            failed += 1
            continue
        try:
            add_contact(
                phone=phone,
                name=c.get("name", ""),
                email=c.get("email", ""),
                tags=c.get("tags", []),
            )
            synced += 1
        except Exception as exc:
            logger.warning("Failed to sync CRM contact %s: %s", phone, exc)
            failed += 1

    logger.info("CRM sync complete — synced=%d, failed=%d.", synced, failed)
    return {"synced": synced, "failed": failed}
