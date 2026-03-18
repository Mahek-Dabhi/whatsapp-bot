"""
message_router.py
-----------------
Central message routing pipeline for all inbound WhatsApp messages.

Processing order:
  1. Security checks  (spam / rate-limit / ban)
  2. Command handler  (/help, /price, etc.)
  3. Keyword handler  (hi → Hello!, etc.)
  4. AI chatbot       (OpenAI fallback)

Each layer returns True if it handled the message, stopping further processing.
"""

from database.message_model import log_message
from database.analytics_model import record_event
from database.contact_model import upsert_contact
from services.security_service import check_and_handle_spam
from services.whatsapp_service import mark_as_read
from bot.command_handler import handle_command
from bot.keyword_handler import handle_keyword
from bot.ai_chatbot import chat
from utils.logger import get_logger

logger = get_logger(__name__)


def route_message(
    phone: str,
    text: str,
    message_id: str = "",
    message_type: str = "text",
) -> None:
    """
    Route an inbound message through the full processing pipeline.

    Args:
        phone:        Sender phone number (digits only).
        text:         Message text body.
        message_id:   WhatsApp message ID (for read receipts).
        message_type: Message type ('text', 'image', etc.).
    """
    logger.info("Routing message from %s (type=%s): '%s'", phone, message_type, text[:80])

    # ── 1. Log the inbound message ────────────────────────────────────────
    log_message(
        phone=phone,
        direction="inbound",
        message_type=message_type,
        body=text,
        message_id=message_id,
    )
    record_event("message_received", phone=phone)

    # ── 2. Auto-save sender as a contact ─────────────────────────────────
    try:
        upsert_contact(phone)
    except Exception as exc:
        logger.warning("Could not upsert contact %s: %s", phone, exc)

    # ── 3. Mark message as read ───────────────────────────────────────────
    if message_id:
        mark_as_read(message_id)

    # ── 4. Security gate ──────────────────────────────────────────────────
    if check_and_handle_spam(phone):
        logger.warning("Message from %s blocked by security gate.", phone)
        return

    # Non-text messages (images, audio, etc.) — acknowledge and return
    if message_type != "text" or not text.strip():
        _handle_non_text(phone, message_type)
        return

    stripped_text = text.strip()

    # ── 5. Command handler ────────────────────────────────────────────────
    if handle_command(phone, stripped_text):
        record_event("command_used", phone=phone, extra={"command": stripped_text.split()[0]})
        return

    # ── 6. Keyword handler ────────────────────────────────────────────────
    if handle_keyword(phone, stripped_text):
        record_event("keyword_matched", phone=phone, extra={"text": stripped_text[:50]})
        return

    # ── 7. AI chatbot fallback ────────────────────────────────────────────
    logger.debug("No command/keyword match for '%s' — falling back to AI.", stripped_text)
    record_event("ai_fallback", phone=phone)
    chat(phone, stripped_text)


def _handle_non_text(phone: str, message_type: str) -> None:
    """
    Send a friendly acknowledgement for non-text message types.

    Args:
        phone:        Sender phone.
        message_type: WhatsApp message type string.
    """
    from services.whatsapp_service import send_text_message

    type_responses = {
        "image":    "📸 Thanks for the image! Type /help if you need assistance.",
        "video":    "🎥 Thanks for the video! Type /help if you need assistance.",
        "audio":    "🎵 Thanks for the audio message! Type /help for commands.",
        "document": "📄 Thanks for the document! Type /help if you need assistance.",
        "sticker":  "😊 Nice sticker! Type /help if you need assistance.",
        "location": "📍 Thanks for sharing your location! Type /contact for support.",
        "contacts": "👤 Thanks for sharing the contact! Type /help for commands.",
    }
    reply = type_responses.get(
        message_type,
        "👋 Got your message! Type /help for available commands.",
    )
    send_text_message(phone, reply)
    logger.info("Acknowledged %s message from %s.", message_type, phone)
