"""
run.py — Start FastAPI + ngrok tunnel together.
Usage:  python run.py
"""

import os
import time
import threading
import uvicorn
from pyngrok import ngrok, conf
from dotenv import load_dotenv

load_dotenv()

PORT        = 8000
NGROK_TOKEN = os.getenv("NGROK_TOKEN", "")


def start_ngrok():
    time.sleep(2)  # wait for uvicorn to be ready

    if NGROK_TOKEN:
        conf.get_default().auth_token = NGROK_TOKEN

    tunnel     = ngrok.connect(PORT, "http")
    public_url = tunnel.public_url.replace("http://", "https://")

    print("\n" + "═" * 60)
    print("  NGROK TUNNEL IS LIVE")
    print("═" * 60)
    print(f"  Webhook URL  :  {public_url}/webhook")
    print(f"  Verify Token :  {os.getenv('VERIFY_TOKEN', 'my_secret_verify_token')}")
    print(f"  AI Model     :  {os.getenv('GROQ_MODEL', 'llama3-8b-8192')}")
    print("═" * 60)
    print("\n  NEXT STEP — paste the Webhook URL into:")
    print("  Meta Developer Portal → WhatsApp → Configuration → Webhook")
    print("  Enter the same Verify Token shown above\n")


if __name__ == "__main__":
    # Start ngrok in background thread
    thread = threading.Thread(target=start_ngrok, daemon=True)
    thread.start()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info",
    )