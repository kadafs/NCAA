from mlb_time import get_mlb_now
import datetime
import statsapi

# We use the live FIP engine constants
FIP_CONSTANT = 3.20

def _parse_ip(ip_str):
    """Convert statsapi innings-pitched string (e.g. '18.2') to decimal IP."""
    try:
        ip = float(ip_str)
        whole = int(ip)
        frac = ip - whole
        if abs(frac - 0.1) < 0.01:
            return whole + 0.333
        elif abs(frac - 0.2) < 0.01:
            return whole + 0.667
        return ip
    except (ValueError, TypeError):
        return 0.0

import json
import os

_player_map = {}
_map_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'player_map.json')
if os.path.exists(_map_path):
    try:
        with open(_map_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for name, info in data.items():
                _player_map[name] = info['id']
    except Exception:
        pass

# Hardcoded 30 MLB Teams to bypass slow API lookups
TEAM_MAP = {
    'Arizona Diamondbacks': 109, 'Atlanta Braves': 144, 'Baltimore Orioles': 110,
    'Boston Red Sox': 111, 'Chicago Cubs': 112, 'Chicago White Sox': 145,
    'Cincinnati Reds': 113, 'Cleveland Guardians': 114, 'Colorado Rockies': 115,
    'Detroit Tigers': 116, 'Houston Astros': 117, 'Kansas City Royals': 118,
    'Los Angeles Angels': 108, 'Los Angeles Dodgers': 119, 'Miami Marlins': 146,
    'Milwaukee Brewers': 158, 'Minnesota Twins': 142, 'New York Yankees': 147,
    'New York Mets': 121, 'Oakland Athletics': 133, 'Athletics': 133,
    'Philadelphia Phillies': 143, 'Pittsburgh Pirates': 134, 'San Diego Padres': 135,
    'San Francisco Giants': 137, 'Seattle Mariners': 136, 'St. Louis Cardinals': 138,
    'Tampa Bay Rays': 139, 'Texas Rangers': 140, 'Toronto Blue Jays': 141,
    'Washington Nationals': 120
}

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Global Session with Exponential Backoff to survive MLB API rate limits
_session = requests.Session()
_retry_strategy = Retry(
    total=5,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
_adapter = HTTPAdapter(max_retries=_retry_strategy)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

import sqlite3

def get_historical_pitcher_fip(pitcher_name, target_date, sport_id=1):
    """
    Returns point-in-time FIP for a pitcher by querying the stats API.
    Uses the exact same Bayesian Shrinkage and weighting logic as the live script.
    """
    if pitcher_name in ('TBD', '', None):
        return 4.50
        
    person_id = _player_map.get(pitcher_name)
    if not person_id:
        players = [p for p in statsapi.lookup_player(pitcher_name, sportId=1) if p.get('primaryPosition', {}).get('abbreviation') in ('P', 'TWP')]
        if not players:
            return 4.50
        person_id = players[0]['id']
        
    current_season = int(target_date.split('-')[0])
    prior_season = current_season - 1
    
    t_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    end_date_str = (t_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    def _fetch_fip_ip(hydrate_str):
        try:
            url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate={hydrate_str}"
            r = _session.get(url, timeout=10)
            raw = r.json()
            stats = {}
            for person in raw.get('people', []):
                for stat_grp in person.get('stats', []):
                    splits = stat_grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats:
                    break
            
            ip = _parse_ip(stats.get('inningsPitched', '0'))
            if ip < 1.0: return None, 0.0
            
            hr = int(stats.get('homeRuns', 0))
            bb = int(stats.get('baseOnBalls', 0))
            hbp = int(stats.get('hitBatsmen', 0))
            k = int(stats.get('strikeOuts', 0))
            fip = ((13 * hr) + (3 * (bb + hbp)) - (2 * k)) / ip + FIP_CONSTANT
            return fip, ip
        except Exception:
            return None, 0.0
            
    cur_fip, cur_ip = _fetch_fip_ip(f"stats(group=[pitching],type=byDateRange,startDate={current_season}-01-01,endDate={end_date_str})")
    prior_fip, prior_ip = _fetch_fip_ip(f"stats(group=[pitching],type=season,season={prior_season})")
    
    REGRESSION_WEIGHT = 50.0
    league_fip = 4.25
    
    total_ip = cur_ip + (prior_ip if prior_fip else 0.0)
    if total_ip == 0: return league_fip
    
    weighted_perf = 0.0
    if cur_fip is not None: weighted_perf += (cur_fip * cur_ip)
    if prior_fip is not None: weighted_perf += (prior_fip * prior_ip)
    
    projected_fip = (weighted_perf + (league_fip * REGRESSION_WEIGHT)) / (total_ip + REGRESSION_WEIGHT)
    return round(projected_fip, 2)

def get_historical_pitcher_avg_ip(pitcher_name, target_date, sport_id=1):
    """
    Returns rolling average IP per start for a pitcher based on their last 10
    starts strictly before target_date. Avoids leaking current-season totals.
    """
    if pitcher_name in ('TBD', '', None):
        return 5.0

    person_id = _player_map.get(pitcher_name)
    if not person_id:
        try:
            players = [p for p in statsapi.lookup_player(pitcher_name, sportId=1) if p.get('primaryPosition', {}).get('abbreviation') in ('P', 'TWP')]
            if players:
                person_id = players[0]['id']
        except Exception:
            return 5.0

    if not person_id:
        return 5.0

    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'mlb_history.db')
    if not os.path.exists(db_path):
        return 5.0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ip FROM pitcher_logs
        WHERE pitcher_id = ? AND date < ? AND is_starter = 1
        ORDER BY date DESC LIMIT 10
    ''', (person_id, target_date))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return 5.0  # Default for rookies / no prior starts

    avg_ip = sum(r[0] for r in rows) / len(rows)
    return round(min(5.0, avg_ip), 2)

def get_historical_team_wrc(team_name: str, target_date: str, sport_id: int = 1) -> float:
    """
    Fetches point-in-time wRC+ proxy for a team strictly before target_date.
    Uses Team OPS normalized against an estimated league average.
    """
    team_id = TEAM_MAP.get(team_name)
    if not team_id:
        teams = statsapi.lookup_team(team_name, sportIds=sport_id)
        if not teams:
            return 100.0
        team_id = teams[0]['id']

    target_year = int(target_date.split('-')[0])
    start_date = f"{target_year}-03-20"
    
    t_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    end_date = (t_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=byDateRange&group=hitting&startDate={start_date}&endDate={end_date}"
        r = _session.get(url, timeout=10)
        data = r.json()
        
        splits = data.get('stats', [])
        if not splits:
            return 100.0
            
        stat = splits[0].get('splits', [])[0].get('stat', {})
        ops_str = stat.get('ops', '.720')
        ops = float(ops_str) if ops_str.startswith('.') else float(ops_str)
        if ops_str.startswith('.'):
            ops = float('0' + ops_str)
            
        league_ops = 0.720
        return round((ops / league_ops) * 100, 1)
        
    except Exception as e:
        print(f"Error fetching historical wRC+ for {team_name}: {e}")
        return 100.0

def get_historical_team_bullpen_fip(team_name, target_date, sport_id=1):
    """
    Returns historical Bullpen FIP by checking the roster, fetching byDateRange stats,
    and filtering for relief pitchers (GS < 3).
    """
    team_id = TEAM_MAP.get(team_name)
    if not team_id:
        teams = statsapi.lookup_team(team_name, sportIds=sport_id)
        if not teams:
            return 4.25
        team_id = teams[0]['id']
        
    current_season = int(target_date.split('-')[0])
    t_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    end_date_str = (t_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/Active?date={target_date}"
        r = _session.get(url, timeout=10)
        roster = r.json().get('roster', [])
        pitcher_ids = [p['person']['id'] for p in roster if p.get('position', {}).get('code') == '1']
    except Exception:
        pitcher_ids = []
        
    if not pitcher_ids:
        return 4.25
        
    relief_k = relief_bb = relief_hr = relief_ip = 0.0
    found_relievers = 0
    id_string = ','.join(str(pid) for pid in pitcher_ids)
    
    try:
        url = f"https://statsapi.mlb.com/api/v1/people?personIds={id_string}&hydrate=stats(group=[pitching],type=byDateRange,startDate={current_season}-01-01,endDate={end_date_str})"
        r = _session.get(url, timeout=10)
        raw = r.json()
        
        for person in raw.get('people', []):
            stats = {}
            for grp in person.get('stats', []):
                splits = grp.get('splits', [])
                if splits:
                    stats = splits[0].get('stat', {})
                    break
            
            if not stats: continue
                
            ip  = _parse_ip(stats.get('inningsPitched', '0'))
            gs  = int(stats.get('gamesStarted', 0) or 0)
            
            if ip < 1.0: continue
            
            if gs < 3:
                relief_ip  += ip
                relief_k   += int(stats.get('strikeOuts',  0) or 0)
                relief_bb  += int(stats.get('baseOnBalls', 0) or 0)
                hbp        = int(stats.get('hitBatsmen', 0) or 0)
                relief_bb  += hbp
                relief_hr  += int(stats.get('homeRuns',    0) or 0)
                found_relievers += 1
    except Exception:
        pass
        
    if found_relievers >= 3 and relief_ip >= 10.0:
        bullpen_fip = ((13 * relief_hr) + (3 * relief_bb) - (2 * relief_k)) / relief_ip + FIP_CONSTANT
        return round(max(2.5, min(7.5, bullpen_fip)), 2)
    
    return 4.25
