"""
validators.py
-------------
Input-validation helpers used across services and API endpoints.
All functions raise ValueError on invalid input so callers can handle uniformly.
"""

import re
from utils.logger import get_logger

logger = get_logger(__name__)


def validate_phone_number(phone: str) -> str:
    """
    Validate and normalise a WhatsApp-compatible phone number.

    Accepts:
        - E.164 format: +1234567890
        - Digits only:  1234567890

    Returns:
        Normalised number without leading '+'.

    Raises:
        ValueError: If the number is not valid.
    """
    # Strip whitespace and leading '+'
    cleaned = phone.strip().lstrip("+")

    if not cleaned.isdigit():
        raise ValueError(f"Phone number must contain digits only: '{phone}'")

    if not (7 <= len(cleaned) <= 15):
        raise ValueError(
            f"Phone number length must be 7–15 digits, got {len(cleaned)}: '{phone}'"
        )

    return cleaned


def validate_message_body(body: str, max_length: int = 4096) -> str:
    """
    Validate a WhatsApp text message body.

    Args:
        body:       Message text.
        max_length: Maximum allowed length (WhatsApp limit is 4096).

    Returns:
        Stripped message body.

    Raises:
        ValueError: If body is empty or exceeds max_length.
    """
    stripped = body.strip()
    if not stripped:
        raise ValueError("Message body must not be empty.")
    if len(stripped) > max_length:
        raise ValueError(
            f"Message body exceeds {max_length} characters (got {len(stripped)})."
        )
    return stripped


def validate_media_url(url: str) -> str:
    """
    Validate that a URL is well-formed and uses HTTPS.

    Args:
        url: Media URL string.

    Returns:
        Stripped URL.

    Raises:
        ValueError: If URL is invalid or not HTTPS.
    """
    stripped = url.strip()
    pattern = re.compile(r"^https://[^\s]+$", re.IGNORECASE)
    if not pattern.match(stripped):
        raise ValueError(
            f"Media URL must be a valid HTTPS URL, got: '{url}'"
        )
    return stripped


def validate_schedule_time(scheduled_time: str) -> str:
    """
    Validate ISO-8601 datetime string (YYYY-MM-DDTHH:MM:SS).

    Args:
        scheduled_time: Datetime string.

    Returns:
        The original string if valid.

    Raises:
        ValueError: If format is incorrect.
    """
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")
    if not pattern.match(scheduled_time.strip()):
        raise ValueError(
            f"scheduled_time must be ISO-8601 (YYYY-MM-DDTHH:MM:SS): '{scheduled_time}'"
        )
    return scheduled_time.strip()


def sanitize_text(text: str) -> str:
    """
    Remove potentially harmful characters from user-supplied text.

    Args:
        text: Raw input text.

    Returns:
        Sanitised string.
    """
    # Strip null bytes and control characters (except newlines/tabs)
    sanitized = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    return sanitized.strip()
