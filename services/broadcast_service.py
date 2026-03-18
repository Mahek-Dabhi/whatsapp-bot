"""
broadcast_service.py
--------------------
Service for sending bulk messages and managing broadcast campaigns.
Implements rate-throttled sending to respect WhatsApp API limits.
"""

import time
from typing import List, Optional
from services.whatsapp_service import send_text_message
from services.media_service import send_image, send_video, send_document, send_audio
from database.contact_model import get_all_contacts, get_contacts_by_tag
from database.campaign_model import (
    create_campaign, update_campaign_status, get_pending_campaigns
)
from database.analytics_model import record_event
from utils.logger import get_logger
from utils.helpers import chunk_list

logger = get_logger(__name__)

# Delay between individual messages to avoid rate-limit bans (seconds)
MESSAGE_DELAY_SECONDS = 1.0


def broadcast_text(
    message: str,
    phones: Optional[List[str]] = None,
    tag: Optional[str] = None,
    campaign_name: str = "Manual Broadcast",
) -> dict:
    """
    Send a text message to multiple recipients.

    Args:
        message:       Message body.
        phones:        Explicit list of phone numbers (overrides tag).
        tag:           Contact segment tag (used if phones is empty).
        campaign_name: Display name for logging.

    Returns:
        Dict with sent_count and failed_count.
    """
    recipients = _resolve_recipients(phones, tag)
    if not recipients:
        logger.warning("broadcast_text: no recipients found.")
        return {"sent_count": 0, "failed_count": 0}

    campaign_id = create_campaign(
        name=campaign_name,
        message=message,
        target_tag=tag,
        target_phones=phones or [],
    )
    update_campaign_status(campaign_id, "running")

    sent, failed = 0, 0
    for phone in recipients:
        result = send_text_message(phone, message)
        if result:
            sent += 1
        else:
            failed += 1
        time.sleep(MESSAGE_DELAY_SECONDS)

    update_campaign_status(campaign_id, "completed", sent_count=sent, failed_count=failed)
    record_event("campaign_completed", campaign_id=campaign_id)
    logger.info("Broadcast '%s' done — sent=%d, failed=%d.", campaign_name, sent, failed)
    return {"sent_count": sent, "failed_count": failed, "campaign_id": campaign_id}


def broadcast_media(
    media_url: str,
    media_type: str,
    caption: str = "",
    phones: Optional[List[str]] = None,
    tag: Optional[str] = None,
    campaign_name: str = "Media Broadcast",
) -> dict:
    """
    Send a media message to multiple recipients.

    Args:
        media_url:  Public HTTPS URL of the media file.
        media_type: 'image' | 'video' | 'audio' | 'document'.
        caption:    Optional caption text.
        phones:     Explicit phone list.
        tag:        Segment tag.
        campaign_name: Display name.

    Returns:
        Dict with sent_count and failed_count.
    """
    recipients = _resolve_recipients(phones, tag)
    if not recipients:
        logger.warning("broadcast_media: no recipients found.")
        return {"sent_count": 0, "failed_count": 0}

    sender_map = {
        "image": lambda p: send_image(p, media_url, caption),
        "video": lambda p: send_video(p, media_url, caption),
        "audio": lambda p: send_audio(p, media_url),
        "document": lambda p: send_document(p, media_url, caption=caption),
    }
    sender = sender_map.get(media_type)
    if not sender:
        raise ValueError(f"Unsupported media_type: '{media_type}'")

    campaign_id = create_campaign(
        name=campaign_name,
        message=caption,
        target_tag=tag,
        target_phones=phones or [],
        media_url=media_url,
        media_type=media_type,
    )
    update_campaign_status(campaign_id, "running")

    sent, failed = 0, 0
    for phone in recipients:
        result = sender(phone)
        if result:
            sent += 1
        else:
            failed += 1
        time.sleep(MESSAGE_DELAY_SECONDS)

    update_campaign_status(campaign_id, "completed", sent_count=sent, failed_count=failed)
    logger.info("Media broadcast done — sent=%d, failed=%d.", sent, failed)
    return {"sent_count": sent, "failed_count": failed, "campaign_id": campaign_id}


def run_pending_campaigns() -> None:
    """
    Check for pending scheduled campaigns and execute them.
    Called periodically by the APScheduler job.
    """
    campaigns = get_pending_campaigns()
    logger.info("Checking pending campaigns — found %d.", len(campaigns))
    for campaign in campaigns:
        cid = campaign["id"]
        try:
            broadcast_text(
                message=campaign["message"],
                phones=campaign.get("target_phones") or None,
                tag=campaign.get("target_tag"),
                campaign_name=campaign["name"],
            )
        except Exception as exc:
            logger.error("Failed to run campaign %s: %s", cid, exc)
            update_campaign_status(cid, "failed")


# ── Private helpers ───────────────────────────────────────────────────────────

def _resolve_recipients(
    phones: Optional[List[str]], tag: Optional[str]
) -> List[str]:
    """
    Resolve the final list of phone numbers to message.

    Priority: explicit phones → tag lookup → all contacts.

    Args:
        phones: Explicit phone list.
        tag:    Segment tag.

    Returns:
        Deduplicated list of phone numbers.
    """
    if phones:
        return list(set(phones))
    if tag:
        contacts = get_contacts_by_tag(tag)
        return [c["phone"] for c in contacts]
    # Fall back to all opted-in contacts
    contacts = get_all_contacts()
    return [c["phone"] for c in contacts]
