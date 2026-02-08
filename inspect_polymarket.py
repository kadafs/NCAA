import requests
import json
from datetime import datetime

GAMMA_API_URL = "https://gamma-api.polymarket.com/events"

def inspect_markets(slug="nba"):
    print(f"--- Inspecting Polymarket for slug: {slug} ---")
    
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "closed": "false",
        "tag_slug": slug,
        "limit": 50,
        "offset": 0,
        "order": "volume24hr", # standard gamma sort
        "ascending": "false"
    }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        events = []
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            events = data.get('data', []) # Structure might vary
            
        print(f"Fetched {len(events)} events for slug '{slug}'.")
        
        for i, event in enumerate(events[:5]): 
            print(f"\nEvent {i+1}: {event.get('title')}")
            print(f"ID: {event.get('id')}")
            print(f"Tags: {event.get('tags')}")
            
            markets = event.get('markets', [])
            print(f"Markets ({len(markets)}):")
            # Look for Game Winner markets
            for m in markets[:3]:
                 print(f"  - {m.get('question')} | Prices: {m.get('outcomePrices')}")

    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    inspect_markets("nba") 
    inspect_markets("cbb") # College Basketball default slug often
