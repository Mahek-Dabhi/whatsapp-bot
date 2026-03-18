"""
media_service.py
----------------
Service for sending all WhatsApp media message types:
  - Images
  - Videos
  - Audio / voice notes
  - Documents (PDF, etc.)
  - Stickers
"""

from typing import Optional
import requests
from app.config import settings
from database.message_model import log_message
from database.analytics_model import record_event
from utils.logger import get_logger

logger = get_logger(__name__)


def _post_media(phone: str, payload: dict) -> Optional[str]:
    """
    Internal helper — post a media payload and return the message ID.

    Args:
        phone:   Recipient phone.
        payload: WhatsApp API payload dict.

    Returns:
        WhatsApp message ID on success, None on failure.
    """
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            settings.WHATSAPP_API_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("messages", [{}])[0].get("id", "")
    except requests.HTTPError as exc:
        logger.error("Media send failed (%s): %s", response.status_code, response.text)
        return None
    except Exception as exc:
        logger.error("_post_media unexpected error: %s", exc)
        return None


def send_image(phone: str, image_url: str, caption: str = "") -> Optional[str]:
    """
    Send an image message via URL.

    Args:
        phone:     Recipient phone number.
        image_url: Public HTTPS URL of the image.
        caption:   Optional caption text.

    Returns:
        WhatsApp message ID or None.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "image",
        "image": {"link": image_url, "caption": caption},
    }
    msg_id = _post_media(phone, payload)
    if msg_id:
        log_message(phone, "outbound", "image", body=caption, message_id=msg_id)
        record_event("media_sent", phone=phone, extra={"media_type": "image"})
        logger.info("Image sent to %s.", phone)
    return msg_id


def send_video(phone: str, video_url: str, caption: str = "") -> Optional[str]:
    """
    Send a video message via URL.

    Args:
        phone:     Recipient phone number.
        video_url: Public HTTPS URL of the video.
        caption:   Optional caption text.

    Returns:
        WhatsApp message ID or None.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "video",
        "video": {"link": video_url, "caption": caption},
    }
    msg_id = _post_media(phone, payload)
    if msg_id:
        log_message(phone, "outbound", "video", body=caption, message_id=msg_id)
        record_event("media_sent", phone=phone, extra={"media_type": "video"})
        logger.info("Video sent to %s.", phone)
    return msg_id


def send_document(
    phone: str,
    document_url: str,
    filename: str = "document.pdf",
    caption: str = "",
) -> Optional[str]:
    """
    Send a document (PDF, DOCX, etc.) message via URL.

    Args:
        phone:        Recipient phone number.
        document_url: Public HTTPS URL of the document.
        filename:     Suggested filename shown in chat.
        caption:      Optional caption text.

    Returns:
        WhatsApp message ID or None.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "document",
        "document": {
            "link": document_url,
            "caption": caption,
            "filename": filename,
        },
    }
    msg_id = _post_media(phone, payload)
    if msg_id:
        log_message(phone, "outbound", "document", body=caption, message_id=msg_id)
        record_event("media_sent", phone=phone, extra={"media_type": "document"})
        logger.info("Document '%s' sent to %s.", filename, phone)
    return msg_id


def send_audio(phone: str, audio_url: str) -> Optional[str]:
    """
    Send an audio / voice note message via URL.

    Args:
        phone:     Recipient phone number.
        audio_url: Public HTTPS URL of the audio file (OGG/Opus preferred).

    Returns:
        WhatsApp message ID or None.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "audio",
        "audio": {"link": audio_url},
    }
    msg_id = _post_media(phone, payload)
    if msg_id:
        log_message(phone, "outbound", "audio", message_id=msg_id)
        record_event("media_sent", phone=phone, extra={"media_type": "audio"})
        logger.info("Audio sent to %s.", phone)
    return msg_id


def send_sticker(phone: str, sticker_url: str) -> Optional[str]:
    """
    Send a WebP sticker via URL.

    Args:
        phone:       Recipient phone.
        sticker_url: Public HTTPS URL of the sticker (.webp).

    Returns:
        WhatsApp message ID or None.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "sticker",
        "sticker": {"link": sticker_url},
    }
    msg_id = _post_media(phone, payload)
    if msg_id:
        log_message(phone, "outbound", "sticker", message_id=msg_id)
    return msg_id
