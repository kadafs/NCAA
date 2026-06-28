import statsapi
import time
from monte_carlo_f5 import get_pitcher_id

def get_pitcher_advanced_metrics(pitcher_name, sport_id=1, player_id=None):
    """
    Fetches the advanced metrics for a given pitcher name.
    Returns K_Rate, BB_Rate, and HR_FB (approximated).
    """
    default_metrics = {'K_Rate': 0.22, 'BB_Rate': 0.08, 'HR_FB': 0.10}
    if sport_id != 1:
        return default_metrics
        
    try:
        pid = player_id if player_id else get_pitcher_id(pitcher_name)
        if not pid:
            return default_metrics
            
        # Try current season first
        raw = statsapi.get('people', {
            'personIds': pid,
            'hydrate': 'stats(group=[pitching],type=season,season=2026)'
        })
        
        stats = {}
        for p in raw.get('people', []):
            for g in p.get('stats', []):
                for s in g.get('splits', []):
                    stats = s.get('stat', {})
                    break
        
        # If no stats for 2026, fallback to 2025
        if not stats:
            raw = statsapi.get('people', {
                'personIds': pid,
                'hydrate': 'stats(group=[pitching],type=season,season=2025)'
            })
            for p in raw.get('people', []):
                for g in p.get('stats', []):
                    for s in g.get('splits', []):
                        stats = s.get('stat', {})
                        break
                        
        if not stats:
            return default_metrics

        bf = stats.get('battersFaced', 0)
        if bf == 0:
            return default_metrics
            
        k = stats.get('strikeOuts', 0)
        bb = stats.get('baseOnBalls', 0)
        hr = stats.get('homeRuns', 0)
        # Some pitchers might not have flyOuts, use airOuts or approx
        fb = stats.get('flyOuts', 0) or stats.get('airOuts', 0) or (bf * 0.25)
        
        return {
            'K_Rate': k / bf,
            'BB_Rate': bb / bf,
            'HR_FB': hr / max(1, fb)
        }
    except Exception as e:
        print(f"Error fetching advanced metrics for {pitcher_name}: {e}")
        return default_metrics
