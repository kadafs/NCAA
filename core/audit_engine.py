# Result Scraper & Grading Engine v1.0
import requests
import os
import json
from datetime import datetime, timedelta
import zoneinfo
from supabase import create_client, Client
from dotenv import load_dotenv
from nba_api.stats.endpoints import scoreboardv3

# Root path for utils mapping
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import NBA_TRICODES

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def grade_total(market_total, away_score, home_score):
    actual_total = away_score + home_score
    if actual_total > market_total:
        return "OVER"
    elif actual_total < market_total:
        return "UNDER"
    else:
        return "PUSH"

def audit_nba(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    print(f"Auditing NBA for {date_str}...")

    # 1. Fetch scores from NBA API
    try:
        sb = scoreboardv3.ScoreboardV3(game_date=date_str, timeout=30)
        data = sb.get_dict()
        games = data.get('scoreboard', {}).get('games', [])
        
        results_map = {}
        for g in games:
            if g.get('gameStatus') == 3: # 3 = Final
                away = g['awayTeam']
                home = g['homeTeam']
                
                # Use tricode to get full name which matches our database
                away_full = NBA_TRICODES.get(away['teamTricode'], away['teamName']).lower()
                home_full = NBA_TRICODES.get(home['teamTricode'], home['teamName']).lower()
                
                # Normalize for matching
                norm_away = away_full.replace(" ", "").replace(".", "").replace("-", "")
                norm_home = home_full.replace(" ", "").replace(".", "").replace("-", "")
                
                results_map[f"{norm_away}_{norm_home}"] = {
                    "away_score": away['score'],
                    "home_score": home['score'],
                    "total": away['score'] + home['score']
                }
        
        if not results_map:
            print(f"No completed NBA games found in API for {date_str}.")
            return

        # 2. Fetch 'pending' rows for this date from history
        pending = supabase.table("predictions_history") \
            .select("*") \
            .eq("league", "nba") \
            .eq("game_date", date_str) \
            .eq("status", "pending") \
            .execute()

        if not pending.data:
            print(f"No pending NBA predictions found in database for {date_str}.")
            return

        print(f"Found {len(pending.data)} pending NBA games. Checking against results...")
        updates = []
        for row in pending.data:
            # Matchup format in DB: "Lakers @ Celtics" or "Los Angeles Lakers @ Boston Celtics"
            parts = [p.strip().lower() for p in row['matchup'].split('@')]
            if len(parts) != 2: continue
            
            # Normalize DB names same way for lookup
            norm_db_away = parts[0].replace(" ", "").replace(".", "").replace("-", "")
            norm_db_home = parts[1].replace(" ", "").replace(".", "").replace("-", "")
            key = f"{norm_db_away}_{norm_db_home}"
            
            if key in results_map:
                res = results_map[key]
                actual_total = res['total']
                market_total = row['market_total']
                model_total = row['model_total']
                
                # Determine intended direction (model vs market)
                direction = "OVER" if model_total > market_total else "UNDER"
                actual_direction = grade_total(market_total, res['away_score'], res['home_score'])
                
                is_win = False
                if actual_direction == "PUSH":
                    is_win = None
                else:
                    is_win = direction == actual_direction

                updates.append({
                    "id": row['id'],
                    "league": row['league'],
                    "game_date": row['game_date'],
                    "matchup": row['matchup'],
                    "actual_score_away": res['away_score'],
                    "actual_score_home": res['home_score'],
                    "actual_total": actual_total,
                    "is_win": is_win,
                    "status": "graded",
                    "profit": 0.91 if is_win else -1.0 if is_win is False else 0.0,
                    "updated_at": datetime.now().isoformat()
                })
                print(f"  - Matched and graded: {row['matchup']} ({res['away_score']}-{res['home_score']})")
            else:
                print(f"  - No result found for matchup: {row['matchup']} (Key: {key})")

        if updates:
            supabase.table("predictions_history").upsert(updates).execute()
            print(f"Successfully graded {len(updates)} NBA games.")
            
    except Exception as e:
        print(f"NBA Audit Error: {e}")

def audit_ncaa(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    print(f"Auditing NCAA for {date_str}...")

    # 1. Fetch scores from Henrygd NCAA API
    url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/{date_obj.year}/{date_obj.month:02d}/{date_obj.day:02d}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"NCAA Scoreboard error: {resp.status_code}")
            return
        
        data = resp.json()
        results_map = {}
        for g_wrapper in data.get('games', []):
            g = g_wrapper.get('game')
            if not g: continue
            
            # Status "final" or "final-ot" - check gameState field
            game_state = g.get('gameState', '').lower()
            if "final" in game_state:
                away = g.get('away', {})
                home = g.get('home', {})
                # Use short names as they usually match what's in Supabase for NCAA
                away_name = away.get('names', {}).get('short', '').lower().strip()
                home_name = home.get('names', {}).get('short', '').lower().strip()
                
                if away_name and home_name:
                    # Create normalized matching keys (spaceless) to match DB identity logic
                    norm_away = away_name.replace(" ", "").replace(".", "").replace("-", "")
                    norm_home = home_name.replace(" ", "").replace(".", "").replace("-", "")
                    
                    results_map[f"{norm_away}_{norm_home}"] = {
                        "away_score": int(away.get('score', 0)),
                        "home_score": int(home.get('score', 0)),
                        "total": int(away.get('score', 0)) + int(home.get('score', 0))
                    }

        if not results_map:
            print(f"No completed NCAA games found in API for {date_str}.")
            return

        # 2. Fetch 'pending' rows for this date from history
        pending = supabase.table("predictions_history") \
            .select("*") \
            .eq("league", "ncaa") \
            .eq("game_date", date_str) \
            .eq("status", "pending") \
            .execute()

        if not pending.data:
            print(f"No pending NCAA predictions found for {date_str}.")
            return

        print(f"Found {len(pending.data)} pending NCAA games. Checking against results...")
        updates = []
        for row in pending.data:
            # Matchup format in DB: "Duke @ UNC"
            parts = [p.strip().lower() for p in row['matchup'].split('@')]
            if len(parts) != 2: continue
            
            # Normalize DB names same way for lookup
            norm_db_away = parts[0].replace(" ", "").replace(".", "").replace("-", "")
            norm_db_home = parts[1].replace(" ", "").replace(".", "").replace("-", "")
            key = f"{norm_db_away}_{norm_db_home}"
            
            if key in results_map:
                res = results_map[key]
                actual_total = res['total']
                market_total = row['market_total']
                model_total = row['model_total']
                
                direction = "OVER" if model_total > market_total else "UNDER"
                actual_direction = grade_total(market_total, res['away_score'], res['home_score'])
                
                is_win = False
                if actual_direction == "PUSH":
                    is_win = None
                else:
                    is_win = direction == actual_direction

                updates.append({
                    "id": row['id'],
                    "league": row['league'],
                    "game_date": row['game_date'],
                    "matchup": row['matchup'],
                    "actual_score_away": res['away_score'],
                    "actual_score_home": res['home_score'],
                    "actual_total": actual_total,
                    "is_win": is_win,
                    "status": "graded",
                    "profit": 0.91 if is_win else -1.0 if is_win is False else 0.0,
                    "updated_at": datetime.now().isoformat()
                })
                print(f"  - Matched and graded: {row['matchup']} ({res['away_score']}-{res['home_score']})")
            else:
                # Debug print for missed matches
                print(f"  - No result found for matchup: {row['matchup']} (Key: {key})")

        if updates:
            supabase.table("predictions_history").upsert(updates).execute()
            print(f"Successfully graded {len(updates)} NCAA games.")

    except Exception as e:
        print(f"NCAA Audit Error: {e}")

def update_summary():
    """Recalculate the audit_summary table based on graded history."""
    print("Recalculating Audit Summary...")
    try:
        all_graded = supabase.table("predictions_history") \
            .select("league, is_win, profit") \
            .eq("status", "graded") \
            .execute()

        if not all_graded.data:
            return

        stats = {}
        total_stats = {"wins": 0, "losses": 0, "pushes": 0, "profit": 0, "total_games": 0}

        for row in all_graded.data:
            l = row['league'].lower()
            if l not in stats:
                stats[l] = {"wins": 0, "losses": 0, "pushes": 0, "profit": 0, "total_games": 0}
            
            p = row['profit'] if row['profit'] is not None else 0
            stats[l]['profit'] += p
            total_stats['profit'] += p
            
            if row['is_win'] is True:
                stats[l]['wins'] += 1
                total_stats['wins'] += 1
            elif row['is_win'] is False:
                stats[l]['losses'] += 1
                total_stats['losses'] += 1
            else:
                stats[l]['pushes'] += 1
                total_stats['pushes'] += 1
            
            stats[l]['total_games'] += 1
            total_stats['total_games'] += 1

        summary_rows = []
        
        # Add league-specific rows
        for l, s in stats.items():
            win_pct = round((s['wins'] / (s['total_games'] - s['pushes']) * 100), 1) if (s['total_games'] - s['pushes']) > 0 else 0
            roi = round((s['profit'] / s['total_games'] * 100), 1) if s['total_games'] > 0 else 0
            
            summary_rows.append({
                "league": l, # "nba", "ncaa", etc
                "wins": s['wins'],
                "losses": s['losses'],
                "pushes": s['pushes'],
                "profit": round(s['profit'] * 100, 2), # $100 units
                "win_pct": win_pct,
                "roi": roi,
                "updated_at": datetime.now().isoformat()
            })

        # Add TOTAL row
        t_win_pct = round((total_stats['wins'] / (total_stats['total_games'] - total_stats['pushes']) * 100), 1) if (total_stats['total_games'] - total_stats['pushes']) > 0 else 0
        t_roi = round((total_stats['profit'] / total_stats['total_games'] * 100), 1) if total_stats['total_games'] > 0 else 0
        
        summary_rows.append({
            "league": "TOTAL",
            "wins": total_stats['wins'],
            "losses": total_stats['losses'],
            "pushes": total_stats['pushes'],
            "profit": round(total_stats['profit'] * 100, 2), # $100 units
            "win_pct": t_win_pct,
            "roi": t_roi,
            "updated_at": datetime.now().isoformat()
        })

        if summary_rows:
            supabase.table("audit_summary").upsert(summary_rows).execute()
            print("Audit Summary updated.")

    except Exception as e:
        print(f"Summary Update Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="Grade games from last N days")
    args = parser.parse_args()

    for i in range(1, args.days + 1):
        target_date = datetime.now(ET_TZ) - timedelta(days=i)
        audit_nba(target_date)
        audit_ncaa(target_date)
    
    update_summary()
