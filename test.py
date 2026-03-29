"""
test.py — Test Groq AI + webhook locally.
Run server first: uvicorn main:app --reload
Then:            python test.py
"""

import requests
import json

BASE         = "http://localhost:8000"
VERIFY_TOKEN = "my_secret_verify_token"
TEST_PHONE   = "919876543210"


def sep(title):
    print(f"\n{'─' * 55}\n  {title}\n{'─' * 55}")


def fake_message(text: str, phone: str = TEST_PHONE) -> dict:
    """Build a payload exactly like Meta sends."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "ENTRY_123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": phone,
                        "phone_number_id": "PHONE_ID_123"
                    },
                    "messages": [{
                        "from":      phone,
                        "id":        "wamid.TEST001",
                        "timestamp": "1700000000",
                        "type":      "text",
                        "text":      {"body": text}
                    }]
                },
                "field": "messages"
            }]
        }]
    }


# ── Test 1: Health ────────────────────────────────────────────────────────
sep("TEST 1 — Health check")
r = requests.get(f"{BASE}/")
print(json.dumps(r.json(), indent=2))


# ── Test 2: Webhook verification ─────────────────────────────────────────
sep("TEST 2 — Meta webhook verification")
r = requests.get(f"{BASE}/webhook", params={
    "hub.mode":         "subscribe",
    "hub.verify_token": VERIFY_TOKEN,
    "hub.challenge":    "CHALLENGE_999",
})
print("Status   :", r.status_code)
print("Challenge:", r.text)
print("Result   :", "PASS" if r.text == "CHALLENGE_999" else "FAIL")


# ── Test 3: Simple greeting ───────────────────────────────────────────────
sep("TEST 3 — Simple chat message (hits Groq API)")
r = requests.post(f"{BASE}/webhook", json=fake_message("Hello! Who are you?"))
print("Status:", r.status_code, "→", r.json())
print("(Check server terminal for Groq's reply)")


# ── Test 4: Follow-up to test memory ─────────────────────────────────────
sep("TEST 4 — Follow-up message (tests conversation memory)")
r = requests.post(f"{BASE}/webhook", json=fake_message("What did I just ask you?"))
print("Status:", r.status_code, "→", r.json())


# ── Test 5: View conversation history ────────────────────────────────────
sep("TEST 5 — View conversation history")
r = requests.get(f"{BASE}/history/{TEST_PHONE}")
data = r.json()
print(f"Messages remembered: {data['count']}")
for msg in data["messages"]:
    role = msg["role"].upper().ljust(10)
    print(f"  {role}: {msg['content'][:80]}...")


# ── Test 6: Reset command ─────────────────────────────────────────────────
sep("TEST 6 — Reset conversation")
r = requests.post(f"{BASE}/webhook", json=fake_message("reset"))
print("Status:", r.status_code)

r = requests.get(f"{BASE}/history/{TEST_PHONE}")
print("History after reset:", r.json()["count"], "messages (expected 0)")


print(f"\n{'═' * 55}")
print("  Done. Check server terminal for full Groq responses.")
print('═' * 55)