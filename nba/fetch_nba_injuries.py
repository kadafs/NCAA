import sys
import os
import json
from bs4 import BeautifulSoup

# Add project root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from utils.ssl_adapter import get_robust_session
import time
import random

INJURY_URL = "https://www.actionnetwork.com/nba/injury-report"
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "nba_injury_notes.json")

def fetch_nba_injuries():
    print(f"Fetching NBA injuries from {INJURY_URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    session = get_robust_session(retries=3)
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            response = session.get(INJURY_URL, headers=headers, timeout=20)
            
            # 202 Accepted handling
            if response.status_code == 202:
                print(f"Attempt {attempt+1}: Received 202 (Processing). Retrying in 5s...")
                time.sleep(5 + random.uniform(1, 3))
                continue
                
            if response.status_code != 200:
                print(f"Failed to fetch injuries: {response.status_code}")
                return False

            soup = BeautifulSoup(response.text, 'html.parser')
            injury_data = {}
            
            # Find all team tables
            tables = soup.find_all('table', class_='injuries-table-layout')
            
            for table in tables:
                rows = table.find_all('tr')
                current_team = None
                
                for row in rows:
                    if 'injuries-table-layout__team-header-row' in row.get('class', []):
                        team_cell = row.find('td')
                        if team_cell:
                            current_team = team_cell.get_text(strip=True)
                            if current_team not in injury_data:
                                injury_data[current_team] = []
                    elif current_team:
                        cols = row.find_all('td')
                        if len(cols) >= 5:
                            player = cols[0].get_text(strip=True)
                            status = cols[2].get_text(strip=True)
                            note = cols[4].get_text(strip=True)
                            
                            injury_data[current_team].append({
                                "player": player,
                                "status": status,
                                "note": note
                            })

            with open(OUTPUT_FILE, "w") as f:
                json.dump(injury_data, f, indent=2)

            print(f"Successfully saved NBA injury data for {len(injury_data)} teams to {OUTPUT_FILE}")
            return True

        except Exception as e:
            print(f"Attempt {attempt+1} Exception: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
            else:
                return False
    return False

if __name__ == "__main__":
    fetch_nba_injuries()
