import datetime
from ncaa.v1_2.populate import fetch_matchups

def test_fetch():
    target_date = datetime.datetime(2026, 2, 5)
    print(f"Testing fetch for {target_date.strftime('%Y-%m-%d')}...")
    
    for i in range(5):
        games = fetch_matchups(target_date)
        print(f" Attempt {i+1}: Found {len(games)} games")

if __name__ == "__main__":
    test_fetch()
