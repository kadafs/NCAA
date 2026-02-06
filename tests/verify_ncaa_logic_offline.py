import os
import sys
import json
from datetime import datetime

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.universal_bridge import get_universal_predictions
from unittest.mock import patch

def test_ncaa_logic_offline():
    print("Testing NCAA Props Logic (OFFLINE)...")
    
    # Mock data for daily sheet
    mock_daily_sheet = [
        {
            "team": "Ohio St.",
            "opponent": "Maryland",
            "away_seo": "ohio-st",
            "home_seo": "maryland",
            "market_total": 142.5
        }
    ]
    
    # Mock ncaa.v1_2.populate.get_daily_input_sheet
    with patch('ncaa.v1_2.populate.get_daily_input_sheet', return_value=mock_daily_sheet):
        # We also need to mock the odds fetch if it's called
        with patch('requests.get') as mock_get:
            # Mock odds response
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"games": []}
            
            results = get_universal_predictions(league="ncaa", mode="safe")
            
            # Debugging info
            print(f"Total processed games: {len(results.get('games', []))}")
            if results.get('games'):
                game = results['games'][0]
                print(f"DEBUG: Matchup: {game['away']} @ {game['home']}")
                
                # Check for props
                if "props" in game and len(game["props"]) > 0:
                    print(f"SUCCESS: Found {len(game['props'])} props")
                    for p in game["props"][:3]:
                        print(f" [PROP] {p['name']}: {p['pts']} PTS")
                else:
                    print("FAIL: No props found.")
                    # Try to see why
                    from core.data_bridge import UniversalDataBridge
                    bridge = UniversalDataBridge("ncaa")
                    # Manual stat load for debug
                    pts_data = bridge._load_json("individual/pts_pg.json")
                    if pts_data:
                        teams = sorted(list(set(i['Team'] for i in pts_data)))
                        print(f"DEBUG: Found {len(teams)} teams in pts_pg.json")
                        print(f"DEBUG: Sample teams: {teams[:5]}")
                        if "Ohio St." in teams:
                            print("DEBUG: 'Ohio St.' IS in stats file.")
                        else:
                            print("DEBUG: 'Ohio St.' is NOT in stats file.")
            else:
                print("FAIL: No games processed")

if __name__ == "__main__":
    test_ncaa_logic_offline()
