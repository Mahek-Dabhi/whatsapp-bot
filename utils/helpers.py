"""
helpers.py
----------
General-purpose helper utilities used across the bot.
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


def unix_timestamp() -> int:
    """Return the current Unix timestamp as an integer."""
    return int(time.time())


def format_phone(phone: str) -> str:
    """
    Ensure a phone number is prefixed with '+' for display.

    Args:
        phone: Normalised digits-only phone number.

    Returns:
        Phone string with leading '+'.
    """
    return f"+{phone}" if not phone.startswith("+") else phone


def extract_whatsapp_message(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Navigate the WhatsApp Cloud API webhook payload and extract the
    first message object found.

    Args:
        payload: Raw JSON body from the webhook POST request.

    Returns:
        A dict with keys: phone, message_id, type, text, timestamp
        or None if no message was found.
    """
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        messages = value.get("messages")
        if not messages:
            return None

        msg = messages[0]
        contact = value.get("contacts", [{}])[0]
        phone = contact.get("wa_id") or msg.get("from", "")

        message_type = msg.get("type", "text")
        text = ""

        if message_type == "text":
            text = msg.get("text", {}).get("body", "")
        elif message_type == "interactive":
            interactive = msg.get("interactive", {})
            if interactive.get("type") == "button_reply":
                text = interactive["button_reply"].get("title", "")
            elif interactive.get("type") == "list_reply":
                text = interactive["list_reply"].get("title", "")

        return {
            "phone": phone,
            "message_id": msg.get("id", ""),
            "type": message_type,
            "text": text,
            "timestamp": msg.get("timestamp", str(unix_timestamp())),
            "raw": msg,
        }

    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Failed to extract message from payload: %s", exc)
        return None


def hash_phone(phone: str) -> str:
    """
    Return a SHA-256 hash of a phone number for anonymised analytics.

    Args:
        phone: Raw phone number string.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(phone.encode()).hexdigest()


def chunk_list(lst: list, size: int) -> list:
    """
    Split a list into chunks of at most `size` elements.

    Args:
        lst:  Source list.
        size: Maximum chunk size.

    Returns:
        List of sub-lists.
    """
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def safe_get(d: Dict[str, Any], *keys, default=None) -> Any:
    """
    Safely traverse nested dicts without raising KeyError.

    Args:
        d:       Root dict.
        *keys:   Sequence of keys to traverse.
        default: Value returned when a key is missing.

    Returns:
        Value at the nested path, or default.
    """
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current
