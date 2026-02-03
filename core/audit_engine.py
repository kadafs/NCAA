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
from utils.mapping import NBA_TRICODES, clean_team_name, BASKETBALL_ALIASES

def get_canonical_key(away, home):
    """Generates a standardized key for matching matchups across sources."""
    a = clean_team_name(away)
    h = clean_team_name(home)
    # Apply aliases to resolve variations (e.g. westerncaro -> westerncarolina)
    a = BASKETBALL_ALIASES.get(a, a)
    h = BASKETBALL_ALIASES.get(h, h)
    return f"{a}_{h}"

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

def fetch_nba_scores_official(date_str):
    """Primary: Fetch scores from official NBA API."""
    try:
        sb = scoreboardv3.ScoreboardV3(game_date=date_str, timeout=15)
        data = sb.get_dict()
        games = data.get('scoreboard', {}).get('games', [])
        
        results_map = {}
        for g in games:
            if g.get('gameStatus') == 3: # 3 = Final
                away = g['awayTeam']
                home = g['homeTeam']
                
                # Use tricode to get full name which matches our database
                # Use tricode to get full name which matches our database
                away_full = NBA_TRICODES.get(away['teamTricode'], away['teamName'])
                home_full = NBA_TRICODES.get(home['teamTricode'], home['teamName'])
                
                key = get_canonical_key(away_full, home_full)
                status_desc = "Final" if g.get('gameStatus') == 3 else "Ongoing/Pre"
                results_map[key] = {
                    "away_score": away['score'],
                    "home_score": home['score'],
                    "total": away['score'] + home['score'],
                    "status_code": g.get('gameStatus'),
                    "status_desc": status_desc
                }
        return results_map
    except Exception as e:
        print(f"Stats.nba.com Audit Fetch failed: {e}")
        return {}

def fetch_nba_scores_espn(date_str):
    """Fallback: Fetch completed NBA scores from ESPN."""
    try:
        espn_date = date_str.replace("-", "")
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={espn_date}"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        results = {}
        for event in data.get('events', []):
            comp = event['competitions'][0]
            home_comp = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
            away_comp = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
            
            # ESPN names are usually "Lakers", "Celtics"
            # Use clean_team_name which handles substring/expansion
            away_name = away_comp['team']['displayName']
            home_name = home_comp['team']['displayName']
            
            key = get_canonical_key(away_name, home_name)
            is_final = event['status']['type']['state'] == 'post'
            results[key] = {
                "away_score": int(away_comp['score']),
                "home_score": int(home_comp['score']),
                "total": int(away_comp['score']) + int(home_comp['score']),
                "status_code": 3 if is_final else 1,
                "status_desc": "Final" if is_final else "Not Final"
            }
        return results
    except Exception as e:
        print(f"NBA ESPN Audit Fallback failed: {e}")
        return {}

def audit_nba(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    print(f"Auditing NBA for {date_str}...")

    # 1. Fetch scores (Primary: stats.nba.com, Fallback: ESPN)
    results_map = fetch_nba_scores_official(date_str)
    if not results_map:
        print("Falling back to ESPN for NBA results...")
        results_map = fetch_nba_scores_espn(date_str)
        
    if not results_map:
        print(f"Failed to fetch any NBA results for {date_str}.")
        return

    print(f"DEBUG: NBA Results Map Keys: {list(results_map.keys())[:5]}... (Total: {len(results_map)})")

    # 2. Fetch 'pending' rows for this date from history
    try:
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
            parts = [p.strip() for p in row['matchup'].split('@')]
            if len(parts) != 2: continue
            
            key = get_canonical_key(parts[0], parts[1])
            
            # Substring/Fuzzy check if direct key missing
            if key not in results_map:
                for r_key in results_map:
                    ra, rh = r_key.split('_')
                    da, dh = key.split('_')
                    if (da in ra or ra in da) and (dh in rh or rh in dh):
                        key = r_key
                        break

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
                away_name = away.get('names', {}).get('short', '')
                home_name = home.get('names', {}).get('short', '')
                
                if away_name and home_name:
                    key = get_canonical_key(away_name, home_name)
                    results_map[key] = {
                        "away_score": int(away.get('score', 0)),
                        "home_score": int(home.get('score', 0)),
                        "total": int(away.get('score', 0)) + int(home.get('score', 0))
                    }

        if not results_map:
            print(f"No completed NCAA games found in API for {date_str}.")
            return

        print(f"DEBUG: NCAA Results Map Keys: {list(results_map.keys())[:5]}... (Total: {len(results_map)})")

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
            parts = [p.strip() for p in row['matchup'].split('@')]
            if len(parts) != 2: continue
            
            key = get_canonical_key(parts[0], parts[1])
            
            # Hotfix for known Kansas City vs Kansas naming mismatch
            if key == "kansas_stthomas":
                key = "kansascity_stthomas"
            
            # Robust matching: try substring if direct key missing
            if key not in results_map:
                for r_key in results_map:
                    ra, rh = r_key.split('_')
                    da, dh = key.split('_')
                    # Match if (Away in Result_Away or Result_Away in Away) AND (Home in Result_Home or Result_Home in Home)
                    if (da in ra or ra in da) and (dh in rh or rh in dh):
                        key = r_key
                        break

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
    parser.add_argument("--league", choices=["nba", "ncaa", "all"], default="all", help="League to audit (default: all)")
    args = parser.parse_args()

    for i in range(1, args.days + 1):
        target_date = datetime.now(ET_TZ) - timedelta(days=i)
        if args.league in ["nba", "all"]:
            audit_nba(target_date)
        if args.league in ["ncaa", "all"]:
            audit_ncaa(target_date)
    
    update_summary()
