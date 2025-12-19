import requests
import json
import os
from dotenv import load_dotenv

# Load env to get your test Property ID
load_dotenv()
PROPERTY_ID = os.getenv("PROPERTY_ID", "123456789") 
URL = "http://localhost:8080/query"

def send_query(name, payload):
    print(f"\n🔹 --- TEST: {name} ---")
    print(f"Query: {payload['query']}")
    try:
        # Timeout set to 60s because LLMs can be slow
        response = requests.post(URL, json=payload, timeout=120) 
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ STATUS: 200 OK")
            print(f"🤖 AGENT RESPONSE:\n{data['response']}")
        else:
            print(f"❌ ERROR {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {str(e)}")

if __name__ == "__main__":
    send_query("Tier 1 - Analytics (GA4)", {
        "propertyId": PROPERTY_ID,
        "query": "How many active users and sessions did we have in the last 7 days?"
    })

    send_query("Tier 2 - SEO (Internal Tab)", {
        "query": "Calculate the percentage of indexable pages on the site. Based on this number, assess whether the site’s technical SEO health is good, average, or poor."
    })

    send_query("Tier 3 - SEO (Response Codes Tab)", {
        "query": "How many URLs are returning 200 codes?"
    })

    send_query("Fusion (GA4 + SEO)", {
        "propertyId": "TEST",
        "query": "What are the top 5 pages by views and what are their title tags?"
    })