"""
message_scheduler.py
--------------------
APScheduler configuration and all scheduled job definitions.
Manages:
  - Daily scheduled messages
  - Birthday reminders
  - Marketing campaign execution
  - Pending campaign sweeper
"""

from datetime import datetime, timezone
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from services.whatsapp_service import send_text_message
from services.broadcast_service import broadcast_text, run_pending_campaigns
from database.contact_model import get_all_contacts
from app.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Scheduler singleton ───────────────────────────────────────────────────────
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Return the global BackgroundScheduler, creating it if necessary."""
    global _scheduler
    if _scheduler is None:
        _scheduler = _build_scheduler()
    return _scheduler


def _build_scheduler() -> BackgroundScheduler:
    """
    Construct and configure the APScheduler instance.
    Uses MongoDB as the persistent job store so scheduled jobs survive restarts.
    """
    try:
        jobstores = {
            "default": MongoDBJobStore(
                database=settings.MONGO_DB_NAME,
                collection="scheduled_jobs",
                host=settings.MONGO_URI,
            )
        }
    except Exception as exc:
        logger.warning("MongoDB job store unavailable (%s) — using memory store.", exc)
        jobstores = {}

    executors = {"default": ThreadPoolExecutor(max_workers=5)}
    job_defaults = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 30}

    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="UTC",
    )
    logger.info("APScheduler configured.")
    return scheduler


def start_scheduler() -> None:
    """Start the background scheduler and register default recurring jobs."""
    scheduler = get_scheduler()
    if scheduler.running:
        logger.warning("Scheduler is already running.")
        return

    # Sweep pending campaigns every 5 minutes
    scheduler.add_job(
        run_pending_campaigns,
        trigger=IntervalTrigger(minutes=5),
        id="pending_campaign_sweeper",
        replace_existing=True,
        name="Pending Campaign Sweeper",
    )

    # Check birthday reminders once daily at 09:00 UTC
    scheduler.add_job(
        _send_birthday_reminders,
        trigger=CronTrigger(hour=9, minute=0),
        id="birthday_reminders",
        replace_existing=True,
        name="Birthday Reminders",
    )

    scheduler.start()
    logger.info("Scheduler started with %d jobs.", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Gracefully shut down the background scheduler."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


# ── Public scheduling API ─────────────────────────────────────────────────────

def schedule_message(
    phone: str,
    message: str,
    send_at: datetime,
    job_id: Optional[str] = None,
) -> str:
    """
    Schedule a single text message for a specific date/time.

    Args:
        phone:    Recipient phone number.
        message:  Text body.
        send_at:  UTC datetime when the message should be sent.
        job_id:   Optional unique job ID (auto-generated if None).

    Returns:
        The APScheduler job ID.
    """
    scheduler = get_scheduler()
    jid = job_id or f"msg_{phone}_{int(send_at.timestamp())}"

    scheduler.add_job(
        send_text_message,
        trigger=DateTrigger(run_date=send_at),
        args=[phone, message],
        id=jid,
        replace_existing=True,
        name=f"Scheduled msg → {phone}",
    )
    logger.info("Message to %s scheduled for %s (job=%s).", phone, send_at, jid)
    return jid


def schedule_daily_message(
    phone: str,
    message: str,
    hour: int,
    minute: int = 0,
    job_id: Optional[str] = None,
) -> str:
    """
    Schedule a recurring daily text message.

    Args:
        phone:   Recipient phone number.
        message: Text body.
        hour:    UTC hour (0–23).
        minute:  UTC minute (0–59).
        job_id:  Optional unique job ID.

    Returns:
        APScheduler job ID.
    """
    scheduler = get_scheduler()
    jid = job_id or f"daily_{phone}_{hour}{minute:02d}"

    scheduler.add_job(
        send_text_message,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[phone, message],
        id=jid,
        replace_existing=True,
        name=f"Daily msg → {phone} at {hour:02d}:{minute:02d}",
    )
    logger.info("Daily message to %s set at %02d:%02d UTC (job=%s).", phone, hour, minute, jid)
    return jid


def schedule_campaign(
    message: str,
    send_at: datetime,
    tag: Optional[str] = None,
    phones: Optional[List[str]] = None,
    campaign_name: str = "Scheduled Campaign",
) -> str:
    """
    Schedule a bulk broadcast campaign for a future datetime.

    Args:
        message:       Broadcast message body.
        send_at:       UTC datetime for the campaign.
        tag:           Segment tag to target.
        phones:        Explicit phone list.
        campaign_name: Human-readable campaign name.

    Returns:
        APScheduler job ID.
    """
    from database.campaign_model import create_campaign

    # Pre-create the campaign record
    campaign_id = create_campaign(
        name=campaign_name,
        message=message,
        target_tag=tag,
        target_phones=phones or [],
        scheduled_at=send_at,
    )

    scheduler = get_scheduler()
    jid = f"campaign_{campaign_id}"

    scheduler.add_job(
        broadcast_text,
        trigger=DateTrigger(run_date=send_at),
        kwargs={
            "message": message,
            "phones": phones,
            "tag": tag,
            "campaign_name": campaign_name,
        },
        id=jid,
        replace_existing=True,
        name=campaign_name,
    )
    logger.info("Campaign '%s' scheduled for %s (job=%s).", campaign_name, send_at, jid)
    return jid


def cancel_job(job_id: str) -> bool:
    """
    Cancel a scheduled job by ID.

    Args:
        job_id: APScheduler job ID.

    Returns:
        True if cancelled, False if not found.
    """
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        logger.info("Job '%s' cancelled.", job_id)
        return True
    except Exception:
        logger.warning("Job '%s' not found for cancellation.", job_id)
        return False


def list_jobs() -> List[dict]:
    """
    Return a summary of all scheduled jobs.

    Returns:
        List of dicts with id, name, next_run_time.
    """
    scheduler = get_scheduler()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        }
        for job in scheduler.get_jobs()
    ]


# ── Internal job functions ────────────────────────────────────────────────────

def _send_birthday_reminders() -> None:
    """
    Job: Find contacts with today's birthday and send them a greeting.
    Contacts must have a 'birthday' field in 'YYYY-MM-DD' format.
    """
    today = datetime.now(tz=timezone.utc).strftime("%m-%d")
    contacts = get_all_contacts()
    sent = 0

    for contact in contacts:
        birthday: str = contact.get("extra", {}).get("birthday", "")
        if not birthday:
            continue
        # Compare month-day only
        try:
            bday_md = datetime.strptime(birthday, "%Y-%m-%d").strftime("%m-%d")
        except ValueError:
            continue

        if bday_md == today:
            name = contact.get("name") or "there"
            msg = (
                f"🎂 Happy Birthday, {name}! 🥳\n\n"
                "Wishing you a wonderful day filled with joy. "
                "Thank you for being a valued customer!"
            )
            send_text_message(contact["phone"], msg)
            sent += 1

    logger.info("Birthday reminders sent: %d.", sent)
