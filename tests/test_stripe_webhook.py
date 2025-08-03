import os
import json
import hmac
import hashlib
import base64
from flask import Flask
import requests

# CONFIGURATION
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000/webhook")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

# Simulate a Stripe webhook payload for checkout.session.completed
MOCK_EVENT = {
    "id": "evt_test_webhook",
    "object": "event",
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_webhook",
            "object": "checkout.session",
            "metadata": {
                "order_id": "test-order-123"
            },
            "amount_total": 1000,
            "currency": "usd"
        }
    }
}

def generate_stripe_signature(payload, secret):
    # Stripe signs payloads with a timestamp and the secret
    timestamp = "1234567890"
    signed_payload = f"{timestamp}.{payload}".encode()
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"

def test_webhook():
    payload = json.dumps(MOCK_EVENT)
    signature = generate_stripe_signature(payload, STRIPE_WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": signature
    }
    print(f"[TEST] Sending simulated Stripe webhook to {WEBHOOK_URL}")
    response = requests.post(WEBHOOK_URL, data=payload, headers=headers)
    print(f"[TEST] Response status: {response.status_code}")
    print(f"[TEST] Response body: {response.text}")
    assert response.status_code == 200, "Webhook did not return 200 OK"
    assert 'success' in response.text, "Webhook handler did not return expected success message"

if __name__ == "__main__":
    test_webhook()
