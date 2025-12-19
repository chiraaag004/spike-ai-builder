import requests
import time
import json
import random

BASE_URL = "http://localhost:8080/query"

def run_test(name, payload):
    print(f"\n🔹 --- TEST: {name} ---")
    print(f"Query: {payload['query']}")
    try:
        start = time.time()
        response = requests.post(BASE_URL, json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"✅ STATUS: 200 OK ({elapsed:.2f}s)")
            print(f"🤖 AGENT RESPONSE:\n{response.json()['response']}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

# --- TIER 1: ANALYTICS (5 Cases) ---
tier1_tests = [
    {"query": "How many active users in the last 7 days?", "propertyId": "DEMO_MODE"},
    {"query": "What is the bounce rate for mobile users?", "propertyId": "DEMO_MODE"},
    {"query": "Show me sessions breakdown by city.", "propertyId": "DEMO_MODE"},
    {"query": "Compare new users vs returning users.", "propertyId": "DEMO_MODE"},
    {"query": "Which source/medium drove the most traffic?", "propertyId": "DEMO_MODE"},
]

# --- TIER 2: SEO (5 Cases) ---
tier2_tests = [
    {"query": "Show me all pages with 404 errors."},
    {"query": "List pages with titles longer than 60 characters."},
    {"query": "Group pages by Indexability status."},
    {"query": "What percentage of pages are non-indexable?"},
    {"query": "Show me pages with missing H1 tags."},
]

# --- TIER 3: FUSION (5 Cases) ---
tier3_tests = [
    # 1. Basic Merge (Checks if Title exists)
    {"query": "What is the title of the most viewed page?", "propertyId": "TEST"},
    
    # 2. Meta Data Check (Checks if Description exists)
    {"query": "Does the top traffic page have a meta description? If yes, what is it?", "propertyId": "TEST"},
    
    # 3. Technical SEO Check (Checks Status Code/Indexability)
    {"query": "Is the most viewed page indexable and what is its status code?", "propertyId": "TEST"},
    
    # 4. Content Check (Checks H1 tag)
    {"query": "What is the H1 tag of the homepage?", "propertyId": "TEST"},
    
    # 5. Combined Metrics (Views + Tech)
    {"query": "Report the views, active users, and title for the top page.", "propertyId": "TEST"},
]

print("🚀 STARTING FULL EVALUATION SUITE...")

# Run a selection to demonstrate (You can uncomment others)

run_test("Tier 1: Basic Traffic", tier1_tests[random.randint(0, len(tier1_tests)-1)])
run_test("Tier 2: Error Check", tier2_tests[random.randint(0, len(tier2_tests)-1)])
run_test("Tier 2: Grouping Logic", tier2_tests[2])
run_test("Tier 3: Fusion (Views + Titles)", tier3_tests[random.randint(0, len(tier3_tests)-1)])