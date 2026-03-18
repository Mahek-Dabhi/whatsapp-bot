"""
main.py
-------
FastAPI application factory and entry point for the WhatsApp Automation Bot.

Registers:
  - Webhook router      (/webhook)
  - Messaging endpoints (/messages/*)
  - Contact endpoints   (/contacts/*)
  - Campaign endpoints  (/campaigns/*)
  - Analytics endpoints (/analytics/*)
  - Admin endpoints     (/admin/*)
  - Scheduler lifecycle (/scheduler/*)

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.webhook import router as webhook_router
from database.db_connection import get_database, close_database
from scheduler.message_scheduler import start_scheduler, stop_scheduler, list_jobs, schedule_message, schedule_campaign, cancel_job
from services.whatsapp_service import send_text_message, send_template_message
from services.media_service import send_image, send_video, send_document, send_audio
from services.broadcast_service import broadcast_text, broadcast_media
from services.contact_service import add_contact, remove_contact, list_contacts, import_from_csv, import_from_excel, tag_contact
from services.analytics_service import get_dashboard_stats, get_campaign_report, get_message_stats_by_day
from services.security_service import ban_phone, unban_phone, is_admin
from utils.logger import get_logger
import tempfile, os, shutil

logger = get_logger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting WhatsApp Automation Bot …")
    try:
        get_database()           # Verify DB connection
        start_scheduler()        # Start APScheduler
        logger.info("Bot started successfully.")
    except Exception as exc:
        logger.error("Startup error: %s", exc)
    yield
    # Shutdown
    logger.info("Shutting down bot …")
    stop_scheduler()
    close_database()
    logger.info("Bot stopped.")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="WhatsApp Automation Bot",
    description="Production-ready WhatsApp Cloud API bot with AI, scheduling, and analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the webhook router
app.include_router(webhook_router)


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic request/response models
# ─────────────────────────────────────────────────────────────────────────────

class SendTextRequest(BaseModel):
    phone: str
    message: str

class SendMediaRequest(BaseModel):
    phone: str
    media_url: str
    caption: str = ""

class BroadcastRequest(BaseModel):
    message: str
    phones: Optional[List[str]] = None
    tag: Optional[str] = None
    campaign_name: str = "API Broadcast"

class MediaBroadcastRequest(BaseModel):
    media_url: str
    media_type: str          # image | video | audio | document
    caption: str = ""
    phones: Optional[List[str]] = None
    tag: Optional[str] = None
    campaign_name: str = "Media Broadcast"

class ScheduleMessageRequest(BaseModel):
    phone: str
    message: str
    send_at: datetime        # ISO-8601 UTC datetime

class ScheduleCampaignRequest(BaseModel):
    message: str
    send_at: datetime
    phones: Optional[List[str]] = None
    tag: Optional[str] = None
    campaign_name: str = "Scheduled Campaign"

class ContactRequest(BaseModel):
    phone: str
    name: str = ""
    email: str = ""
    tags: Optional[List[str]] = None

class TagRequest(BaseModel):
    phone: str
    tag: str

class BanRequest(BaseModel):
    phone: str
    duration_seconds: int = 3600


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Root health-check endpoint."""
    return {"status": "ok", "service": "WhatsApp Automation Bot", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    """Detailed health check."""
    try:
        db = get_database()
        db.command("ping")
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {
        "status": "ok",
        "database": db_status,
        "scheduler": "running",
        "environment": settings.ENVIRONMENT,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Messaging endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/messages/send", tags=["Messages"])
def api_send_text(req: SendTextRequest):
    """Send an instant text message to a single number."""
    msg_id = send_text_message(req.phone, req.message)
    if not msg_id:
        raise HTTPException(status_code=502, detail="Failed to send message.")
    return {"status": "sent", "message_id": msg_id}


@app.post("/messages/send-image", tags=["Messages"])
def api_send_image(req: SendMediaRequest):
    """Send an image message."""
    msg_id = send_image(req.phone, req.media_url, req.caption)
    if not msg_id:
        raise HTTPException(status_code=502, detail="Failed to send image.")
    return {"status": "sent", "message_id": msg_id}


@app.post("/messages/send-video", tags=["Messages"])
def api_send_video(req: SendMediaRequest):
    """Send a video message."""
    msg_id = send_video(req.phone, req.media_url, req.caption)
    if not msg_id:
        raise HTTPException(status_code=502, detail="Failed to send video.")
    return {"status": "sent", "message_id": msg_id}


@app.post("/messages/send-document", tags=["Messages"])
def api_send_document(req: SendMediaRequest):
    """Send a document/PDF message."""
    msg_id = send_document(req.phone, req.media_url, caption=req.caption)
    if not msg_id:
        raise HTTPException(status_code=502, detail="Failed to send document.")
    return {"status": "sent", "message_id": msg_id}


@app.post("/messages/send-audio", tags=["Messages"])
def api_send_audio(req: SendMediaRequest):
    """Send an audio/voice note message."""
    msg_id = send_audio(req.phone, req.media_url)
    if not msg_id:
        raise HTTPException(status_code=502, detail="Failed to send audio.")
    return {"status": "sent", "message_id": msg_id}


@app.post("/messages/broadcast", tags=["Messages"])
def api_broadcast(req: BroadcastRequest):
    """Send a bulk text broadcast to a list of numbers or a segment tag."""
    result = broadcast_text(
        message=req.message,
        phones=req.phones,
        tag=req.tag,
        campaign_name=req.campaign_name,
    )
    return result


@app.post("/messages/broadcast-media", tags=["Messages"])
def api_broadcast_media(req: MediaBroadcastRequest):
    """Send a bulk media broadcast."""
    result = broadcast_media(
        media_url=req.media_url,
        media_type=req.media_type,
        caption=req.caption,
        phones=req.phones,
        tag=req.tag,
        campaign_name=req.campaign_name,
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Scheduling endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/scheduler/schedule-message", tags=["Scheduler"])
def api_schedule_message(req: ScheduleMessageRequest):
    """Schedule a single message for a future UTC datetime."""
    job_id = schedule_message(req.phone, req.message, req.send_at)
    return {"status": "scheduled", "job_id": job_id, "send_at": str(req.send_at)}


@app.post("/scheduler/schedule-campaign", tags=["Scheduler"])
def api_schedule_campaign(req: ScheduleCampaignRequest):
    """Schedule a bulk broadcast campaign for a future datetime."""
    job_id = schedule_campaign(
        message=req.message,
        send_at=req.send_at,
        phones=req.phones,
        tag=req.tag,
        campaign_name=req.campaign_name,
    )
    return {"status": "scheduled", "job_id": job_id}


@app.delete("/scheduler/jobs/{job_id}", tags=["Scheduler"])
def api_cancel_job(job_id: str):
    """Cancel a scheduled job by its ID."""
    cancelled = cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"status": "cancelled", "job_id": job_id}


@app.get("/scheduler/jobs", tags=["Scheduler"])
def api_list_jobs():
    """List all scheduled jobs."""
    return {"jobs": list_jobs()}


# ─────────────────────────────────────────────────────────────────────────────
# Contact management endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/contacts", tags=["Contacts"])
def api_add_contact(req: ContactRequest):
    """Add or update a contact."""
    contact = add_contact(req.phone, req.name, req.email, req.tags)
    return {"status": "ok", "contact": contact}


@app.delete("/contacts/{phone}", tags=["Contacts"])
def api_delete_contact(phone: str):
    """Delete a contact by phone number."""
    deleted = remove_contact(phone)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found.")
    return {"status": "deleted"}


@app.get("/contacts", tags=["Contacts"])
def api_list_contacts(tag: Optional[str] = None):
    """List all contacts, optionally filtered by tag."""
    contacts = list_contacts(tag)
    return {"count": len(contacts), "contacts": contacts}


@app.post("/contacts/tag", tags=["Contacts"])
def api_tag_contact(req: TagRequest):
    """Add a tag/segment to a contact."""
    tag_contact(req.phone, req.tag)
    return {"status": "tagged", "phone": req.phone, "tag": req.tag}


@app.post("/contacts/import/csv", tags=["Contacts"])
async def api_import_csv(file: UploadFile = File(...)):
    """Import contacts from an uploaded CSV file."""
    tmp_path = _save_upload(file)
    try:
        result = import_from_csv(tmp_path)
    finally:
        os.remove(tmp_path)
    return result


@app.post("/contacts/import/excel", tags=["Contacts"])
async def api_import_excel(file: UploadFile = File(...)):
    """Import contacts from an uploaded Excel (.xlsx) file."""
    tmp_path = _save_upload(file)
    try:
        result = import_from_excel(tmp_path)
    finally:
        os.remove(tmp_path)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Analytics endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/analytics/dashboard", tags=["Analytics"])
def api_dashboard():
    """Return the full analytics dashboard snapshot."""
    return get_dashboard_stats()


@app.get("/analytics/campaigns/{campaign_id}", tags=["Analytics"])
def api_campaign_report(campaign_id: str):
    """Return performance stats for a specific campaign."""
    return get_campaign_report(campaign_id)


@app.get("/analytics/messages/daily", tags=["Analytics"])
def api_daily_messages(days: int = 7):
    """Return per-day message volume for the last N days."""
    return get_message_stats_by_day(days)


# ─────────────────────────────────────────────────────────────────────────────
# Admin endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/admin/ban", tags=["Admin"])
def api_ban(req: BanRequest):
    """Temporarily ban a phone number from using the bot."""
    ban_phone(req.phone, req.duration_seconds)
    return {"status": "banned", "phone": req.phone, "duration_seconds": req.duration_seconds}


@app.post("/admin/unban/{phone}", tags=["Admin"])
def api_unban(phone: str):
    """Lift a ban from a phone number."""
    unban_phone(phone)
    return {"status": "unbanned", "phone": phone}


@app.post("/admin/sync/crm", tags=["Admin"])
def api_sync_crm():
    """Sync contacts from CRM into MongoDB."""
    from integrations.crm_integration import sync_crm_to_mongo
    return sync_crm_to_mongo()


@app.post("/admin/sync/sheets", tags=["Admin"])
def api_sync_sheets():
    """Sync contacts from Google Sheets into MongoDB."""
    from integrations.google_sheets import sync_contacts_from_sheet
    return sync_contacts_from_sheet()


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _save_upload(file: UploadFile) -> str:
    """
    Save an uploaded file to a temporary path and return that path.

    Args:
        file: FastAPI UploadFile object.

    Returns:
        Absolute path to the saved temporary file.
    """
    suffix = os.path.splitext(file.filename or "upload")[1] or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        return tmp.name
