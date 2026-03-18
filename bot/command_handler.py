"""
command_handler.py
------------------
Handles slash-command messages from users.
Commands are matched by prefix (e.g. /help, /price, /order).
Admin-only commands are protected by the security service.
"""

from typing import Optional
from services.whatsapp_service import send_text_message
from services.security_service import is_admin
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Command response registry ─────────────────────────────────────────────────
# Maps command string → response text (or callable)
COMMANDS: dict = {
    "/help": (
        "🤖 *Available Commands*\n\n"
        "/help    — Show this help menu\n"
        "/price   — View our price list\n"
        "/order   — How to place an order\n"
        "/contact — Contact our support team\n"
        "/status  — Check bot status\n"
    ),
    "/price": (
        "💰 *Price List*\n\n"
        "• Basic Plan   — $9.99/mo\n"
        "• Pro Plan     — $29.99/mo\n"
        "• Enterprise   — Custom pricing\n\n"
        "Reply /order to get started!"
    ),
    "/order": (
        "🛒 *How to Order*\n\n"
        "1. Visit our website: https://example.com/shop\n"
        "2. Select a product\n"
        "3. Complete checkout\n"
        "4. We'll confirm via WhatsApp\n\n"
        "Questions? Type /contact"
    ),
    "/contact": (
        "📞 *Contact Us*\n\n"
        "📧 Email: support@example.com\n"
        "📱 Phone: +1-800-EXAMPLE\n"
        "🌐 Web:   https://example.com\n"
        "⏰ Hours: Mon–Fri, 9 AM–6 PM"
    ),
    "/status": "✅ Bot is online and running normally.",
}

# Admin-only commands
ADMIN_COMMANDS: dict = {
    "/stats": "📊 Use the /admin/stats API endpoint for detailed analytics.",
    "/broadcast": "📢 Use the /admin/broadcast API endpoint to send broadcasts.",
    "/ban": "🚫 Use the /admin/ban API endpoint to ban a number.",
}


def handle_command(phone: str, text: str) -> bool:
    """
    Detect and handle a slash command.

    Args:
        phone: Sender phone number.
        text:  Incoming message text (stripped).

    Returns:
        True if the message was a command and was handled.
        False if it was not a command.
    """
    if not text.startswith("/"):
        return False

    # Normalise: take first word as the command
    command = text.split()[0].lower().strip()

    # Check regular commands
    if command in COMMANDS:
        response = COMMANDS[command]
        send_text_message(phone, response)
        logger.info("Command '%s' handled for %s.", command, phone)
        return True

    # Check admin-only commands
    if command in ADMIN_COMMANDS:
        if not is_admin(phone):
            send_text_message(
                phone, "🔒 This command is restricted to administrators."
            )
            logger.warning("Unauthorised admin command '%s' from %s.", command, phone)
        else:
            send_text_message(phone, ADMIN_COMMANDS[command])
            logger.info("Admin command '%s' handled for %s.", command, phone)
        return True

    # Unknown command
    send_text_message(
        phone,
        f"❓ Unknown command '{command}'. Type /help for a list of available commands.",
    )
    logger.info("Unknown command '%s' from %s.", command, phone)
    return True


def register_command(command: str, response: str, admin_only: bool = False) -> None:
    """
    Dynamically register a new command at runtime.

    Args:
        command:    The slash command string (e.g. '/promo').
        response:   Response text to send.
        admin_only: Whether the command is restricted to admins.
    """
    cmd = command.lower().strip()
    if admin_only:
        ADMIN_COMMANDS[cmd] = response
    else:
        COMMANDS[cmd] = response
    logger.info("Registered command '%s' (admin_only=%s).", cmd, admin_only)
