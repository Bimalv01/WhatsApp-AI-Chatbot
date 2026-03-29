# WhatsApp AI Chatbot — Powered by Groq + FastAPI

A WhatsApp chatbot that uses **Groq AI** (free, ultra-fast LLM) to reply to messages
in real time. Built with **Python + FastAPI**, exposed via **ngrok** during development.

---

## What it does

- Receives WhatsApp messages via Meta Cloud API
- Sends each message to Groq AI (LLaMA 3 model)
- Remembers conversation history per user (up to 10 messages)
- Replies back to the user on WhatsApp instantly
- Supports `reset` / `clear` command to wipe conversation memory

---

## Project Structure

```
WhatAppAi/
├── main.py            ← FastAPI server — all webhook + AI logic
├── run.py             ← Starts uvicorn + ngrok tunnel together
├── test.py            ← Local tests — simulate Meta requests
├── requirements.txt   ← Python dependencies
├── .env               ← Your secret keys (never commit this)
└── README.md
```

---

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Language    | Python 3.13                         |
| Web server  | FastAPI + Uvicorn                   |
| AI model    | Groq API (LLaMA 3 / Mixtral)        |
| WhatsApp    | Meta WhatsApp Cloud API             |
| Tunnel      | ngrok (dev) / Railway or Render (prod) |
| HTTP client | httpx (async)                       |

---

## Prerequisites

- Python 3.10 or higher
- A **Meta Developer account** — developers.facebook.com
- A **Groq API key** (free) — console.groq.com
- An **ngrok account** (free) — ngrok.com

---

## Installation

### 1. Clone or download the project

```bash
cd your-project-folder
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / Mac
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# WhatsApp (Meta Developer Portal)
VERIFY_TOKEN=my_secret_verify_token    # any word you choose
WA_TOKEN=EAAxxxxxxxxxxxxxxxx           # Meta Portal → WhatsApp → API Setup
PHONE_ID=12345678901234                # Meta Portal → WhatsApp → API Setup
APP_SECRET=                            # optional — Meta Portal → App Settings → Basic

# Groq AI (console.groq.com)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama3-8b-8192

# ngrok (dashboard.ngrok.com)
NGROK_TOKEN=2xxxxxxxxxxxxxxxxxxxxxxxx
```

### Where to find each key

| Key           | Location                                                      |
|---------------|---------------------------------------------------------------|
| `VERIFY_TOKEN`| You choose this — any secret word                            |
| `WA_TOKEN`    | Meta Developer Portal → WhatsApp → API Setup → Access Token  |
| `PHONE_ID`    | Meta Developer Portal → WhatsApp → API Setup → Phone Number ID |
| `APP_SECRET`  | Meta Developer Portal → App Settings → Basic → App Secret    |
| `GROQ_API_KEY`| console.groq.com → API Keys → Create new key                 |
| `NGROK_TOKEN` | dashboard.ngrok.com → Getting Started → Your Authtoken       |

---

## Running the Server

```bash
python run.py
```

You will see:

```
════════════════════════════════════════════════════════════
  NGROK TUNNEL IS LIVE
════════════════════════════════════════════════════════════
  Webhook URL  :  https://abc123.ngrok-free.app/webhook
  Verify Token :  my_secret_verify_token
  AI Model     :  llama3-8b-8192
════════════════════════════════════════════════════════════
```

---

## Connecting to Meta (One-time Setup)

### Step 1 — Add WhatsApp to your Meta app
- Go to **developers.facebook.com** → your app
- Click **Add Product** → **WhatsApp** → **Set Up**

### Step 2 — Register your webhook
- Go to **WhatsApp → Configuration → Webhook → Edit**
- Paste your ngrok URL: `https://abc123.ngrok-free.app/webhook`
- Enter your `VERIFY_TOKEN`
- Click **Verify and Save** → you should see a green checkmark

### Step 3 — Subscribe to messages
- Click **Manage** next to Webhook fields
- Check the box next to **messages**
- Click **Done**

### Step 4 — Add your phone as test recipient
- Go to **WhatsApp → API Setup**
- Under **"To"** field → **Add phone number**
- Enter your personal WhatsApp number
- Verify the OTP Meta sends you on WhatsApp

### Step 5 — Chat!
- Open WhatsApp on your phone
- Message the Meta test number shown in API Setup
- You will get a Groq AI reply within seconds

