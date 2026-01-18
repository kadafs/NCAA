import requests
from bs4 import BeautifulSoup
import json
import os

INJURY_URL = "https://www.actionnetwork.com/ncaab/injury-report"
OUTPUT_FILE = "data/injury_notes.json"

def fetch_injuries():
    print(f"Fetching injuries from {INJURY_URL}...")
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

        # The table is structured with team headers and player rows
        # Based on DOM research: 
        # Team header: <tr class="injuries-table-layout__team-header-row">
        # Player rows follow it.
        
        current_team = None
        rows = soup.find_all('tr')
        
        for row in rows:
            # Check for team header
            if 'injuries-table-layout__team-header-row' in row.get('class', []):
                team_cell = row.find('td')
                if team_cell:
                    current_team = team_cell.get_text(strip=True)
                    injury_data[current_team] = []
            elif current_team:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    # Columns: 0:Name, 1:Pos, 2:Status, 3:Injury, 4:Update, 5:Updated
                    player = cols[0].get_text(strip=True)
                    status = cols[2].get_text(strip=True)
                    note = cols[4].get_text(strip=True)
                    
                    injury_data[current_team].append({
                        "player": player,
                        "status": status,
                        "note": note
                    })

        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(injury_data, f, indent=2)

        print(f"Successfully saved injury data for {len(injury_data)} teams to {OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"Error fetching injuries: {e}")
        return False

if __name__ == "__main__":
    fetch_injuries()
