from core.universal_bridge import get_universal_predictions
import json

def test_dual():
    for league in ["nba", "ncaa"]:
        print(f"\n=== Testing {league.upper()} ===")
        
        # Test Safe Mode (Legacy)
        safe_data = get_universal_predictions(league, mode="safe")
        safe_games = safe_data.get("games", [])
        
        # Test Full Mode (Sharp)
        full_data = get_universal_predictions(league, mode="full")
        full_games = full_data.get("games", [])
        
        if not safe_games or not full_games:
            print(f"Skipping {league} - no games found.")
            continue
            
        for i in range(min(5, len(safe_games))):
            s_game = safe_games[i]
            f_game = full_games[i]
            
            delta = round(f_game['model_total'] - s_game['model_total'], 2)
            print(f"\nMatchup: {s_game['matchup']}")
            print(f"  SAFE: {s_game['model_total']} | FULL: {f_game['model_total']} | Delta: {delta}")
            
            if i == 0:
                print("  FULL Trace (Complete):")
                for line in f_game['trace']:
                    print(f"    {line}")

if __name__ == "__main__":
    test_dual()
