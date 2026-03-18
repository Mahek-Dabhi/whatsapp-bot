"""
ai_chatbot.py  —  Pure Groq ChatGPT-like chatbot
Replace your existing whatsapp_bot_v2/bot/ai_chatbot.py with this file.
"""

import os
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a smart, friendly and helpful AI assistant on WhatsApp.
You can help with anything — answering questions, solving maths, writing, coding, 
explaining topics, giving advice, telling jokes, and much more.
Keep your replies conversational and concise since this is WhatsApp.
Use emojis where appropriate to make replies friendly. 😊"""

# ── Per-user conversation history ─────────────────────────────────────────────
_history: dict[str, list] = {}

def _get_history(phone: str) -> list:
    if phone not in _history:
        _history[phone] = []
    return _history[phone]

def clear_history(phone: str):
    _history.pop(phone, None)


# ── Main async function ────────────────────────────────────────────────────────
async def get_ai_response(phone: str, message: str) -> str:
    if not GROQ_API_KEY:
        return "⚠️ Groq API key not configured. Please add GROQ_API_KEY to your .env file."

    try:
        client  = Groq(api_key=GROQ_API_KEY)
        history = _get_history(phone)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += history[-10:]  # last 5 exchanges
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        reply = response.choices[0].message.content.strip()

        # Save to history
        history.append({"role": "user",      "content": message})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            _history[phone] = history[-20:]

        logger.info(f"Groq response sent to {phone}.")
        return reply

    except Exception as e:
        logger.error(f"Groq chatbot error for {phone}: {e}")
        return "Sorry, I couldn't process your request right now. Please try again! 😊"


# ── Sync wrapper called by message_router.py ──────────────────────────────────
def chat(phone: str, message: str) -> None:
    import asyncio
    from services.whatsapp_service import send_text_message
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, get_ai_response(phone, message))
                reply  = future.result(timeout=30)
        else:
            reply = loop.run_until_complete(get_ai_response(phone, message))
    except Exception as e:
        logger.error(f"chat() wrapper error for {phone}: {e}")
        reply = "Sorry, I couldn't process your request. Please try again! 😊"
    send_text_message(phone, reply)