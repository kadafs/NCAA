"""
npb/fetch_metrics.py
Fetches pitcher and team offensive metrics for the NPB engine.

Data Strategy:
NPB is a highly pitcher-friendly environment.
League average FIP fallback: 3.50 (NPB average).
Team wRC+ proxy: Approximated from team run production relative to league average.
"""

from functools import lru_cache

# NPB league constants
NPB_LEAGUE_AVG_FIP      = 3.50
NPB_LEAGUE_AVG_WRC_PLUS = 100
NPB_BULLPEN_AVG_ERA     = 3.20
NPB_STARTER_AVG_IP      = 6.0  # NPB starters traditionally go deeper than MLB/KBO

# Team wRC+ proxy: based on offensive performance
NPB_TEAM_WRC_PROXY = {
    # Central League
    'Yakult Swallows':      108,
    'DeNA BayStars':        105,
    'Hanshin Tigers':       103,
    'Yomiuri Giants':       102,
    'Chunichi Dragons':     94,
    'Hiroshima Carp':       92,
    
    # Pacific League
    'SoftBank Hawks':       110,
    'Orix Buffaloes':       106,
    'Nippon-Ham Fighters':  104,
    'Lotte Marines':        98,
    'Rakuten Eagles':       96,
    'Seibu Lions':          85,
}

@lru_cache(maxsize=128)
def get_pitcher_fip(pitcher_name: str, sport_id: int = 1) -> float:
    """Returns FIP proxy for the given NPB pitcher. Falls back to league average."""
    # Without FanGraphs/B-Ref scraping available, we use league average
    # until a dedicated stats provider API is sourced.
    if not pitcher_name or pitcher_name == 'TBD':
        return NPB_LEAGUE_AVG_FIP
    
    # In a full production system, we would map the Japanese pitcher name
    # to a local database of NPB stats.
    return NPB_LEAGUE_AVG_FIP

@lru_cache(maxsize=32)
def get_pitcher_projected_ip(pitcher_name: str, sport_id: int = 1) -> float:
    return NPB_STARTER_AVG_IP

@lru_cache(maxsize=32)
def get_team_bullpen_fip(team_name: str, sport_id: int = 1) -> float:
    return NPB_BULLPEN_AVG_ERA

@lru_cache(maxsize=32)
def get_team_wrc_proxy(team_name: str, sport_id: int = 1) -> float:
    if team_name in NPB_TEAM_WRC_PROXY:
        return float(NPB_TEAM_WRC_PROXY[team_name])
        
    team_lower = team_name.lower()
    for name, wrc in NPB_TEAM_WRC_PROXY.items():
        if any(part in team_lower for part in name.lower().split() if len(part) > 3):
            return float(wrc)
            
    return float(NPB_LEAGUE_AVG_WRC_PLUS)
