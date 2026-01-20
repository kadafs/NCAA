import requests
import json
import os
import csv
import io
import time

BARTTORVIK_JSON_URL = "https://barttorvik.com/2026_team_results.json"
BARTTORVIK_CSV_URL = "https://barttorvik.com/trank.php?year=2026&csv=1"

# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats.json")

def fetch_barttorvik_stats():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://barttorvik.com/"
    }

    print(f"Fetching BartTorvik JSON (Conference) from {BARTTORVIK_JSON_URL}...")
    conf_lookup = {}
    try:
        resp_json = requests.get(BARTTORVIK_JSON_URL, headers=headers, timeout=15)
        if resp_json.status_code == 200:
            raw_json = resp_json.json()
            for team_data in raw_json:
                # 1: Team Name, 2: Conference
                name = team_data[1]
                conf = team_data[2]
                conf_lookup[name] = conf
        else:
            print(f"Failed to fetch JSON: {resp_json.status_code}")
    except Exception as e:
        print(f"Error fetching JSON: {e}")

    print(f"Fetching BartTorvik CSV (Stats) from {BARTTORVIK_CSV_URL}...")
    processed_data = {}
    
    # Use session to handle potential cookie/referrer checks
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # Visit home page first to establish session
        session.get("https://barttorvik.com/", timeout=10)
        time.sleep(1)
        resp_csv = session.get(BARTTORVIK_CSV_URL, timeout=15)
        
        if resp_csv.status_code == 200 and "Verifying browser" not in resp_csv.text and "<!DOCTYPE html>" not in resp_csv.text[:100]:
            print("Successfully fetched CSV data.")
            # CSV Mapping (2026 Verified):
            # 0: Team, 1: AdjOE, 2: AdjDE, 7-14: Four Factors, 15: Adj Tempo
            f = io.StringIO(resp_csv.text)
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 16: continue
                try:
                    name = row[0]
                    processed_data[name] = {
                        "conf": conf_lookup.get(name, "N/A"),
                        "adj_off": float(row[1]),
                        "adj_def": float(row[2]),
                        "adj_t": float(row[15]),
                        "efg": float(row[7]),
                        "efg_d": float(row[8]),
                        "ftr": float(row[9]),
                        "ftr_d": float(row[10]),
                        "to": float(row[11]),
                        "to_d": float(row[12]),
                        "or": float(row[13]),
                        "or_d": float(row[14])
                    }
                except (IndexError, ValueError):
                    continue
        else:
            print(f"CSV fetch blocked or failed (Status: {resp_csv.status_code}). Falling back to JSON source...")
            # If CSV failed, we use the JSON data which is usually unprotected
            resp_json = requests.get(BARTTORVIK_JSON_URL, headers=headers, timeout=15)
            if resp_json.status_code == 200:
                raw_json = resp_json.json()
                for team_data in raw_json:
                    # Index 1: Name, 2: Conf, 4: AdjOE, 6: AdjDE, 44: Adj Tempo
                    try:
                        name = team_data[1]
                        processed_data[name] = {
                            "conf": team_data[2],
                            "adj_off": float(team_data[4]),
                            "adj_def": float(team_data[6]),
                            "adj_t": float(team_data[44]),
                            # Default Four Factors (approx D1 averages) since they aren't in this JSON
                            "efg": 50.0, "efg_d": 50.0, "ftr": 30.0, "ftr_d": 30.0, 
                            "to": 18.0, "to_d": 18.0, "or": 28.0, "or_d": 28.0
                        }
                    except (IndexError, ValueError, TypeError):
                        continue
                print(f"Extracted {len(processed_data)} teams from JSON metadata.")

    except Exception as e:
        print(f"Error fetching CSV stats: {e}")

    if processed_data:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)
        print(f"Successfully saved {len(processed_data)} teams to {OUTPUT_FILE}")
        return True
    
    return False

if __name__ == "__main__":
    fetch_barttorvik_stats()
