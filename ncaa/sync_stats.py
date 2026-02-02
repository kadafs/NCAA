import requests
import json
import os
import sys

# Centralized Render API URL
BACKEND_URL = "https://ncaa-api-w2ry.onrender.com/stats/barttorvik"

# Path to local high-quality stats
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_STATS_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'barttorvik_stats.json'))

def sync_stats():
    """
    Pushes local BartTorvik stats to the Render backend cache.
    This serves as a Manual Plan B if automated scraping is blocked.
    """
    if not os.path.exists(LOCAL_STATS_FILE):
        print(f"Error: Local stats file not found at {LOCAL_STATS_FILE}")
        return

    print(f"Reading local stats from {LOCAL_STATS_FILE}...")
    with open(LOCAL_STATS_FILE, 'r') as f:
        stats_data = json.load(f)

    print(f"Pushing {len(stats_data)} teams to Render backend...")
    try:
        # Use verify=False if hitting SSL issues locally
        resp = requests.post(BACKEND_URL, json=stats_data, timeout=30)
        
        if resp.status_code == 200:
            print(f"Successfully synchronized {len(stats_data)} teams to Render!")
        else:
            print(f"Sync failed with status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Error during synchronization: {e}")

if __name__ == "__main__":
    sync_stats()
