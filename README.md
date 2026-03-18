# 🤖 WhatsApp Automation Bot

A **production-ready** WhatsApp automation backend built with **Python**, **FastAPI**, **MongoDB**, and the **WhatsApp Cloud API**. Features an AI chatbot fallback powered by OpenAI, a full scheduling engine, bulk broadcasting, contact management, analytics, and security controls.

---

## 📁 Project Structure

```
whatsapp_automation_bot/
├── app/
│   ├── main.py              # FastAPI app factory + all API routes
│   ├── webhook.py           # WhatsApp webhook verification & message reception
│   └── config.py            # Centralised settings from .env
├── bot/
│   ├── message_router.py    # Central inbound message pipeline
│   ├── command_handler.py   # /help, /price, /order, /contact, /status
│   ├── keyword_handler.py   # Keyword → auto-reply matching
│   └── ai_chatbot.py        # OpenAI GPT fallback with per-user history
├── services/
│   ├── whatsapp_service.py  # Send text, templates, read receipts
│   ├── media_service.py     # Send images, videos, audio, documents
│   ├── broadcast_service.py # Bulk and group broadcasting
│   ├── contact_service.py   # Contact CRUD + CSV/Excel import
│   ├── analytics_service.py # Dashboard, campaign reports, daily stats
│   └── security_service.py  # Rate limiting, banning, admin checks
├── database/
│   ├── db_connection.py     # MongoDB singleton connection
│   ├── contact_model.py     # Contact CRUD helpers
│   ├── message_model.py     # Message log CRUD helpers
│   ├── campaign_model.py    # Campaign CRUD helpers
│   └── analytics_model.py   # Analytics event recording + aggregation
├── scheduler/
│   └── message_scheduler.py # APScheduler: daily msgs, birthday reminders, campaigns
├── integrations/
│   ├── google_sheets.py     # Read/write Google Sheets
│   ├── crm_integration.py   # Generic CRM REST API sync
│   └── website_api.py       # External website / product API hooks
├── utils/
│   ├── logger.py            # Rotating file + console logger
│   ├── validators.py        # Phone, URL, message validation
│   └── helpers.py           # Payload parsing, chunking, hashing utilities
├── scripts/
│   ├── import_contacts.py   # CLI: import contacts from CSV/Excel
│   └── send_bulk_messages.py# CLI: send bulk broadcast from terminal
├── logs/                    # Auto-created; rotating bot.log
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourname/whatsapp_automation_bot.git
cd whatsapp_automation_bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
| Variable | Description |
|---|---|
| `WHATSAPP_TOKEN` | Meta Graph API Bearer token |
| `WHATSAPP_PHONE_NUMBER_ID` | Your WhatsApp business phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | Secret string for webhook verification |
| `MONGO_URI` | MongoDB connection string |
| `OPENAI_API_KEY` | OpenAI API key for AI fallback |

### 3. Start MongoDB

```bash
# Local (Docker)
docker run -d -p 27017:27017 --name mongo mongo:7
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Expose Webhook (Development)

```bash
# Use ngrok or cloudflared to expose localhost
ngrok http 8000
# Set the webhook URL in Meta Developer Console:
# https://<your-ngrok-url>/webhook
```

---

## 🔧 API Endpoints

### Health
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service health check |
| GET | `/health` | DB + scheduler status |

### Webhook
| Method | Endpoint | Description |
|---|---|---|
| GET | `/webhook` | WhatsApp verification challenge |
| POST | `/webhook` | Inbound messages & status events |

### Messages
| Method | Endpoint | Description |
|---|---|---|
| POST | `/messages/send` | Send instant text message |
| POST | `/messages/send-image` | Send image |
| POST | `/messages/send-video` | Send video |
| POST | `/messages/send-document` | Send PDF/document |
| POST | `/messages/send-audio` | Send audio/voice note |
| POST | `/messages/broadcast` | Send bulk text broadcast |
| POST | `/messages/broadcast-media` | Send bulk media broadcast |

