import os
import json
import hmac
import hashlib
import logging
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("whatsapp_groq")

# ── Config ────────────────────────────────────────────────────────────────────
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_secret_verify_token")
WA_TOKEN     = os.getenv("WA_TOKEN", "")
PHONE_ID     = os.getenv("PHONE_ID", "")
APP_SECRET   = os.getenv("APP_SECRET", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# ── Groq client ───────────────────────────────────────────────────────────────
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

app = FastAPI(title="WhatsApp + Groq AI", version="1.0.0")

# ══════════════════════════════════════════════════════════════════════════════
#  CONVERSATION MEMORY
#  Stores last N messages per user so Groq has context across replies.
#  In production replace this dict with Redis.
# ══════════════════════════════════════════════════════════════════════════════
MAX_HISTORY = 10   # messages to remember per user

conversation_history: dict[str, list[dict]] = {}

def get_history(sender: str) -> list[dict]:
    return conversation_history.get(sender, [])

def add_to_history(sender: str, role: str, content: str):
    if sender not in conversation_history:
        conversation_history[sender] = []
    conversation_history[sender].append({"role": role, "content": content})
    # Keep only last MAX_HISTORY messages
    if len(conversation_history[sender]) > MAX_HISTORY:
        conversation_history[sender] = conversation_history[sender][-MAX_HISTORY:]

def clear_history(sender: str):
    conversation_history.pop(sender, None)


# ══════════════════════════════════════════════════════════════════════════════
#  GROQ — ask AI and get a reply
# ══════════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are a helpful, friendly assistant integrated into WhatsApp.
Keep your responses concise and conversational — this is a chat interface, 
not an email. Use plain text only, no markdown formatting like ** or ##.
If the user asks something you don't know, say so honestly.
"""

async def ask_groq(sender: str, user_message: str) -> str:
    """Send message to Groq with conversation history, return AI reply."""
    try:
        # Add user message to history
        add_to_history(sender, "user", user_message)

        # Build messages: system prompt + full conversation history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += get_history(sender)

        log.info("Sending to Groq — model=%s history_len=%d", GROQ_MODEL, len(get_history(sender)))

        response = await groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )

        ai_reply = response.choices[0].message.content.strip()

        # Add AI reply to history so next message has full context
        add_to_history(sender, "assistant", ai_reply)

        log.info("Groq replied (%d chars)", len(ai_reply))
        return ai_reply

    except Exception as e:
        log.error("Groq API error: %s", e)
        return "Sorry, I'm having trouble thinking right now. Please try again in a moment."


# ══════════════════════════════════════════════════════════════════════════════
#  WHATSAPP — send a reply back
# ══════════════════════════════════════════════════════════════════════════════
async def send_whatsapp(to: str, message: str):
    """Send a WhatsApp text message."""
    if not WA_TOKEN or not PHONE_ID:
        log.warning("WA_TOKEN or PHONE_ID not set — skipping send")
        return

    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type":    "individual",
                "to":                to,
                "type":              "text",
                "text":              {"preview_url": False, "body": message},
            },
            timeout=10,
        )

    if resp.status_code == 200:
        log.info("WhatsApp reply sent to %s", to)
    else:
        log.error("WhatsApp send failed: %s — %s", resp.status_code, resp.text)


# ══════════════════════════════════════════════════════════════════════════════
#  SIGNATURE VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════
def verify_signature(body: bytes, sig_header: str | None) -> bool:
    if not APP_SECRET:
        return True
    if not sig_header:
        return False
    expected = "sha256=" + hmac.new(
        APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig_header)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTE — GET /webhook  (Meta verification handshake)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/webhook")
async def verify_webhook(request: Request):
    params    = dict(request.query_params)
    mode      = params.get("hub.mode")
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    log.info("Verification request — mode=%s", mode)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        log.info("Webhook verified OK")
        return PlainTextResponse(content=challenge, status_code=200)

    log.warning("Verification failed — wrong token")
    raise HTTPException(status_code=403, detail="Verification failed")


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTE — POST /webhook  (incoming WhatsApp messages)
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/webhook")
async def receive_message(request: Request):
    raw_body = await request.body()

    # Signature check
    if not verify_signature(raw_body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Pretty print full payload
    log.info("─" * 55)
    log.info("WEBHOOK PAYLOAD:\n%s", json.dumps(body, indent=2, ensure_ascii=False))
    log.info("─" * 55)

    try:
        value    = body["entry"][0]["changes"][0]["value"]
        messages = value.get("messages", [])

        # Ignore delivery/read receipts
        if "statuses" in value or not messages:
            return {"status": "ok"}

        msg      = messages[0]
        sender   = msg["from"]
        msg_type = msg.get("type")
        ts       = datetime.fromtimestamp(int(msg.get("timestamp", 0)))

        log.info("FROM : %s  |  TYPE : %s  |  TIME : %s",
                 sender, msg_type, ts.strftime("%d-%b-%Y %H:%M:%S"))

        # ── Text message → send to Groq ───────────────────────────────────
        if msg_type == "text":
            user_text = msg["text"]["body"].strip()
            log.info("USER : %s", user_text)

            # Special command: clear conversation memory
            if user_text.lower() in ("reset", "clear", "/reset", "/clear"):
                clear_history(sender)
                await send_whatsapp(sender, "Conversation cleared! Let's start fresh.")
                return {"status": "ok"}

            # Send to Groq → get AI reply → send back via WhatsApp
            ai_reply = await ask_groq(sender, user_text)
            log.info("GROQ : %s", ai_reply[:120] + ("..." if len(ai_reply) > 120 else ""))
            await send_whatsapp(sender, ai_reply)

        # ── Image / audio / other ─────────────────────────────────────────
        else:
            await send_whatsapp(
                sender,
                "I can only understand text messages right now. Please type your question."
            )

    except (KeyError, IndexError, TypeError) as e:
        log.debug("Could not parse payload: %s", e)

    # Always return 200 — Meta retries on anything else
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTE — GET /  (health check)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/")
async def health():
    return {
        "status":     "running",
        "ai_model":   GROQ_MODEL,
        "groq":       "configured" if GROQ_API_KEY else "NOT SET",
        "whatsapp":   "configured" if (WA_TOKEN and PHONE_ID) else "NOT SET",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTE — GET /history/{phone}  (debug — view conversation memory)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/history/{phone}")
async def view_history(phone: str):
    """Debug endpoint — see what the bot remembers about a user."""
    return {
        "phone":    phone,
        "messages": get_history(phone),
        "count":    len(get_history(phone)),
    }