from supabase import create_client
import json

def check():
    url = "https://anmwjtibdzavxcfjqipv.supabase.co"
    key = "sb_publishable_T9Sr_qS8lPZ3wDoKjicOFA_m3nAQxNR" # Using the anon key from .env
    
    s = create_client(url, key)
    
    for mode in ["ncaa_safe", "ncaa_full", "nba_safe", "nba_full"]:
        print(f"\n--- {mode} ---")
        try:
            res = s.table("predictions_store").select("data").eq("league", mode).execute()
            if res.data:
                game = res.data[0]['data']['games'][0]
                print(f"Matchup: {game['matchup']}")
                print(f"Model Total: {game['model_total']}")
                print(f"Trace Length: {len(game['trace'])}")
                print("Trace Content:")
                for line in game['trace']:
                    print(f"  {line}")
            else:
                print("NOT FOUND")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    check()
