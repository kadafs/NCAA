import requests
from bs4 import BeautifulSoup
import json
import os

INJURY_URL = "https://www.actionnetwork.com/nba/injury-report"
OUTPUT_FILE = "data/nba_injury_notes.json"

def fetch_nba_injuries():
    print(f"Fetching NBA injuries from {INJURY_URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(INJURY_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch injuries: {response.status_code}")
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        injury_data = {}
        
        # Find all team tables
        # Correct class based on research: table-layout__table injuries-table-layout
        tables = soup.find_all('table', class_='injuries-table-layout')
        
        for table in tables:
            rows = table.find_all('tr')
            current_team = None
            
            for row in rows:
                # Check for team header row
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
        print(f"Error fetching NBA injuries: {e}")
        return False

if __name__ == "__main__":
    fetch_nba_injuries()
