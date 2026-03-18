"""
webhook.py
----------
FastAPI router for the WhatsApp Cloud API webhook.
FIXED: Uses PlainTextResponse instead of int() conversion for challenge.
"""

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from app.config import settings
from bot.message_router import route_message
from database.message_model import update_message_status
from utils.helpers import extract_whatsapp_message
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Webhook"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Respond to WhatsApp webhook verification challenge.
    FIXED: Returns hub_challenge as plain text string (not int).
    """
    logger.info(
        "Webhook verification: mode=%s, token_match=%s",
        hub_mode,
        hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN,
    )

    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning("Webhook verification failed.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Webhook verification failed.",
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_webhook(request: Request):
    """Handle all inbound WhatsApp events."""
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("Failed to parse webhook payload: %s", exc)
        return {"status": "error", "detail": "invalid JSON"}

    logger.debug("Webhook payload: %s", str(payload)[:500])

    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        if "messages" in value:
            message_data = extract_whatsapp_message(payload)
            if message_data:
                route_message(
                    phone=message_data["phone"],
                    text=message_data["text"],
                    message_id=message_data["message_id"],
                    message_type=message_data["type"],
                )
        elif "statuses" in value:
            for status_obj in value.get("statuses", []):
                msg_id = status_obj.get("id", "")
                new_status = status_obj.get("status", "")
                if msg_id and new_status:
                    update_message_status(msg_id, new_status)
        else:
            logger.info("Unhandled webhook event — ignoring.")

    except Exception as exc:
        logger.error("Webhook processing error: %s", exc, exc_info=True)

    return {"status": "ok"}
