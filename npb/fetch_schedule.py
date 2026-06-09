"""
npb/fetch_schedule.py
Fetches today's NPB schedule and game matchups from the official npb.jp site.
Because the site is in Japanese, this module handles translation of team
names and parsing the HTML table structures.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
BASE_URL = 'https://npb.jp'

# JST is UTC+9 (same as KST)
JST = timezone(timedelta(hours=9))

# Japanese to English team name mapping
TEAM_MAP = {
    '巨人':       'Yomiuri Giants',
    'ヤクルト':   'Yakult Swallows',
    'ＤｅＮＡ':   'DeNA BayStars',
    'DeNA':       'DeNA BayStars',
    '中日':       'Chunichi Dragons',
    '阪神':       'Hanshin Tigers',
    '広島':       'Hiroshima Carp',
    '日本ハム':   'Nippon-Ham Fighters',
    '楽天':       'Rakuten Eagles',
    '西武':       'Seibu Lions',
    'ロッテ':     'Lotte Marines',
    'オリックス': 'Orix Buffaloes',
    'ソフトバンク':'SoftBank Hawks',
}

def _get_jst_date(date_str: str | None = None) -> tuple[str, str, str]:
    """Returns (YYYY, MM, DD) in JST."""
    if date_str:
        dt = datetime.strptime(date_str, '%m/%d/%Y')
    else:
        dt = datetime.now(JST)
    return dt.strftime('%Y'), dt.strftime('%m'), dt.strftime('%d')

def get_today_games(date_str: str | None = None) -> list[dict]:
    """
    Main entry point. Returns list of game dicts for the NPB date.
    Each dict includes: game_id, away_team, home_team, venue, away_starter, home_starter.
    """
    yyyy, mm, dd = _get_jst_date(date_str)
    print(f"Fetching NPB schedule for {mm}/{dd}/{yyyy} (JST)...")
    
    url = f"{BASE_URL}/games/{yyyy}/schedule_{mm}_detail.html"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = 'utf-8'  # Force UTF-8 since npb.jp might not set charset properly
    except Exception as e:
        print(f"Failed to fetch NPB schedule: {e}")
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    games = []
    
    # NPB schedule groups games by date headers. We look for rows matching our DD.
    # Format typically: <tr id="dateMMDD"> or text matching M/D
    # For robust parsing, we will scan all rows and track the current date.
    
    tables = soup.find_all('table')
    if not tables:
        return []
        
    current_date = None
    target_date_str = f"{int(mm)}/{int(dd)}"  # e.g. "6/1"
    
    for row in tables[0].find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if not cells:
            continue
            
        row_text = row.get_text(' ', strip=True)
        
        # Check if this row is a date header (e.g. "6/1（月）")
        text0 = cells[0].get_text(strip=True)
        date_match = re.search(r'^(\d{1,2})/(\d{1,2})', text0)
        
        # NPB uses full-width parens or normal parens for day of week
        is_date_cell = date_match and ('(' in text0 or '（' in text0 or '月' in text0 or '火' in text0 or '水' in text0 or '木' in text0 or '金' in text0 or '土' in text0 or '日' in text0)
        
        if is_date_cell:
            current_date = f"{date_match.group(1)}/{date_match.group(2)}"
            if len(cells) < 4:
                continue
            else:
                # shift cells if date is column 0 but game data is in columns 1-4
                cells = cells[1:]
             
        if current_date != target_date_str:
            continue
            
        # Parse game row
        # Expected structure: Matchup | Venue+Time | Notes | Pitchers
        if len(cells) >= 2:
            matchup_text = cells[0].get_text(' ', strip=True)
            
            # Matchup looks like "巨人 3 - 2 オリックス" or "巨人 - オリックス"
            # Split by '-', 'vs', or numbers
            matchup_parts = re.split(r'\s+[-|vs|中止]+\s+|\s+\d+\s+-\s+\d+\s+', matchup_text)
            
            if len(matchup_parts) >= 2:
                away_jp = matchup_parts[0].strip()
                home_jp = matchup_parts[-1].strip()
            else:
                continue # not a valid game row
            
            # Translate
            away_team = TEAM_MAP.get(away_jp, away_jp)
            home_team = TEAM_MAP.get(home_jp, home_jp)
            
            if not away_team or not home_team or away_team == away_jp:
                continue # Skip if we can't translate (likely not a game row)
                
            venue_time = cells[1].get_text(' ', strip=True)
            venue = venue_time.split()[0] if venue_time else 'Unknown'
            
            # Probable pitchers (often in column 3 if it exists)
            away_starter, home_starter = 'TBD', 'TBD'
            if len(cells) >= 4:
                pitchers_text = cells[3].get_text(' ', strip=True)
                # Text looks like "勝：則本 敗：九里" or "予告先発：[Away] [Home]"
                parts = pitchers_text.split()
                if len(parts) >= 2:
                    # Strip out prefixes like 勝：, 敗：, S：
                    away_starter = re.sub(r'^[勝敗S]：', '', parts[0])
                    home_starter = re.sub(r'^[勝敗S]：', '', parts[1])
                    
            games.append({
                'game_id': f"{yyyy}{mm}{dd}_{away_team}_{home_team}".replace(' ', ''),
                'away_team': away_team,
                'home_team': home_team,
                'venue': venue,
                'away_starter': away_starter,
                'home_starter': home_starter
            })

    print(f"Found {len(games)} games.")
    for i, g in enumerate(games):
        print(f"  [{i+1}/{len(games)}] {g['away_team']} @ {g['home_team']} | Starters: {g['away_starter']} vs {g['home_starter']}")
        
    return games

if __name__ == '__main__':
    get_today_games('06/01/2026')  # Test with a known date from the probe
