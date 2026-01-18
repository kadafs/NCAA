from nba_api.stats.endpoints import leaguedashteamstats
import json

def test():
    try:
        print("Testing basic fetch...")
        res = leaguedashteamstats.LeagueDashTeamStats(season='2024-25').get_dict()
        print(f"Success! Found {len(res['resultSets'][0]['rowSet'])} teams.")
        print("Sample Row Keys:", res['resultSets'][0]['headers'])
        print("Sample Row 1:", res['resultSets'][0]['rowSet'][0])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
