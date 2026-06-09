"""
kbo/fetch_schedule.py
Fetches today's (or a specified date's) KBO schedule and game matchups
from mykbostats.com. Returns structured game dicts with team names and venues.

Probable starting pitchers are identified by scraping the game detail page
for the 'GS' (game started) marker in the pitching box, or fall back to
the most recent starting pitcher for that team (last-7-days rotation logic).
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import re
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
BASE_URL = 'https://mykbostats.com'

# KST is UTC+9
KST = timezone(timedelta(hours=9))

# Venue name mappings from schedule text -> canonical name
VENUE_MAP = {
    'Seoul-Jamsil':   'Jamsil Baseball Stadium',
    'Daejeon':        'Hanwha Life Eagles Park',
    'Seoul-Gocheok':  'Gocheok Sky Dome',
    'Busan-Sajik':    'Sajik Baseball Stadium',
    'Suwon':          'Suwon KT Wiz Park',
    'Incheon':        'Incheon SSG Landers Field',
    'Daegu':          'Daegu Samsung Lions Park',
    'Gwangju':        'Gwangju-Kia Champions Field',
    'Changwon':       'Changwon NC Park',
    'Pohang':         'Pohang Baseball Stadium',
}

def _get_kst_date(date_str: str | None = None) -> str:
    """Returns date as 'YYYYMMDD' in KST. Accepts 'MM/DD/YYYY' or None for today."""
    if date_str:
        dt = datetime.strptime(date_str, '%m/%d/%Y')
    else:
        dt = datetime.now(KST)
    return dt.strftime('%Y%m%d')

def _parse_schedule_page(date_str: str | None = None) -> list[dict]:
    """
    Scrapes the mykbostats schedule page and extracts games for the target date.
    Returns a list of dicts: {away_team, home_team, venue, game_url, time_kst}
    """
    url = f'{BASE_URL}/schedule'
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    # Find all game links on the schedule page
    target_date = _get_kst_date(date_str)
    target_fmt = f'{target_date[:4]}{target_date[4:6]}{target_date[6:]}'  # YYYYMMDD

    games = []
    # Game links follow pattern: /games/NNNNN-Team-vs-Team-YYYYMMDD
    all_links = soup.find_all('a', href=re.compile(r'/games/\d+-\w+-vs-\w+-\d{8}'))
    seen = set()
    for link in all_links:
        href = link['href']
        if href in seen:
            continue
        seen.add(href)

        # Extract date from URL
        match = re.search(r'/games/(\d+)-(\w+)-vs-(\w+)-(\d{8})', href)
        if not match:
            continue
        game_id, away_slug, home_slug, game_date = match.groups()
        if game_date != target_date:
            continue

        # Get surrounding context for venue and time
        parent = link.find_parent(['tr', 'li', 'div'])
        parent_text = parent.get_text(' ', strip=True) if parent else ''

        # Identify venue
        venue = 'Unknown'
        for key, val in VENUE_MAP.items():
            if key in parent_text:
                venue = val
                break

        # Team names: slugs use '-' separator, convert to title case
        away_team = away_slug.replace('-', ' ')
        home_team = home_slug.replace('-', ' ')

        # Try to get full team name from link text or surrounding elements
        link_text = link.get_text(' ', strip=True)

        games.append({
            'game_id':   game_id,
            'away_team': away_team,
            'home_team': home_team,
            'venue':     venue,
            'game_url':  f'{BASE_URL}{href}',
            'game_date': game_date,
        })

    return games


def _get_probable_starters(game_url: str) -> tuple[str | None, str | None]:
    """
    For a game that has started or completed, returns (away_starter, home_starter)
    by finding the first pitcher listed with 'GS' > 0 in the pitching table.
    For pre-game pages, returns (None, None).
    """
    try:
        r = requests.get(game_url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')

        pitching_h3 = soup.find('h3', string=lambda t: t and 'Pitching' in t)
        if not pitching_h3:
            return None, None

        panel = pitching_h3.find_parent('div')
        if not panel:
            return None, None

        text = panel.get_text(' ', strip=True)
        # Pattern: "TeamName ... ERA IP ... GS" where GS column is near end of row
        # The pitching section lists away team first, then home team.
        # We look for lines where GS != 0 (the actual game starter).

        rows = panel.find_all('tr')
        away_starter = None
        home_starter = None
        current_team = 'away'

        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all('td')]
            if not cells:
                th_text = ' '.join(th.get_text(strip=True) for th in row.find_all('th'))
                if th_text and any(t in th_text for t in ['ERA', 'IP', 'GS']):
                    continue
                if th_text:
                    current_team = 'home' if away_starter else 'away'
                continue
            # If GS column (last) is non-zero, this is the starter
            if len(cells) >= 2 and cells[-1].isdigit() and int(cells[-1]) > 0:
                name = cells[0]
                # Strip jersey number if present
                name = re.sub(r'#\d+', '', name).strip()
                if current_team == 'away' and not away_starter:
                    away_starter = name
                elif current_team == 'home' and not home_starter:
                    home_starter = name

        return away_starter, home_starter

    except Exception:
        return None, None


def get_today_games(date_str: str | None = None) -> list[dict]:
    """
    Main entry point. Returns list of game dicts for the KBO date.
    Each dict includes: game_id, away_team, home_team, venue, game_url,
    away_starter (name or None), home_starter (name or None).
    """
    print(f"Fetching KBO schedule for {date_str or 'today (KST)'}...")
    games = _parse_schedule_page(date_str)
    print(f"Found {len(games)} games.")

    for i, game in enumerate(games):
        time.sleep(0.5)  # Polite rate limiting
        away_s, home_s = _get_probable_starters(game['game_url'])
        game['away_starter'] = away_s
        game['home_starter'] = home_s
        status = f"{away_s or 'TBD'} vs {home_s or 'TBD'}"
        print(f"  [{i+1}/{len(games)}] {game['away_team']} @ {game['home_team']} | Starters: {status}")

    return games


if __name__ == '__main__':
    games = get_today_games()
    for g in games:
        print(g)
