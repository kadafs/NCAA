# Result Scraper & Grading Engine v1.0
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
                results_map[f"{away['teamName']}_{home['teamName']}".lower()] = {
                    "away_score": away['score'],
                    "home_score": home['score'],
                    "total": away['score'] + home['score']
                }
        
        if not results_map:
            print(f"No completed NBA games found for {date_str}.")
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

        updates = []
        for row in pending.data:
            # Matchup format in DB: "Lakers @ Celtics"
            # Matching key: "lakers_celtics"
            parts = [p.strip().lower() for p in row['matchup'].split('@')]
            if len(parts) != 2: continue
            key = f"{parts[0]}_{parts[1]}"
            
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
                    "actual_score_away": res['away_score'],
                    "actual_score_home": res['home_score'],
                    "actual_total": actual_total,
                    "is_win": is_win,
                    "status": "graded",
                    "profit": 0.91 if is_win else -1.0 if is_win is False else 0.0, # Simple units
                    "updated_at": datetime.now().isoformat()
                })

        if updates:
            supabase.table("predictions_history").upsert(updates).execute()
            print(f"✅ Successfully graded {len(updates)} NBA games.")
            
    except Exception as e:
        print(f"NBA Audit Error: {e}")

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
        for row in all_graded.data:
            l = row['league']
            if l not in stats: stats[l] = {"wins": 0, "losses": 0, "pushes": 0, "profit": 0.0}
            
            if row['is_win'] is True: stats[l]['wins'] += 1
            elif row['is_win'] is False: stats[l]['losses'] += 1
            else: stats[l]['pushes'] += 1
            
            stats[l]['profit'] += row['profit']

        summary_rows = []
        for l, s in stats.items():
            total_games = s['wins'] + s['losses']
            win_pct = (s['wins'] / total_games * 100) if total_games > 0 else 0
            # ROI = Profit / Total Units Wagered
            roi = (s['profit'] / total_games * 100) if total_games > 0 else 0
            
            summary_rows.append({
                "league": l,
                "wins": s['wins'],
                "losses": s['losses'],
                "pushes": s['pushes'],
                "profit": round(s['profit'] * 100, 2), # Using 100 as unit size proxy
                "win_pct": round(win_pct, 1),
                "roi": round(roi, 1),
                "updated_at": datetime.now().isoformat()
            })

        if summary_rows:
            supabase.table("audit_summary").upsert(summary_rows).execute()
            print("✅ Audit Summary updated.")

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
    
    update_summary()