### Scheduler
| Method | Endpoint | Description |
|---|---|---|
| POST | `/scheduler/schedule-message` | Schedule single message |
| POST | `/scheduler/schedule-campaign` | Schedule bulk campaign |
| GET | `/scheduler/jobs` | List all scheduled jobs |
| DELETE | `/scheduler/jobs/{job_id}` | Cancel a scheduled job |

### Contacts
| Method | Endpoint | Description |
|---|---|---|
| POST | `/contacts` | Add/update contact |
| GET | `/contacts` | List contacts (optional `?tag=` filter) |
| DELETE | `/contacts/{phone}` | Delete contact |
| POST | `/contacts/tag` | Tag a contact |
| POST | `/contacts/import/csv` | Import from CSV upload |
| POST | `/contacts/import/excel` | Import from Excel upload |

### Analytics
| Method | Endpoint | Description |
|---|---|---|
| GET | `/analytics/dashboard` | Full stats snapshot |
| GET | `/analytics/campaigns/{id}` | Campaign performance |
| GET | `/analytics/messages/daily` | Per-day message volume |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| POST | `/admin/ban` | Ban a phone number |
| POST | `/admin/unban/{phone}` | Unban a phone number |
| POST | `/admin/sync/crm` | Sync contacts from CRM |
| POST | `/admin/sync/sheets` | Sync contacts from Google Sheets |

---

## 🤖 Bot Message Flow

```
Inbound WhatsApp Message
        │
        ▼
 [Security Gate]  ────── Banned / Rate-limited? ──► Silently drop
        │
        ▼
 [Command Handler] ──── /help, /price, /order? ──► Pre-defined response
        │ (no match)
        ▼
 [Keyword Handler] ──── hi, hello, thanks? ──────► Auto-reply
        │ (no match)
        ▼
 [AI Chatbot] ─────────── OpenAI GPT fallback ───► Dynamic response
```

---

## 📋 Bot Commands

| Command | Response |
|---|---|
| `/help` | Show all available commands |
| `/price` | Display pricing information |
| `/order` | How to place an order |
| `/contact` | Support contact details |
| `/status` | Bot online status |

---

## 📅 Scheduler Jobs

| Job | Schedule | Description |
|---|---|---|
| Pending Campaign Sweeper | Every 5 min | Runs due campaigns |
| Birthday Reminders | Daily 09:00 UTC | Greets contacts with today's birthday |

---

## 🔒 Security Features

- **Rate limiting** — Sliding window (10 messages / 60 seconds by default)
- **Auto-ban** — Repeated rate-limit violations trigger a 1-hour ban
- **Admin-only commands** — Protected by `ADMIN_NUMBERS` env variable
- **Input validation** — Phone numbers, URLs, and message bodies validated before use

---

## 🛠 CLI Scripts

```bash
# Import contacts from CSV
python scripts/import_contacts.py --file contacts.csv

# Import from Excel
python scripts/import_contacts.py --file contacts.xlsx --type excel

# Send bulk broadcast (interactive confirmation)
python scripts/send_bulk_messages.py --message "Hello everyone!"

# Send to a segment tag
python scripts/send_bulk_messages.py --message "VIP offer!" --tag vip

# Dry run (preview only)
python scripts/send_bulk_messages.py --message "Test" --dry-run
```

---

## 🌐 Interactive API Docs

After starting the server, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📦 Tech Stack

| Component | Technology |
|---|---|
| Web Framework | FastAPI |
| Database | MongoDB (PyMongo) |
| Task Scheduler | APScheduler |
| AI Chatbot | OpenAI GPT-4o-mini |
| HTTP Client | requests |
| Data Import | pandas + openpyxl |
| Sheets Integration | gspread |
| Environment | python-dotenv |
| Logging | Python logging (rotating files) |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📝 License

MIT License — free to use and modify.
