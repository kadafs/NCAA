import requests

# Test if D2 odds are available
url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"

print("Testing NCAA Odds API for D2 support...")
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=15)
    if response.status_code == 200:
        data = response.json()
        print(f"Total games with odds: {len(data)}")
        
        # Check if any D2 games
        d2_count = 0
        sample_d2 = None
        
        for key, game_data in data.items():
            # D2 teams often have specific naming patterns
            # Let's check a few known D2 teams from today's games
            if any(team in key.lower() for team in ['livingstone', 'fayetteville', 'rockhurst', 'southwest baptist']):
                d2_count += 1
                if not sample_d2:
                    sample_d2 = (key, game_data)
        
        print(f"\nPotential D2 games found: {d2_count}")
        
        if sample_d2:
            print(f"\nSample D2 game:")
            print(f"  Key: {sample_d2[0]}")
            print(f"  Data: {sample_d2[1]}")
        else:
            print("\nNo D2 games found in odds data.")
            print("\nSample of available games (first 5):")
            for i, (key, val) in enumerate(list(data.items())[:5]):
                print(f"  {key}: {val}")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Exception: {e}")
