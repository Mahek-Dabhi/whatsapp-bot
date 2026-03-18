"""
google_sheets.py
----------------
Google Sheets integration for reading/writing contact and campaign data.
Uses the gspread library with a service-account credentials file.
"""

from typing import Any, Dict, List, Optional
from app.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_client():
    """
    Authenticate with Google Sheets API using a service-account JSON file.

    Returns:
        Authenticated gspread Client.

    Raises:
        ImportError: If gspread is not installed.
        FileNotFoundError: If the credentials file is missing.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise ImportError(
            "gspread and google-auth are required for Google Sheets integration. "
            "Install with: pip install gspread google-auth"
        ) from exc

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(
        settings.GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scopes
    )
    return gspread.authorize(creds)


def read_contacts_from_sheet(
    sheet_name: str = "Contacts",
    spreadsheet_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Read contact rows from a Google Sheet.

    The sheet must have a header row with at least a 'phone' column.
    Optional columns: name, email, tags.

    Args:
        sheet_name:     Name of the worksheet tab.
        spreadsheet_id: Google Sheet ID (defaults to GOOGLE_SHEET_ID in env).

    Returns:
        List of dicts representing contact rows.
    """
    sid = spreadsheet_id or settings.GOOGLE_SHEET_ID
    if not sid:
        raise ValueError("GOOGLE_SHEET_ID is not configured.")

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(sid)
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        logger.info("Read %d contacts from Google Sheet '%s'.", len(records), sheet_name)
        return records
    except Exception as exc:
        logger.error("read_contacts_from_sheet failed: %s", exc)
        raise


def append_contact_to_sheet(
    contact: Dict[str, Any],
    sheet_name: str = "Contacts",
    spreadsheet_id: Optional[str] = None,
) -> None:
    """
    Append a single contact row to a Google Sheet.

    Args:
        contact:        Dict with keys: phone, name, email, tags.
        sheet_name:     Worksheet tab name.
        spreadsheet_id: Google Sheet ID.
    """
    sid = spreadsheet_id or settings.GOOGLE_SHEET_ID
    if not sid:
        raise ValueError("GOOGLE_SHEET_ID is not configured.")

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(sid)
        worksheet = spreadsheet.worksheet(sheet_name)
        row = [
            contact.get("phone", ""),
            contact.get("name", ""),
            contact.get("email", ""),
            ", ".join(contact.get("tags", [])),
        ]
        worksheet.append_row(row)
        logger.info("Contact %s appended to Google Sheet.", contact.get("phone"))
    except Exception as exc:
        logger.error("append_contact_to_sheet failed: %s", exc)
        raise


def log_message_to_sheet(
    phone: str,
    direction: str,
    body: str,
    sheet_name: str = "MessageLog",
    spreadsheet_id: Optional[str] = None,
) -> None:
    """
    Append a message log entry to a Google Sheet.

    Args:
        phone:          Contact phone number.
        direction:      'inbound' or 'outbound'.
        body:           Message text.
        sheet_name:     Worksheet tab name.
        spreadsheet_id: Google Sheet ID.
    """
    from utils.helpers import utc_now

    sid = spreadsheet_id or settings.GOOGLE_SHEET_ID
    if not sid:
        logger.warning("GOOGLE_SHEET_ID not set — skipping sheet log.")
        return

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(sid)
        worksheet = spreadsheet.worksheet(sheet_name)
        row = [str(utc_now()), phone, direction, body[:500]]
        worksheet.append_row(row)
    except Exception as exc:
        logger.error("log_message_to_sheet failed: %s", exc)


def sync_contacts_from_sheet() -> Dict[str, int]:
    """
    Import all contacts from the default Google Sheet into MongoDB.

    Returns:
        Dict with imported and skipped counts.
    """
    from services.contact_service import add_contact

    records = read_contacts_from_sheet()
    imported, skipped = 0, 0

    for row in records:
        phone = str(row.get("phone", "")).strip()
        if not phone:
            skipped += 1
            continue
        try:
            tags_raw = str(row.get("tags", ""))
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            add_contact(
                phone=phone,
                name=str(row.get("name", "")),
                email=str(row.get("email", "")),
                tags=tags,
            )
            imported += 1
        except Exception as exc:
            logger.warning("Skipping row (phone=%s): %s", phone, exc)
            skipped += 1

    logger.info("Sheet sync complete — imported=%d, skipped=%d.", imported, skipped)
    return {"imported": imported, "skipped": skipped}
