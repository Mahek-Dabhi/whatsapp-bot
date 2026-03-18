"""
website_api.py
--------------
Integration with an external website or product API.
Enables the bot to:
  - Fetch product/pricing info for commands
  - Submit orders / lead forms
  - Receive webhook triggers from the website
"""

from typing import Any, Dict, List, Optional
import requests
from app.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

TIMEOUT = 10
WEBSITE_API_URL = settings.CRM_API_URL  # Reuse or add WEBSITE_API_URL to .env


def get_product_catalog() -> List[Dict[str, Any]]:
    """
    Fetch the product catalog from the website API.

    Returns:
        List of product dicts (id, name, price, description).
    """
    if not WEBSITE_API_URL:
        logger.warning("WEBSITE_API_URL not configured.")
        return []

    try:
        response = requests.get(
            f"{WEBSITE_API_URL.rstrip('/')}/products",
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("products", [])
    except Exception as exc:
        logger.error("get_product_catalog failed: %s", exc)
        return []


def submit_lead(
    phone: str,
    name: str,
    message: str,
    email: str = "",
) -> bool:
    """
    Submit a lead / inquiry form to the website API.

    Args:
        phone:   Contact phone number.
        name:    Contact name.
        message: User's message / inquiry.
        email:   Optional email address.

    Returns:
        True on success, False on failure.
    """
    if not WEBSITE_API_URL:
        logger.warning("WEBSITE_API_URL not configured — skipping lead submission.")
        return False

    from utils.helpers import utc_now

    payload = {
        "phone": phone,
        "name": name,
        "email": email,
        "message": message,
        "source": "whatsapp",
        "submitted_at": utc_now().isoformat(),
    }

    try:
        response = requests.post(
            f"{WEBSITE_API_URL.rstrip('/')}/leads",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        logger.info("Lead submitted for %s.", phone)
        return True
    except Exception as exc:
        logger.error("submit_lead failed for %s: %s", phone, exc)
        return False


def check_order_status(order_id: str) -> Optional[Dict[str, Any]]:
    """
    Query the website API for an order status.

    Args:
        order_id: External order identifier.

    Returns:
        Order status dict, or None if not found.
    """
    if not WEBSITE_API_URL:
        return None

    try:
        response = requests.get(
            f"{WEBSITE_API_URL.rstrip('/')}/orders/{order_id}",
            timeout=TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("check_order_status failed for %s: %s", order_id, exc)
        return None


def notify_website_of_message(
    phone: str,
    message: str,
    direction: str = "inbound",
) -> bool:
    """
    Send an outgoing webhook to the website when a message is received.
    Useful for real-time chat inbox integrations.

    Args:
        phone:     Sender phone number.
        message:   Message body.
        direction: 'inbound' | 'outbound'.

    Returns:
        True on success.
    """
    if not WEBSITE_API_URL:
        return False

    from utils.helpers import utc_now

    payload = {
        "phone": phone,
        "message": message,
        "direction": direction,
        "channel": "whatsapp",
        "timestamp": utc_now().isoformat(),
    }

    try:
        response = requests.post(
            f"{WEBSITE_API_URL.rstrip('/')}/webhooks/whatsapp",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("notify_website_of_message failed: %s", exc)
        return False
