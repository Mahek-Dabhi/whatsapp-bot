"""
config.py
---------
Centralised configuration loader for the WhatsApp Automation Bot.
All settings are read from environment variables (via .env) using python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load .env file into the environment
load_dotenv()


class Settings:
    """Application-wide settings loaded from environment variables."""

    # ── WhatsApp Cloud API ──────────────────────────────────────────────────
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token")
    WHATSAPP_API_VERSION: str = os.getenv("WHATSAPP_API_VERSION", "v19.0")

    @property
    def WHATSAPP_API_URL(self) -> str:
        """Construct the base WhatsApp send-message URL."""
        return (
            f"https://graph.facebook.com/{self.WHATSAPP_API_VERSION}"
            f"/{self.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

    # ── MongoDB ─────────────────────────────────────────────────────────────
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "whatsapp_bot")

    # ── OpenAI ──────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ── Google Sheets ────────────────────────────────────────────────────────
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = os.getenv(
        "GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json"
    )
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")

    # ── CRM ──────────────────────────────────────────────────────────────────
    CRM_API_URL: str = os.getenv("CRM_API_URL", "")
    CRM_API_KEY: str = os.getenv("CRM_API_KEY", "")

    # ── Security ─────────────────────────────────────────────────────────────
    ADMIN_NUMBERS: list[str] = [
        n.strip()
        for n in os.getenv("ADMIN_NUMBERS", "").split(",")
        if n.strip()
    ]
    RATE_LIMIT_MAX_MESSAGES: int = int(os.getenv("RATE_LIMIT_MAX_MESSAGES", "10"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # ── App ───────────────────────────────────────────────────────────────────
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")


# Singleton instance used across the project
settings = Settings()