---

## Testing Locally (Without WhatsApp)

While your server is running, open a second terminal:

```bash
python test.py
```

This simulates all 6 webhook scenarios:

```
TEST 1 — Health check                → PASS
TEST 2 — Meta webhook verification   → PASS
TEST 3 — Wrong verify token (403)    → PASS
TEST 4 — Incoming text message       → PASS  (hits real Groq API)
TEST 5 — Conversation memory         → PASS
TEST 6 — Reset command               → PASS
```

---

## API Endpoints

| Method | Route              | Description                              |
|--------|--------------------|------------------------------------------|
| GET    | `/`                | Health check — shows server + config status |
| GET    | `/webhook`         | Meta verification handshake              |
| POST   | `/webhook`         | Receives incoming WhatsApp messages      |
| GET    | `/history/{phone}` | Debug — view conversation memory for a number |

---

## Available Groq Models

Change `GROQ_MODEL` in `.env` — no code change needed:

| Model                  | Speed    | Best for                    |
|------------------------|----------|-----------------------------|
| `llama3-8b-8192`       | Fastest  | General chat (default)      |
| `llama3-70b-8192`      | Slower   | Smarter, complex responses  |
| `mixtral-8x7b-32768`   | Fast     | Long conversations          |
| `gemma2-9b-it`         | Fast     | Concise replies             |

---

## Special User Commands

Users can type these in WhatsApp to control the bot:

| Command  | Action                                      |
|----------|---------------------------------------------|
| `reset`  | Clears conversation memory, fresh start     |
| `clear`  | Same as reset                               |
| `/reset` | Same as reset                               |
| `/clear` | Same as reset                               |

---

## Customizing the AI Personality

Edit the `SYSTEM_PROMPT` in `main.py` to change how the bot behaves:

```python
SYSTEM_PROMPT = """You are a customer support agent for Clarity Web.
Help customers with orders, products, and returns.
Keep replies short — this is WhatsApp, not email.
Always respond in the same language the user writes in.
"""
```

---

## Common Errors & Fixes

| Error                                        | Fix                                                         |
|----------------------------------------------|-------------------------------------------------------------|
| `No module named 'requests'`                 | `pip install -r requirements.txt`                           |
| `authentication failed` (ngrok)              | Go to dashboard.ngrok.com/agents → kill active sessions     |
| `1 simultaneous ngrok agent sessions`        | `pkill ngrok` then restart                                  |
| `403 Verification failed`                    | VERIFY_TOKEN in `.env` doesn't match Meta portal            |
| `WA_TOKEN or PHONE_ID not set`               | Fill in `.env` from Meta Developer Portal                   |
| Groq API error                               | Check GROQ_API_KEY is correct at console.groq.com           |
| Meta can't verify webhook                    | Make sure `python run.py` is running before clicking Verify |
| ngrok URL changed after restart              | Re-paste new URL in Meta Portal → WhatsApp → Configuration  |

---

## Limitations (Free Tier)

| Service  | Free Limit                                              |
|----------|---------------------------------------------------------|
| Meta     | Only manually added numbers can receive messages        |
| Meta     | 1,000 free conversations per month                      |
| Groq     | Very generous free tier — effectively unlimited for dev |
| ngrok    | 1 active tunnel, URL changes on every restart           |

---

## Moving to Production

When you're ready to go live and stop using ngrok:

1. Deploy to **Railway** (railway.app) or **Render** (render.com) — both have free tiers
2. You get a permanent `https://` URL — paste it once in Meta portal, never change it
3. The bot runs 24/7 without your laptop being on
4. Replace the in-memory conversation history dict with **Redis** for persistence

```bash
# Deploy to Railway in 3 commands
npm install -g @railway/cli
railway login
railway up
```

---

## Next Steps / Roadmap

- [ ] Connect to your MySQL database for e-commerce queries
- [ ] Add schema-aware SQL generation (Groq reads your DB schema)
- [ ] Two-step table router for 100+ table databases
- [ ] Redis for persistent conversation memory
- [ ] Deploy to Railway for 24/7 uptime
- [ ] Add image/document handling
- [ ] Multi-language support

---

## License

MIT — free to use and modify for personal or commercial projects.# WhatsApp-AI-Chatbot
