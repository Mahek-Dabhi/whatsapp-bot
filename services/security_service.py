"""
security_service.py
-------------------
Security controls for the WhatsApp bot:
  - Admin-only command enforcement
  - Per-number rate limiting (in-memory sliding window)
  - Spam detection and temporary banning
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict
from app.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ── In-memory rate limit store ─────────────────────────────────────────────
# phone → deque of timestamps within the current window
_rate_limit_store: Dict[str, Deque[float]] = defaultdict(deque)

# phone → ban expiry unix timestamp (0 = not banned)
_ban_store: Dict[str, float] = defaultdict(float)

# How long to ban a spammer (seconds)
BAN_DURATION_SECONDS = 3600  # 1 hour


def is_admin(phone: str) -> bool:
    """
    Check whether a phone number belongs to an admin user.

    Args:
        phone: Normalised phone number (digits only).

    Returns:
        True if the number is in ADMIN_NUMBERS.
    """
    return phone in settings.ADMIN_NUMBERS


def is_rate_limited(phone: str) -> bool:
    """
    Determine whether a phone number has exceeded the message rate limit.

    Uses a sliding window algorithm: if the number sent more than
    RATE_LIMIT_MAX_MESSAGES in the last RATE_LIMIT_WINDOW_SECONDS, it
    is rate-limited.

    Args:
        phone: Normalised phone number.

    Returns:
        True if the sender should be throttled.
    """
    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    max_msgs = settings.RATE_LIMIT_MAX_MESSAGES

    timestamps: Deque[float] = _rate_limit_store[phone]

    # Remove timestamps outside the window
    while timestamps and now - timestamps[0] > window:
        timestamps.popleft()

    if len(timestamps) >= max_msgs:
        logger.warning("Rate limit hit for %s (%d msgs in %ds).", phone, len(timestamps), window)
        return True

    timestamps.append(now)
    return False


def is_banned(phone: str) -> bool:
    """
    Check whether a phone number is temporarily banned.

    Args:
        phone: Normalised phone number.

    Returns:
        True if the ban is still active.
    """
    ban_until = _ban_store.get(phone, 0)
    if ban_until and time.time() < ban_until:
        return True
    # Clear expired ban
    if phone in _ban_store:
        del _ban_store[phone]
    return False


def ban_phone(phone: str, duration_seconds: int = BAN_DURATION_SECONDS) -> None:
    """
    Temporarily ban a phone number from using the bot.

    Args:
        phone:            Phone number to ban.
        duration_seconds: Ban duration in seconds.
    """
    _ban_store[phone] = time.time() + duration_seconds
    logger.warning("Phone %s banned for %ds.", phone, duration_seconds)


def unban_phone(phone: str) -> None:
    """
    Lift a ban from a phone number.

    Args:
        phone: Phone number to unban.
    """
    _ban_store.pop(phone, None)
    logger.info("Phone %s unbanned.", phone)


def check_and_handle_spam(phone: str) -> bool:
    """
    Combined spam check: applies ban if rate limit has been exceeded.
    Returns True if the message should be blocked.

    Args:
        phone: Sender phone number.

    Returns:
        True if blocked (banned or rate limited beyond threshold).
    """
    if is_banned(phone):
        logger.info("Blocked banned phone: %s.", phone)
        return True

    # Auto-ban if rate limited more than 3× in a row — tracked via store depth
    if is_rate_limited(phone):
        if len(_rate_limit_store[phone]) >= settings.RATE_LIMIT_MAX_MESSAGES * 3:
            ban_phone(phone)
        return True

    return False
