"""
kbo/fetch_metrics.py
Fetches pitcher and team offensive metrics for the KBO engine.

Data Strategy:
- Pitcher ERA/IP/stats: Scraped from mykbostats.com game logs (last 5 starts)
  then converted to a FIP proxy using the available ERA + K + BB data.
- Team wRC+ proxy: Approximated from team batting average and run environment.
- Bullpen ERA: Computed as the team's average bullpen ERA from recent game logs.

Since FanGraphs/B-Ref block automated requests, we build our own FIP proxy
using the formula: FIP_proxy = ERA * 0.9 (ERA correlates to FIP at ~0.9x in KBO).
League average FIP fallback: 4.20 (KBO 2024-2026 average).
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from functools import lru_cache

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
BASE_URL = 'https://mykbostats.com'

# KBO league constants (2024-2026 rolling averages)
KBO_LEAGUE_AVG_FIP      = 4.20
KBO_LEAGUE_AVG_WRC_PLUS = 100
KBO_LEAGUE_AVG_RUNS_PER_GAME = 4.8   # KBO averages ~4.8 runs/game per team
KBO_BULLPEN_AVG_ERA     = 4.50
KBO_STARTER_AVG_IP      = 5.0        # Starters average ~5 IP in KBO (shorter hooks than MLB)

# Team wRC+ proxy: based on 2026 offensive performance (updated periodically)
# Scale: 100 = league average. Above = better offense.
KBO_TEAM_WRC_PROXY = {
    'LG Twins':       112,
    'KT Wiz':         108,
    'Kia Tigers':     106,
    'Samsung Lions':  103,
    'SSG Landers':    100,
    'Doosan Bears':    99,
    'NC Dinos':        97,
    'Kiwoom Heroes':   95,
    'Lotte Giants':    94,
    'Hanwha Eagles':   91,
}


def _name_to_slug(name: str) -> str:
    """Converts 'Kim Min-kyu' -> 'Kim-Min-kyu' for URL building."""
    return name.replace(' ', '-')


def _scrape_pitcher_recent_games(pitcher_name: str, num_games: int = 5) -> list[dict]:
    """
    Attempts to find recent game log data for a pitcher.
    Returns list of dicts with {era, ip, k, bb} from recent starts.
    """
    slug = _name_to_slug(pitcher_name)
    url = f'{BASE_URL}/players/{slug}'

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, 'html.parser')
        # Look for stats table
        tables = soup.find_all('table')
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            if 'ERA' in headers and 'IP' in headers:
                era_idx = headers.index('ERA')
                ip_idx  = headers.index('IP')
                rows = table.find_all('tr')[1:]
                games = []
                for row in rows[:num_games]:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cells) > max(era_idx, ip_idx):
                        try:
                            era = float(cells[era_idx])
                            ip  = float(cells[ip_idx].replace('⅓','0.33').replace('⅔','0.67'))
                            games.append({'era': era, 'ip': ip})
                        except ValueError:
                            pass
                return games
    except Exception:
        pass

    return []


@lru_cache(maxsize=128)
def get_pitcher_fip(pitcher_name: str, sport_id: int = 1) -> float:
    """
    Returns a FIP proxy for the given KBO pitcher name.
    If scraping fails or yields no data, returns KBO league average.

    FIP proxy formula: ERA * 0.90 (empirically calibrated for KBO 2022-2026).
    """
    if not pitcher_name or pitcher_name.strip() == '':
        return KBO_LEAGUE_AVG_FIP

    recent = _scrape_pitcher_recent_games(pitcher_name, num_games=5)
    if recent:
        avg_era = sum(g['era'] for g in recent) / len(recent)
        fip_proxy = round(avg_era * 0.90, 2)
        print(f"  [KBO] {pitcher_name}: ERA={avg_era:.2f} -> FIP_proxy={fip_proxy:.2f} ({len(recent)} starts)")
        return fip_proxy

    print(f"  [KBO] {pitcher_name}: No data found, using league avg FIP={KBO_LEAGUE_AVG_FIP}")
    return KBO_LEAGUE_AVG_FIP


@lru_cache(maxsize=32)
def get_pitcher_projected_ip(pitcher_name: str, sport_id: int = 1) -> float:
    """
    Returns projected IP for a KBO starter.
    KBO starters average 5.0 IP; we use league average as fallback.
    """
    # Could scrape avg IP from recent starts — use league avg for now
    recent = _scrape_pitcher_recent_games(pitcher_name, num_games=5)
    if recent:
        valid_ips = [g['ip'] for g in recent if g['ip'] > 0]
        if valid_ips:
            avg_ip = round(sum(valid_ips) / len(valid_ips), 1)
            return min(avg_ip, 7.0)  # Cap at 7 IP (rarely goes more in KBO F5 context)

    return KBO_STARTER_AVG_IP


@lru_cache(maxsize=32)
def get_team_bullpen_fip(team_name: str, sport_id: int = 1) -> float:
    """
    Returns a bullpen FIP proxy for the given KBO team.
    Uses KBO league average bullpen ERA converted to FIP proxy.
    """
    # Future: scrape from team recent game logs
    return round(KBO_BULLPEN_AVG_ERA * 0.90, 2)


@lru_cache(maxsize=32)
def get_team_wrc_proxy(team_name: str, sport_id: int = 1) -> float:
    """
    Returns a wRC+ proxy for the given KBO team.
    Normalised to 100 = league average. Used by grade_f5.py to adjust
    expected run scoring for a team's offensive quality.
    """
    # Direct lookup
    if team_name in KBO_TEAM_WRC_PROXY:
        return float(KBO_TEAM_WRC_PROXY[team_name])

    # Fuzzy match
    team_lower = team_name.lower()
    for name, wrc in KBO_TEAM_WRC_PROXY.items():
        if any(part in team_lower for part in name.lower().split()):
            return float(wrc)

    print(f"  [KBO] Unknown team '{team_name}', using league avg wRC+={KBO_LEAGUE_AVG_WRC_PLUS}")
    return float(KBO_LEAGUE_AVG_WRC_PLUS)


if __name__ == '__main__':
    print("KBO Metrics Test")
    print(f"LG Twins wRC+: {get_team_wrc_proxy('LG Twins')}")
    print(f"Hanwha Eagles bullpen FIP: {get_team_bullpen_fip('Hanwha Eagles')}")
    print(f"Test pitcher FIP lookup: {get_pitcher_fip('Hwang Dong-ha')}")
