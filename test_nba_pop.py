import json
from nba.v1_2.populate import get_nba_daily_input_sheet
from datetime import datetime

def test_nba():
    print(f"Testing NBA population for {datetime.now().strftime('%Y-%m-%d')}...")
    try:
        sheet = get_nba_daily_input_sheet()
        print(f"Games found: {len(sheet)}")
        if sheet:
            for g in sheet:
                print(f"Matchup: {g['team']} @ {g['opponent']}")
        else:
            print("No games found in the daily sheet.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nba()
