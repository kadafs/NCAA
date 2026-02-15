import requests
import json
import os
import csv
import io
import time
import sys
from datetime import datetime

# Path injection for root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Conference-only URLs
BARTTORVIK_JSON_URL = "https://barttorvik.com/2026_team_results.json"
BARTTORVIK_CSV_CONF_URL = "https://barttorvik.com/trank.php?year=2026&csv=1&conflimit=1"

# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats_conf.json")
RAW_INPUT_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_raw_conf.json")

def fetch_barttorvik_conf_stats():
    """
    Fetch conference-only stats from Barttorvik.
    Uses &conflimit=1 parameter to get stats from conference games only.
    """
    processed_data = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://barttorvik.com/"
    }

    print(f"Fetching centralized BartTorvik CONFERENCE-ONLY stats from https://ncaa-api-w2ry.onrender.com/stats/barttorvik/conf")
    try:
        from utils.ssl_adapter import get_robust_session
        session = get_robust_session(retries=2)

        render_resp = session.get("https://ncaa-api-w2ry.onrender.com/stats/barttorvik/conf", timeout=30)
        
        # SSL Fallback logic
        if render_resp.status_code != 200:
            print(f"Centralized fetch returned {render_resp.status_code}. Retrying with SSL bypass...")
            render_resp = session.get("https://ncaa-api-w2ry.onrender.com/stats/barttorvik/conf", timeout=30, verify=False)

        if render_resp.status_code == 200:
            processed_data = render_resp.json()
            if processed_data and len(processed_data) > 300:
                # Validate that it's NOT just serving defaults
                sample_teams = list(processed_data.values())[:5]
                is_default = any(t.get('efg') == 50.0 and t.get('to') == 18.0 for t in sample_teams)
                
                if is_default:
                    print("Centralized API is serving default metrics. Ignoring and scraping fresh...")
                else:
                    print(f"Successfully fetched {len(processed_data)} teams from centralized Render API (Conference-Only).")
                    with open(OUTPUT_FILE, "w") as f:
                        json.dump(processed_data, f, indent=2)
                    
                    # Update RAW_INPUT_FILE as well
                    print(f"Updating high-quality fallback {RAW_INPUT_FILE}...")
                    raw_to_save = []
                    for name, d in processed_data.items():
                        raw_to_save.append([
                            name, d['adj_off'], d['adj_def'], 0, 0, 0, 0, 
                            d['efg'], d.get('efg_d', 50.0), d['ftr'], d.get('ftr_d', 30.0), 
                            d['to'], d.get('to_d', 18.0), d['or'], d.get('or_d', 28.0), d['adj_t']
                        ])
                    with open(RAW_INPUT_FILE, "w") as f_raw:
                        json.dump(raw_to_save, f_raw, indent=2)
                    
                    return True
            else:
                print(f"Centralized API returned empty dataset. Falling back...")
        else:
            print(f"Centralized API failed with status {render_resp.status_code}. Falling back...")
    except Exception as e:
        print(f"Centralized API fetch failed ({e}). Falling back to manual scraping...")

    # --- LEGACY SCRAPING FALLBACK ---
    print(f"Fetching BartTorvik JSON (Conference lookup) from {BARTTORVIK_JSON_URL}")
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

    try:
        from utils.ssl_adapter import get_robust_session
        session = get_robust_session(retries=3)
        session.headers.update(headers)
        
        print(f"Attempting robust CSV fetch (CONFERENCE-ONLY) from {BARTTORVIK_CSV_CONF_URL}")
        resp_csv = session.get(BARTTORVIK_CSV_CONF_URL, timeout=20)
        
        if resp_csv.status_code == 200 and "Verifying browser" not in resp_csv.text and "<!DOCTYPE html>" not in resp_csv.text[:100]:
            print("Successfully fetched CONFERENCE-ONLY CSV data.")
            # CSV Mapping (2026 Verified):
            # 0: Team, 1: AdjOE, 2: AdjDE, 7-14: Four Factors, 15: Adj Tempo
            f = io.StringIO(resp_csv.text)
            reader = csv.reader(f)
            raw_to_save = []
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
                    raw_to_save.append(row)
                except (IndexError, ValueError):
                    continue
            
            # Auto-update high-quality fallback
            if processed_data:
                print(f"Updating high-quality fallback {RAW_INPUT_FILE}...")
                with open(RAW_INPUT_FILE, "w") as f_raw:
                    json.dump(raw_to_save, f_raw, indent=2)
        else:
            print(f"CSV fetch blocked or failed (Status: {resp_csv.status_code}). Trying Fallback sources...")
            
            # High-Quality Fallback: Check for BARTTORVIK_RAW_CONF.json
            if os.path.exists(RAW_INPUT_FILE):
                mtime = os.path.getmtime(RAW_INPUT_FILE)
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"Loading high-quality metrics from {RAW_INPUT_FILE} (Cached: {mtime_str})...")
                try:
                    with open(RAW_INPUT_FILE, "r") as f_raw:
                        raw_json = json.load(f_raw)
                        for team_data in raw_json:
                            try:
                                name = team_data[0]
                                processed_data[name] = {
                                    "conf": conf_lookup.get(name, "N/A"),
                                    "adj_off": float(team_data[1]),
                                    "adj_def": float(team_data[2]),
                                    "adj_t": float(team_data[15]),
                                    "efg": float(team_data[7]),
                                    "efg_d": float(team_data[8]),
                                    "ftr": float(team_data[9]),
                                    "ftr_d": float(team_data[10]),
                                    "to": float(team_data[11]),
                                    "to_d": float(team_data[12]),
                                    "or": float(team_data[13]),
                                    "or_d": float(team_data[14])
                                }
                            except (IndexError, ValueError, TypeError):
                                continue
                        print(f"Parsed {len(processed_data)} teams from high-quality raw fallback.")
                except Exception as e:
                    print(f"Error reading {RAW_INPUT_FILE}: {e}")

    except Exception as e:
        print(f"Error fetching CSV stats: {e}")

    if processed_data:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)
        print(f"Successfully saved {len(processed_data)} teams to {OUTPUT_FILE}")
        print(f"\n[OK] Conference-only stats fetched successfully!")
        print(f"  Data source: Barttorvik (conflimit=1)")
        print(f"  Output: {OUTPUT_FILE}")
        return True
    
    return False

if __name__ == "__main__":
    fetch_barttorvik_conf_stats()
