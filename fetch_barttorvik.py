import requests
import json
import os

BARTTORVIK_JSON_URL = "https://barttorvik.com/2026_team_results.json"
OUTPUT_FILE = "data/barttorvik_stats.json"

def fetch_barttorvik_stats():
    print(f"Fetching BartTorvik stats from {BARTTORVIK_JSON_URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(BARTTORVIK_JSON_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            raw_data = response.json()
            processed_data = {}
            
            for team_data in raw_data:
                # Based on research:
                # Index 1: Team Name
                # Index 4: AdjOE
                # Index 6: AdjDE
                # Index 44: Adj Tempo
                try:
                    name = team_data[1]
                    processed_data[name] = {
                        "adj_off": float(team_data[4]),
                        "adj_def": float(team_data[6]),
                        "adj_t": float(team_data[44])
                    }
                except (IndexError, ValueError) as e:
                    continue
            
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, "w") as f:
                json.dump(processed_data, f, indent=2)
            
            print(f"Successfully saved {len(processed_data)} teams to {OUTPUT_FILE}")
            return True
        else:
            print(f"Failed to fetch BartTorvik stats: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error fetching BartTorvik stats: {e}")
    return False

if __name__ == "__main__":
    fetch_barttorvik_stats()
