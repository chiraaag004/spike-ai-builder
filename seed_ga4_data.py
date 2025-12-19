import requests
import json
import time
import random

# CONFIGURATION
MEASUREMENT_ID = "G-ELZ0TTB5LE"  # From Data Stream
API_SECRET = "70Bkdq-3R9K-f9HobOCEpA"          # From Measurement Protocol API Secrets
# The endpoint for sending events
URL = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"

def send_backdated_event(client_id, event_name, params, timestamp_micros):
    payload = {
        "client_id": client_id,
        "timestamp_micros": timestamp_micros, # This creates the "Backdated" effect
        "non_personalized_ads": False,
        "events": [
            {
                "name": event_name,
                "params": params
            }
        ]
    }
    
    # Send the POST request
    response = requests.post(URL, json=payload)
    if response.status_code == 204:
        print(f"✅ Sent {event_name} for user {client_id}")
    else:
        print(f"❌ Failed: {response.status_code} {response.text}")

# --- SIMULATION ---
# Let's backdate data to 7 days ago
days_ago = 7
seconds_ago = days_ago * 24 * 60 * 60
# GA4 expects microseconds (millionths of a second)
past_timestamp = int((time.time() - seconds_ago) * 1_000_000)

# Simulate 5 users visiting specific pages
pages = ["/home", "/pricing", "/blog/seo-tips", "/contact"]

for i in range(5):
    user_id = f"user_{random.randint(1000, 9999)}"
    page = random.choice(pages)
    
    send_backdated_event(
        client_id=user_id,
        event_name="page_view",
        params={
            "page_location": f"https://example.com{page}",
            "page_title": f"Page {page}",
            "session_id": "100" # Required to show up in "Traffic Acquisition"
        },
        timestamp_micros=past_timestamp
    )