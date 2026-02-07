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

BARTTORVIK_JSON_URL = "https://barttorvik.com/2026_team_results.json"
BARTTORVIK_CSV_URL = "https://barttorvik.com/trank.php?year=2026&csv=1"

# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats.json")
RAW_INPUT_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_raw.json") # High-quality browser-fetched backup

def fetch_barttorvik_stats():
    processed_data = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://barttorvik.com/"
    }

    print(f"Fetching centralized BartTorvik stats from https://ncaa-api-w2ry.onrender.com/stats/barttorvik")
    try:
        from utils.ssl_adapter import get_robust_session
        session = get_robust_session(retries=2)

        render_resp = session.get("https://ncaa-api-w2ry.onrender.com/stats/barttorvik", timeout=30)
        
        # SSL Fallback logic
        if render_resp.status_code != 200:
            print(f"Centralized fetch returned {render_resp.status_code}. Retrying with SSL bypass...")
            render_resp = session.get("https://ncaa-api-w2ry.onrender.com/stats/barttorvik", timeout=30, verify=False)

        if render_resp.status_code == 200:
            processed_data = render_resp.json()
            if processed_data and len(processed_data) > 300:
                # Validate that it's NOT just serving defaults (checking first few teams)
                sample_teams = list(processed_data.values())[:5]
                is_default = any(t.get('efg') == 50.0 and t.get('to') == 18.0 for t in sample_teams)
                
                if is_default:
                    print("Centralized API is serving default metrics. Ignoring and scraping fresh...")
                else:
                    print(f"Successfully fetched {len(processed_data)} teams from centralized Render API.")
                    with open(OUTPUT_FILE, "w") as f:
                        json.dump(processed_data, f, indent=2)
                    
                    # Update RAW_INPUT_FILE as well to keep the fallback fresh for GitHub
                    print(f"Updating high-quality fallback {RAW_INPUT_FILE}...")
                    raw_to_save = []
                    for name, d in processed_data.items():
                        # Reconstruct the expected format or just dump the dict
                        # The RAW_INPUT_FILE is expected to be a list of lists by the loader
                        # index 0: Name, 1: AdjOE, 2: AdjDE, 7: eFG, 8: eFG_D, 9: FTR, 10: FTR_D, 11: TO, 12: TO_D, 13: OR, 14: OR_D, 15: AdjT
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
            try:
                print(f"Error Details: {render_resp.text[:200]}")
            except: pass
    except Exception as e:
        print(f"Centralized API fetch failed ({e}). Falling back to manual scraping...")

    # --- LEGACY SCRAPING FALLBACK ---
    print(f"Fetching BartTorvik JSON (Conference) from {BARTTORVIK_JSON_URL}")
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
        
        print(f"Attempting robust CSV fetch from {BARTTORVIK_CSV_URL}")
        resp_csv = session.get(BARTTORVIK_CSV_URL, timeout=20)
        
        if resp_csv.status_code == 200 and "Verifying browser" not in resp_csv.text and "<!DOCTYPE html>" not in resp_csv.text[:100]:
            print("Successfully fetched CSV data.")
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
            
            # High-Quality Fallback: Check for BARTTORVIK_RAW.json (browser-fetched full data)
            if os.path.exists(RAW_INPUT_FILE):
                mtime = os.path.getmtime(RAW_INPUT_FILE)
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"Loading high-quality metrics from {RAW_INPUT_FILE} (Cached: {mtime_str})...")
                try:
                    with open(RAW_INPUT_FILE, "r") as f_raw:
                        raw_json = json.load(f_raw)
                        for team_data in raw_json:
                            # Index mapping for json=1 (Verified 2026):
                            # 0: Team, 1: AdjOE, 2: AdjDE, 7: eFG, 8: eFG_D, 9: FTR, 10: FTR_D, 
                            # 11: TO, 12: TO_D, 13: OR, 14: OR_D, 15: AdjT
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

            # Basic Fallback: Use 2026_team_results.json (accessible but no four factors)
            if not processed_data:
                print("No high-quality raw data found. Falling back to basic results JSON...")
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
                                # Optimized indices from raw JSON inspection (2026 Season):
                                # Index 10: OR%, Index 12: TO%
                                "efg": 50.0, # eFG still not confirmed in results.json
                                "efg_d": 50.0, 
                                "ftr": 30.0, 
                                "ftr_d": 30.0, 
                                "to": float(team_data[12]) if len(team_data) > 12 else 18.0,
                                "to_d": 18.0,
                                "or": float(team_data[10]) if len(team_data) > 10 else 28.0,
                                "or_d": 28.0
                            }
                        except (IndexError, ValueError, TypeError):
                            continue
                    print(f"Extracted {len(processed_data)} teams from basic JSON metadata.")

    except Exception as e:
        print(f"Error fetching CSV stats: {e}")

    if processed_data:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)
        print(f"Successfully saved {len(processed_data)} teams to {OUTPUT_FILE}")
        
        # Suggest syncing to cloud if running locally and fresh data was found
        if not os.getenv("GITHUB_ACTIONS"):
            print("\n[TIP] Running locally? Use 'python ncaa/sync_stats.py' to push these fresh metrics to your cloud backend.")
        
        return True
    
    return False

if __name__ == "__main__":
    fetch_barttorvik_stats()
