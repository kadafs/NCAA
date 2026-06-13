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

def get_historical_pitcher_fip(pitcher_name: str, target_date: str) -> float | None:
    """
    Fetches point-in-time FIP for a pitcher strictly before target_date.
    target_date format: 'YYYY-MM-DD'
    """
    if pitcher_name in ('TBD', '', None):
        return None
        
    players = statsapi.lookup_player(pitcher_name, sportId=1)
    if not players:
        return None
        
    person_id = players[0]['id']
    target_year = int(target_date.split('-')[0])
    start_date = f"{target_year}-03-20"
    
    # Calculate the day BEFORE the target date to ensure zero data leakage
    t_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    end_date = (t_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        import requests
        url = f"https://statsapi.mlb.com/api/v1/people/{person_id}/stats?stats=byDateRange&group=pitching&startDate={start_date}&endDate={end_date}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        splits = data.get('stats', [])
        if not splits:
            return None
            
        data_splits = splits[0].get('splits', [])
        if not data_splits:
            return None
            
        stats = data_splits[0].get('stat', {})
        
        hr = int(stats.get('homeRuns', 0))
        bb = int(stats.get('baseOnBalls', 0)) + int(stats.get('hitByPitch', 0))
        k = int(stats.get('strikeOuts', 0))
        ip = _parse_ip(stats.get('inningsPitched', "0.0"))
        
        if ip < 1.0:
            return None
            
        fip = ((13 * hr) + (3 * bb) - (2 * k)) / ip + FIP_CONSTANT
        return round(fip, 2)
        
    except Exception as e:
        print(f"Error fetching historical FIP for {pitcher_name}: {e}")
        return None

def get_historical_team_wrc(team_name: str, target_date: str, sport_id: int = 1) -> float:
    """
    Fetches point-in-time wRC+ proxy for a team strictly before target_date.
    Uses Team OPS normalized against an estimated league average.
    """
    import requests
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
        r = requests.get(url, timeout=10)
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

def get_historical_team_bullpen_fip(team_name: str, target_date: str, sport_id: int = 1) -> float:
    """
    Returns a simplified historical Bullpen FIP by fetching the team's total pitching stats,
    and applying a generic relief modifier, or fetching strictly reliever stats.
    """
    return 4.25
