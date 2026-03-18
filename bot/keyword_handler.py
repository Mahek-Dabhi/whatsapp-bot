"""
keyword_handler.py
------------------
Keyword-based auto-reply system.
Matches incoming messages against a keyword registry and sends pre-defined
responses. Supports exact match, prefix match, and fuzzy substring match.
"""

from typing import Optional
from services.whatsapp_service import send_text_message
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Keyword → Response registry ──────────────────────────────────────────────
# Keys are lowercased trigger words/phrases.
# Values are the response texts to send.
KEYWORD_RESPONSES: dict[str, str] = {
    # Greetings
    "hi": "👋 Hello! How can I help you today? Type /help for commands.",
    "hello": "👋 Hello! How can I help you today? Type /help for commands.",
    "hey": "👋 Hey there! How can I assist you?",
    "good morning": "🌅 Good morning! Hope you have a great day. How can I help?",
    "good afternoon": "☀️ Good afternoon! How can I assist you?",
    "good evening": "🌙 Good evening! How can I help you?",

    # Thanks
    "thank you": "😊 You're welcome! Let me know if there's anything else I can help with.",
    "thanks": "😊 You're welcome! Anything else I can help with?",

    # Pricing
    "price": "💰 Please type /price to see our full price list.",
    "cost": "💰 Please type /price to see our full price list.",
    "how much": "💰 Type /price for a full breakdown of our pricing.",

    # Support
    "help": "🤖 Type /help to see all available commands.",
    "support": "📞 Our support team is available via /contact.",
    "problem": "🔧 Sorry to hear that! Please reach out via /contact for assistance.",
    "issue": "🔧 We're here to help! Use /contact to reach our support team.",

    # Orders
    "order": "🛒 To place an order, type /order for step-by-step instructions.",
    "buy": "🛒 Ready to purchase? Type /order for our ordering process.",
    "purchase": "🛒 Type /order to get started with your purchase.",

    # Goodbye
    "bye": "👋 Goodbye! Have a wonderful day. Feel free to message us anytime.",
    "goodbye": "👋 Goodbye! We're here whenever you need us.",
}


def handle_keyword(phone: str, text: str) -> bool:
    """
    Check if the message matches any registered keyword and respond.

    Matching strategy (in order):
    1. Exact match (entire message equals a keyword).
    2. Starts-with match (message begins with a keyword phrase).
    3. Contains match (keyword appears anywhere in the message).

    Args:
        phone: Sender phone number.
        text:  Incoming message text (already stripped).

    Returns:
        True if a keyword matched and a reply was sent.
        False if no keyword matched.
    """
    normalised = text.lower().strip()

    # 1. Exact match
    if normalised in KEYWORD_RESPONSES:
        _send_reply(phone, KEYWORD_RESPONSES[normalised], normalised)
        return True

    # 2. Starts-with match
    for keyword, response in KEYWORD_RESPONSES.items():
        if normalised.startswith(keyword):
            _send_reply(phone, response, keyword)
            return True

    # 3. Contains match
    for keyword, response in KEYWORD_RESPONSES.items():
        if keyword in normalised:
            _send_reply(phone, response, keyword)
            return True

    return False


def _send_reply(phone: str, response: str, matched_keyword: str) -> None:
    """
    Send the keyword reply and log the match.

    Args:
        phone:           Recipient phone.
        response:        Pre-defined response text.
        matched_keyword: The keyword that triggered the reply.
    """
    send_text_message(phone, response)
    logger.info("Keyword '%s' matched for %s.", matched_keyword, phone)


def add_keyword(keyword: str, response: str) -> None:
    """
    Register a new keyword-response pair at runtime.

    Args:
        keyword:  Trigger word/phrase (will be lowercased).
        response: Response text to send when matched.
    """
    KEYWORD_RESPONSES[keyword.lower().strip()] = response
    logger.info("Keyword '%s' registered.", keyword)


def remove_keyword(keyword: str) -> bool:
    """
    Remove a keyword from the registry.

    Args:
        keyword: Keyword to remove.

    Returns:
        True if removed, False if not found.
    """
    key = keyword.lower().strip()
    if key in KEYWORD_RESPONSES:
        del KEYWORD_RESPONSES[key]
        logger.info("Keyword '%s' removed.", key)
        return True
    return False
