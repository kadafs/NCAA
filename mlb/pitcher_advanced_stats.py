import statsapi
import time
from monte_carlo_f5 import get_pitcher_id

# League-average defaults (used when data unavailable)
_DEFAULT_FB_PCT = 0.33   # average fly-ball rate
_DEFAULT_GB_PCT = 0.45   # average ground-ball rate
_DEFAULT_K_RATE = 0.22
_DEFAULT_BB_RATE = 0.08
_DEFAULT_HR_FB  = 0.10

def get_pitcher_advanced_metrics(pitcher_name, sport_id=1, player_id=None):
    """
    Fetches advanced metrics for a given pitcher.

    Returns
    -------
    dict with keys:
      K_Rate  : strikeout rate (K / BF)
      BB_Rate : walk rate (BB / BF)
      HR_FB   : home-run-per-fly-ball rate
      FB_pct  : fly-ball percentage (airOuts / total batted-ball outs)
      GB_pct  : ground-ball percentage (groundOuts / total batted-ball outs)

    FB_pct and GB_pct are the primary inputs for the Effective Park Factor
    calculation in env_confidence.py — they determine how park-sensitive
    this pitcher actually is (FB pitchers are fully park-sensitive;
    GB/K pitchers are mostly park-immune).
    """
    default_metrics = {
        'K_Rate':  _DEFAULT_K_RATE,
        'BB_Rate': _DEFAULT_BB_RATE,
        'HR_FB':   _DEFAULT_HR_FB,
        'FB_pct':  _DEFAULT_FB_PCT,
        'GB_pct':  _DEFAULT_GB_PCT,
    }
    try:
        pid = player_id if player_id else get_pitcher_id(pitcher_name, sport_id=sport_id)
        if not pid:
            return default_metrics

        def _fetch_stats(season):
            raw = statsapi.get('people', {
                'personIds': pid,
                'hydrate': f'stats(group=[pitching],type=season,season={season},sportId={sport_id})'
            })
            for p in raw.get('people', []):
                for g in p.get('stats', []):
                    for s in g.get('splits', []):
                        return s.get('stat', {})
            return {}

        stats = _fetch_stats(2026)
        if not stats:
            stats = _fetch_stats(2025)
        if not stats:
            return default_metrics

        bf = stats.get('battersFaced', 0)
        if bf == 0:
            return default_metrics

        k  = stats.get('strikeOuts', 0)
        bb = stats.get('baseOnBalls', 0)
        hr = stats.get('homeRuns', 0)

        # Batted-ball profile: airOuts (fly balls + pop-ups) and groundOuts
        air_outs    = stats.get('airOuts', 0) or stats.get('flyOuts', 0)
        ground_outs = stats.get('groundOuts', 0)
        total_bip_outs = air_outs + ground_outs

        if total_bip_outs > 0:
            fb_pct = air_outs    / total_bip_outs
            gb_pct = ground_outs / total_bip_outs
        else:
            fb_pct = _DEFAULT_FB_PCT
            gb_pct = _DEFAULT_GB_PCT

        fb = air_outs or (bf * _DEFAULT_FB_PCT)

        return {
            'K_Rate':  k  / bf,
            'BB_Rate': bb / bf,
            'HR_FB':   hr / max(1, fb),
            'FB_pct':  round(fb_pct, 4),
            'GB_pct':  round(gb_pct, 4),
        }

    except Exception as e:
        print(f"Error fetching advanced metrics for {pitcher_name}: {e}")
        return default_metrics
