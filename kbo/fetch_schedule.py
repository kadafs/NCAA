"""
kbo/fetch_schedule.py
Fetches today's KBO schedule and game matchups from Naver Sports API.
"""

import requests
import json
from datetime import datetime, timezone, timedelta

def _get_kst_date(date_str: str | None = None) -> tuple[str, str, str, str]:
    """Returns (YYYY, MM, DD, YYYY-MM-DD) in KST (UTC+9)."""
    KST = timezone(timedelta(hours=9))
    if date_str:
        try:
            dt = datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        dt = datetime.now(KST)
    return dt.strftime('%Y'), dt.strftime('%m'), dt.strftime('%d'), dt.strftime('%Y-%m-%d')

def get_today_games(date_str: str | None = None) -> list[dict]:
    """
    Main entry point. Returns list of game dicts for the KBO date.
    Each dict includes: game_id, away_team, home_team, venue, away_starter, home_starter, game_time.
    """
    yyyy, mm, dd, yyyy_mm_dd = _get_kst_date(date_str)
    print(f"Fetching KBO schedule for {yyyy_mm_dd} from Naver API...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://sports.naver.com/kbaseball/schedule/index'
    }
    
    url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&categoryId=kbo&date={yyyy_mm_dd}"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Failed to fetch KBO schedule: {e}")
        return []

    games = []
    
    # Check if successful and extract games list
    if not data.get('success', False):
        print("Naver API returned success=False")
        return []
        
    result = data.get('result', {})
    games_list = result.get('games', [])
    
    if not games_list:
        print(f"No games found on {yyyy_mm_dd}.")
        return []
        
    for game in games_list:
        away_team = game.get('awayTeamName')
        home_team = game.get('homeTeamName')
        
        if not away_team or not home_team:
            continue
            
        # Naver game schedule doesn't include probable pitchers here
        away_starter = 'TBD'
        home_starter = 'TBD'
        
        # Time format is usually "HH:MM", we can extract it from gameDateTime (e.g. 2026-07-09T18:30:00)
        game_time_raw = game.get('gameDateTime', '')
        game_time = game_time_raw.split('T')[1][:5] if 'T' in game_time_raw else '00:00'
        
        # English translations for KBO teams
        team_map = {
            '두산': 'Doosan Bears',
            'LG': 'LG Twins',
            'SSG': 'SSG Landers',
            'NC': 'NC Dinos',
            'KIA': 'KIA Tigers',
            '롯데': 'Lotte Giants',
            '삼성': 'Samsung Lions',
            '한화': 'Hanwha Eagles',
            '키움': 'Kiwoom Heroes',
            'KT': 'KT Wiz',
            'kt': 'KT Wiz'
        }
        
        away_team_eng = team_map.get(away_team, away_team)
        home_team_eng = team_map.get(home_team, home_team)
        
        game_id = f"{yyyy}{mm}{dd}_{away_team_eng}_{home_team_eng}".replace(' ', '')
        
        games.append({
            'game_id': game_id,
            'game_time': game_time,
            'away_team': away_team_eng,
            'home_team': home_team_eng,
            'venue': 'KBO Stadium',
            'away_starter': away_starter,
            'home_starter': home_starter
        })

    print(f"Found {len(games)} games.")
    for i, g in enumerate(games):
        print(f"  [{i+1}/{len(games)}] {g['away_team']} @ {g['home_team']} | Time: {g['game_time']}")
        
    return games

if __name__ == "__main__":
    get_today_games()
