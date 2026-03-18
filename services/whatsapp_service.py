"""
whatsapp_service.py
-------------------
Core service for interacting with the WhatsApp Cloud API.
Handles sending text messages, marks messages as read, and provides
the low-level HTTP request wrapper used by other services.
"""

import requests
from typing import Any, Dict, Optional
from app.config import settings
from database.message_model import log_message
from database.analytics_model import record_event
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Internal HTTP helper ──────────────────────────────────────────────────────

def _post(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a POST request to the WhatsApp Cloud API.

    Args:
        payload: JSON body for the Messages API.

    Returns:
        Parsed API response dict.

    Raises:
        requests.HTTPError: On 4xx / 5xx responses.
    """
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        settings.WHATSAPP_API_URL,
        headers=headers,
        json=payload,
        timeout=15,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.error("WhatsApp API error %s: %s", response.status_code, response.text)
        raise
    return response.json()


# ── Public API ────────────────────────────────────────────────────────────────

def send_text_message(phone: str, message: str) -> Optional[str]:
    """
    Send a plain-text WhatsApp message.

    Args:
        phone:   Recipient phone number (digits only, no '+').
        message: Message text body.

    Returns:
        WhatsApp message ID on success, None on failure.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    try:
        response = _post(payload)
        message_id = response.get("messages", [{}])[0].get("id", "")
        log_message(phone, "outbound", "text", body=message, message_id=message_id)
        record_event("message_sent", phone=phone)
        logger.info("Text sent to %s (msg_id=%s).", phone, message_id)
        return message_id
    except Exception as exc:
        logger.error("send_text_message failed for %s: %s", phone, exc)
        log_message(phone, "outbound", "text", body=message, status="failed")
        return None


def send_template_message(phone: str, template_name: str, language_code: str = "en_US") -> Optional[str]:
    """
    Send a pre-approved WhatsApp template message.

    Args:
        phone:          Recipient phone number.
        template_name:  Approved template name.
        language_code:  BCP-47 language code.

    Returns:
        WhatsApp message ID on success, None on failure.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    try:
        response = _post(payload)
        message_id = response.get("messages", [{}])[0].get("id", "")
        log_message(phone, "outbound", "template", body=template_name, message_id=message_id)
        record_event("template_sent", phone=phone)
        logger.info("Template '%s' sent to %s.", template_name, phone)
        return message_id
    except Exception as exc:
        logger.error("send_template_message failed for %s: %s", phone, exc)
        return None


def mark_as_read(message_id: str) -> bool:
    """
    Mark an inbound message as read (shows double blue ticks).

    Args:
        message_id: WhatsApp message ID to mark read.

    Returns:
        True on success, False on failure.
    """
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    try:
        _post(payload)
        return True
    except Exception as exc:
        logger.warning("mark_as_read failed for %s: %s", message_id, exc)
        return False


def send_reaction(phone: str, message_id: str, emoji: str = "👍") -> bool:
    """
    React to an existing message with an emoji.

    Args:
        phone:      Recipient phone.
        message_id: ID of the message to react to.
        emoji:      Unicode emoji string.

    Returns:
        True on success, False on failure.
    """
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "reaction",
        "reaction": {"message_id": message_id, "emoji": emoji},
    }
    try:
        _post(payload)
        return True
    except Exception as exc:
        logger.warning("send_reaction failed: %s", exc)
        return False
