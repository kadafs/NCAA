import os
import json
import argparse
from datetime import datetime
import zoneinfo
from nba_api.stats.endpoints import scoreboardv3
import sys

# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import get_target_date
from utils.odds_provider import get_odds, extract_total_for_matchup

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
MATCHUP_FILE = os.path.join(ROOT_DIR, "data", "nba_matchups.json")

import requests
import csv

def load_market_csv(target_date_obj):
    """
    Looks for a file named data/nba_market_YYYY-MM-DD.csv.
    Returns a dictionary of {(Away, Home): Market_Total}.
    """
    date_str = target_date_obj.strftime("%Y-%m-%d")
    filename = os.path.join(ROOT_DIR, "data", f"nba_market_{date_str}.csv")
    
    market_map = {}
    if not os.path.exists(filename):
        print(f"DEBUG: No NBA market CSV found for {date_str}.")
        return market_map

    print(f"DEBUG: Found NBA Market CSV for {date_str}. Injecting...")
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matchup = row.get('Matchup', '')
                # Handle different column naming conventions
                total_raw = row.get('Market_Odds') or row.get('Market Total') or row.get('Total')
                
                if not matchup or not total_raw:
                    continue
                
                import re
                total_match = re.search(r"(\d+\.?\d*)", str(total_raw))
                if not total_match:
                    continue
                total = float(total_match.group(1))

                # Identify teams in the CSV string (e.g. "Lakers vs Celtics" or "Lakers @ Celtics")
                away, home = None, None
                if ' vs ' in matchup:
                    parts = matchup.split(' vs ')
                    away, home = parts[0].strip(), parts[1].strip()
                elif '@' in matchup:
                    parts = matchup.split('@')
                    away, home = parts[0].strip(), parts[1].strip()
                
                if away and home:
                    market_map[(away.lower(), home.lower())] = total
        
        return market_map
    except Exception as e:
        print(f"Error loading NBA market CSV: {e}")
        return {}

def fetch_schedule_espn(date_str):
    """
    Fallback: Fetches NBA schedule from ESPN's public API.
    Reliable for cloud environments.
    """
    print(f"Attempting ESPN Fallback for {date_str}...")
    try:
        # ESPN uses YYYYMMDD format
        espn_date = date_str.replace("-", "")
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={espn_date}"
        
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        matchups = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            
            # Competitors: usually home is index 0, but check homeAway
            home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
            away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
            
            matchups.append({
                "away": away['team']['name'], # e.g. "Lakers"
                "home": home['team']['name'], # e.g. "Celtics"
                "away_city": away['team']['location'],
                "home_city": home['team']['location'],
                "game_time": event['status']['type']['detail'] # e.g. "Final" or "7:00 PM ET"
            })
            
        print(f"ESPN found {len(matchups)} games.")
        return matchups
    except Exception as e:
        print(f"ESPN Fallback failed: {e}")
        return []

def fetch_nba_daily_schedule(target_date=None):
    if target_date is None:
        target_date = get_target_date()
    
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"Fetching NBA schedule for {date_str}...")
    
    matchups = []
    
    # 1. Try Official API (nba_api)
    try:
        # ScoreboardV3 is the newer, flat structure endpoint
        custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'Connection': 'keep-alive',
        }
        
        sb = scoreboardv3.ScoreboardV3(game_date=date_str, headers=custom_headers, timeout=15)
        data = sb.get_dict()
        
        games = data.get('scoreboard', {}).get('games', [])
        
        for g in games:
            home = g['homeTeam']
            away = g['awayTeam']
            matchups.append({
                "away": away['teamName'],
                "home": home['teamName'],
                "away_city": away['teamCity'],
                "home_city": home['teamCity'],
                "game_time": g.get('gameStatusText', 'Scheduled')
            })
            
        print(f"Nba_api found {len(matchups)} games.")
        
    except Exception as e:
        print(f"Primary NBA API failed: {e}")

    # 2. Fallback to ESPN if primary failed (or found 0 games, which might mean blocked)
    if not matchups:
        matchups = fetch_schedule_espn(date_str)
        
    # 3. Inject Vegas Lines (NBA V1.3 Integration)
    if matchups:
        print("Injecting NBA Vegas Lines...")
        try:
            odds_data = get_odds("nba", provider='render')
            if odds_data:
                for m in matchups:
                    total = extract_total_for_matchup(odds_data, m['away'], m['home'])
                    if total:
                        m['total'] = total
                        m['odds_source'] = "Action Network (Vegas)"
                    else:
                        m['total'] = None
                        m['odds_source'] = "Waiting for Lines"
            else:
                for m in matchups: 
                    m['total'] = None
                    m['odds_source'] = "Waiting for Lines"
        except Exception as e:
            print(f"Failed to inject NBA odds from API: {e}")

        # 4. CSV Fallback for missing/null lines
        market_csv = load_market_csv(target_date)
        if market_csv:
            print(f"Checking {len(market_csv)} CSV lines for gaps...")
            for m in matchups:
                if m.get('total') is None:
                    # Simple matching logic
                    key = (m['away'].lower(), m['home'].lower())
                    if key in market_csv:
                        m['total'] = market_csv[key]
                        m['odds_source'] = "Manual CSV (Fallback)"
                        print(f"  - Injected {m['total']} for {m['away']} @ {m['home']} from CSV")

    # Save results
    with open(MATCHUP_FILE, "w", encoding="utf-8") as f:
        json.dump(matchups, f, indent=2)
        
    return matchups

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    target = get_target_date(args.date)
    fetch_nba_daily_schedule(target)
