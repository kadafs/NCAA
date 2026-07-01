from mlb_time import get_mlb_now
"""
fetch_lineups.py
Fetches today's confirmed batting lineups from the MLB StatsAPI.
Falls back gracefully when lineups haven't been posted yet.
"""
import statsapi
import os
import json
from defense_f5 import calculate_defensive_hit_modifier


def get_lineup_for_game(game_id):
    """
    Returns {'away': [player_id, ...], 'home': [player_id, ...]}
    in batting order (1-9). Returns empty lists if lineup not yet posted.
    """
    try:
        box = statsapi.boxscore_data(game_id)
        away_ids = box.get('away', {}).get('battingOrder', [])
        home_ids = box.get('home', {}).get('battingOrder', [])
        return {'away': away_ids, 'home': home_ids}
    except Exception:
        return {'away': [], 'home': []}


_batter_hand_cache = {}

_player_map = {}
_map_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'player_map.json')
if os.path.exists(_map_path):
    try:
        import json
        with open(_map_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for name, info in data.items():
                _player_map[str(info['id'])] = info
                _player_map[name] = info
    except Exception:
        pass

def get_batter_hand(player_id: int) -> str:
    """
    Returns 'L' or 'R' for a batter's bat side from the Stats API.

    Switch hitters ('S') are treated as 'R' for platoon modelling purposes
    (switch hitters have no platoon disadvantage, so the same-hand penalty
    in adjust_batter_rates() should not apply — 'R' is the safer neutral).
    Falls back to 'R' on any API error (league is ~70% RHB).

    This is the canonical implementation shared by both the pre-game MC engine
    and the live cache builder. live_cache._get_batter_hand() delegates here.
    """
    if player_id in _batter_hand_cache:
        return _batter_hand_cache[player_id]
        
    if str(player_id) in _player_map:
        code = _player_map[str(player_id)]['bat_side']
        return code if code in ('L', 'R') else 'R'
        
    import os, json, datetime
    today_str = get_mlb_now().date().isoformat()
    cache_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'batter_hand_{player_id}_{today_str}.json')
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                hand = json.load(f).get('hand')
                if hand:
                    _batter_hand_cache[player_id] = hand
                    return hand
        except Exception:
            pass
        
    try:
        data = statsapi.get('people', {'personIds': player_id})
        for p in data.get('people', []):
            code = p.get('batSide', {}).get('code', 'R')
            # 'S' = switch hitter — treated as 'R' (no platoon penalty applies)
            hand = code if code in ('L', 'R') else 'R'
            _batter_hand_cache[player_id] = hand
            
            try:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump({'hand': hand}, f)
            except Exception as e:
                print("ERROR SAVING BATTER CACHE:", e)
                
            return hand
    except Exception:
        pass
    
    _batter_hand_cache[player_id] = 'R'
    return 'R'


def get_pitcher_hand(pitcher_name: str, sport_id: int = 1) -> str:
    """
    Returns 'L' or 'R' for the pitcher's throwing hand.
    Defaults to 'R' (majority of MLB starters are RHP) if not found.
    """
    import unicodedata

    def _strip_accents(s: str) -> str:
        """Normalize accented characters to ASCII equivalents for fuzzy matching."""
        return ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        )

    if not pitcher_name or pitcher_name.strip().upper() == 'TBD':
        return 'R'

    # Check player_map first — try exact match then accent-stripped fallback
    if pitcher_name in _player_map:
        code = _player_map[pitcher_name].get('pitch_hand', '')
        if code:
            return code.upper()

    # Accent-stripped fallback for names like Rodón, Luzardo
    stripped_name = _strip_accents(pitcher_name)
    for key, info in _player_map.items():
        if isinstance(key, str) and _strip_accents(key) == stripped_name:
            code = info.get('pitch_hand', '')
            if code:
                return code.upper()

    # Live API fallback: lookup_player to get ID, then people endpoint for pitchHand
    try:
        results = statsapi.lookup_player(pitcher_name, sportId=sport_id)
        if not results:
            # Try accent-stripped name
            results = statsapi.lookup_player(stripped_name, sportId=sport_id)
        if results:
            player_id = results[0]['id']
            person_data = statsapi.get('people', {'personIds': player_id})
            for person in person_data.get('people', []):
                hand = person.get('pitchHand', {})
                if isinstance(hand, dict):
                    return hand.get('code', 'R').upper()
                elif hand:
                    return str(hand).upper()
    except Exception:
        pass
    return 'R'




def _fetch_recent_batter_rates(player_id, days=15):
    """
    Fetches a batter's hitting rates over the last `days` calendar days.
    Returns a dict of rates (same keys as LEAGUE_AVG) or None on failure / insufficient sample.
    Minimum 15 PA required to be used.
    """
    import datetime
    today = get_mlb_now().date()
    start_date = (today - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    try:
        raw = statsapi.get('people', {
            'personIds': player_id,
            'hydrate': f'stats(group=[hitting],type=byDateRange,startDate={start_date},endDate={end_date})'
        })
        stats = {}
        for person in raw.get('people', []):
            for grp in person.get('stats', []):
                splits = grp.get('splits', [])
                if splits:
                    stats = splits[0].get('stat', {})
                    break
            if stats:
                break

        pa = int(stats.get('plateAppearances', 0) or 0)
        if pa < 15:
            return None  # too small a sample

        bb  = int(stats.get('baseOnBalls', 0) or 0)
        k   = int(stats.get('strikeOuts',  0) or 0)
        hr  = int(stats.get('homeRuns',    0) or 0)
        h   = int(stats.get('hits',        0) or 0)
        dbl = int(stats.get('doubles',     0) or 0)
        trp = int(stats.get('triples',     0) or 0)
        sng = max(h - hr - dbl - trp, 0)

        return {
            'bb':     bb  / pa,
            'k':      k   / pa,
            'hr':     hr  / pa,
            'single': sng / pa,
            'double': dbl / pa,
            'triple': trp / pa,
        }
    except Exception:
        return None


def get_batter_pa_rates(player_id, pitcher_hand=None):
    """
    Returns a dict of plate appearance outcome rates for a batter,
    blended across 2024/2025/2026 seasons using the same weights as run_daily_f5.py.

    Keys: bb_rate, k_rate, hr_rate, single_rate, double_rate, triple_rate, out_rate
    All values are per-PA probabilities that sum to ~1.0.
    """
    import os, json, datetime
    today_str = get_mlb_now().date().isoformat()
    cache_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'batter_stats_{player_id}_{pitcher_hand}_{today_str}.json')
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # Monte Carlo uses historical data to determine true talent
    MC_WEIGHTS = {
        2026: 0.40,
        2025: 0.40,
        2024: 0.20,
    }
    CURRENT_SEASON = 2026
    # Below this PA threshold, the current season sample is regressed toward
    # the player's own prior-season baseline to prevent hot/cold streak noise.
    PA_STABILIZATION_THRESHOLD = 250

    LEAGUE_AVG = {
        'bb':     0.085,
        'k':      0.225,
        'hr':     0.030,
        'single': 0.150,
        'double': 0.048,
        'triple': 0.005,
        'iso':    0.160,
    }

    # --- Pass 1: Collect raw rates per season ---
    season_rates = {}   # season -> {'rates': {...}, 'pa': int}
    for season in MC_WEIGHTS:
        try:
            # Force correct split translations for batters vs pitchers
            if pitcher_hand and pitcher_hand.upper() in ('L', 'R'):
                # For hitting stats, 'vs Left pitcher' is 'vsL', 'vs Right pitcher' is 'vsR'
                sit_code = 'vsL' if pitcher_hand.upper() == 'L' else 'vsR'
                hydrate_str = f'stats(group=[hitting],type=statSplits,sitCodes={sit_code},season={season})'
            else:
                hydrate_str = f'stats(group=[hitting],type=season,season={season})'
                
            raw = statsapi.get('people', {
                'personIds': player_id,
                'hydrate':   hydrate_str
            })
            stats = {}
            for person in raw.get('people', []):
                for grp in person.get('stats', []):
                    splits = grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats:
                    break

            pa  = int(stats.get('plateAppearances', 0) or 0)
            if pa < 10:
                continue

            bb  = int(stats.get('baseOnBalls', 0) or 0)
            k   = int(stats.get('strikeOuts',  0) or 0)
            hr  = int(stats.get('homeRuns',    0) or 0)
            h   = int(stats.get('hits',        0) or 0)
            dbl = int(stats.get('doubles',     0) or 0)
            trp = int(stats.get('triples',     0) or 0)
            sng = h - hr - dbl - trp
            ab  = int(stats.get('atBats',      0) or 0)

            # ISO = SLG - AVG = (1B + 2B*2 + 3B*3 + HR*4)/AB - H/AB
            # Simplified: (dbl + 2*trp + 3*hr) / ab
            iso = (dbl + 2*trp + 3*hr) / ab if ab > 0 else 0.160

            season_rates[season] = {
                'pa': pa,
                'rates': {
                    'bb':     bb  / pa,
                    'k':      k   / pa,
                    'hr':     hr  / pa,
                    'single': max(sng, 0) / pa,
                    'double': dbl / pa,
                    'triple': trp / pa,
                    'iso':    iso,
                }
            }
        except Exception:
            continue

    # --- Pass 2: Build personal prior from prior seasons (2024 + 2025) ---
    prior_rates = None
    prior_pa_total = 0.0
    prior_seasons = [s for s in season_rates if s != CURRENT_SEASON]
    if prior_seasons:
        prior_weighted = {k: 0.0 for k in LEAGUE_AVG}
        prior_weight_sum = 0.0
        for s in prior_seasons:
            w = MC_WEIGHTS.get(s, 0.0)
            for metric in prior_weighted:
                prior_weighted[metric] += season_rates[s]['rates'][metric] * w
            prior_weight_sum += w
            prior_pa_total += season_rates[s]['pa']
        if prior_weight_sum > 0:
            prior_rates = {k: prior_weighted[k] / prior_weight_sum for k in prior_weighted}

    # --- Pass 3: Bayesian regression on current season if below PA threshold ---
    if CURRENT_SEASON in season_rates:
        cur = season_rates[CURRENT_SEASON]
        cur_pa = cur['pa']
        if cur_pa < PA_STABILIZATION_THRESHOLD:
            # Determine the regression anchor.
            # If the player has a personal prior (2024/2025), use it (credibility-weighted).
            # If they have NO prior data (rookie / no MLB history), regress toward LEAGUE_AVG.
            if prior_rates is not None:
                # Credibility Fix: if the prior itself is built from very few PAs (e.g., 51 PAs
                # across 2024+2025), it is statistically unreliable. We blend the prior toward
                # league average proportionally before using it as the regression anchor.
                # At prior_pa=150 → 50/50 blend. At prior_pa=0 → pure league avg. At prior_pa=300+ → trust prior.
                MIN_PRIOR_PA = 150
                prior_credibility = min(1.0, prior_pa_total / (prior_pa_total + MIN_PRIOR_PA))
                regression_target = {
                    metric: (prior_rates[metric] * prior_credibility) + (LEAGUE_AVG[metric] * (1.0 - prior_credibility))
                    for metric in LEAGUE_AVG
                }
            else:
                # No prior data at all (true rookie or player with no MLB history).
                # Regress directly toward league average to prevent tiny-sample inflation
                # (e.g., K=58% from 12 PAs, or HR=8% from a hot 20-PA stretch).
                regression_target = LEAGUE_AVG

            regressed = {}
            for metric in LEAGUE_AVG:
                raw_val   = cur['rates'][metric]
                prior_val = regression_target[metric]
                regressed[metric] = (
                    (raw_val * cur_pa) + (prior_val * PA_STABILIZATION_THRESHOLD)
                ) / (cur_pa + PA_STABILIZATION_THRESHOLD)
            season_rates[CURRENT_SEASON]['rates'] = regressed

    # --- Pass 4: Apply MC_WEIGHTS blend across all available seasons ---
    # PA-credibility weighting: a season with 11 PA should not count the same as one with 400 PA.
    # Each season's effective weight = its MC_WEIGHT × min(PA / PA_SATURATION, 1.0).
    # This is Marcel projection methodology — small samples get proportionally downweighted.
    PA_SATURATION = 250  # Full weight at 250+ PAs; smaller samples are downweighted
    weighted = {k: 0.0 for k in LEAGUE_AVG}
    total_weight = 0.0
    for season, weight in MC_WEIGHTS.items():
        if season not in season_rates:
            continue
        season_pa = season_rates[season]['pa']
        pa_credibility = min(1.0, season_pa / PA_SATURATION)
        effective_weight = weight * pa_credibility
        rates = season_rates[season]['rates']
        for k_name in weighted:
            weighted[k_name] += rates[k_name] * effective_weight
        total_weight += effective_weight

    if total_weight == 0:
        # No data — return league averages
        out = dict(LEAGUE_AVG)
        out['out_rate'] = 1.0 - sum(LEAGUE_AVG.values())
        return out

    # Rescale to actual weight collected
    result = {k: weighted[k] / total_weight for k in weighted}

    # ── 15-Day Rolling Form Blend ─────────────────────────────────────────────
    # Blend 30% last-15-day overall rates + 70% multi-season (split) blend.
    # Gated by >=15 PA in the 15-day window.
    recent_rates = _fetch_recent_batter_rates(player_id, days=15)
    if recent_rates is not None:
        for k in result:
            if k in recent_rates:
                result[k] = (recent_rates[k] * 0.30) + (result[k] * 0.70)

    result['out_rate'] = max(0.0, 1.0 - sum(v for key, v in result.items() if key != 'out_rate'))

    try:
        import os, json
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(result, f)
    except Exception:
        pass

    return result


def get_pitcher_pa_modifiers_xfip(pitcher_xfip, pitcher_player_id=None,
                                  defending_team=None, venue_name=None):
    """
    V6 Monte Carlo Pitcher Modifier Engine: Uses xFIP as a true proxy for 
    base-hit suppression, completely eliminating home run double-counting.
    
    Now overlays the Defensive Efficiency & Turf Surface modifier so that
    elite defenses on natural grass suppress the hit_mod, and poor defenses
    on artificial turf inflate it.

    modifiers: {'k': float, 'bb': float, 'hr': float, 'hit_mod': float}
    A modifier of 1.2 means the pitcher inflates that outcome by 20%.
    """
    # League averages as baseline
    LEAGUE_K_PER_9  = 8.8
    LEAGUE_BB_PER_9 = 3.1
    LEAGUE_HR_PER_9 = 1.2

    # 1. Use xFIP to scale base hits. (4.20 is the historical MLB xFIP baseline)
    # This cleanly isolates structural run prevention from home run luck.
    default_hit_mod = (pitcher_xfip / 4.20) ** 0.6 if pitcher_xfip else 1.0
    default_hit_mod = max(0.75, min(1.25, default_hit_mod))

    # 2. Overlay Defensive Efficiency & Turf Surface modifier
    if defending_team and venue_name and pitcher_player_id:
        defensive_scaler = calculate_defensive_hit_modifier(
            pitcher_player_id, defending_team, venue_name
        )
        default_hit_mod = round(max(0.70, min(1.30, default_hit_mod * defensive_scaler)), 4)

    default_profile = {'k': 1.0, 'bb': 1.0, 'hr': 1.0, 'hit_mod': default_hit_mod}

    if pitcher_player_id is None:
        return {'L': default_profile, 'R': default_profile}

    # Monte Carlo uses historical data to determine true talent
    MC_WEIGHTS = {
        2026: 0.40,
        2025: 0.40,
        2024: 0.20,
    }

    # 'L' = vs LHB, 'R' = vs RHB
    split_stats = {
        'L': {'k': 0.0, 'bb': 0.0, 'hr': 0.0, 'ip': 0.0, 'w': 0.0},
        'R': {'k': 0.0, 'bb': 0.0, 'hr': 0.0, 'ip': 0.0, 'w': 0.0}
    }

    # 1. Fetch exact splits
    for season, weight in MC_WEIGHTS.items():
        for hand, sit_code in [('L', 'vl'), ('R', 'vr')]:
            try:
                raw = statsapi.get('people', {
                    'personIds': pitcher_player_id,
                    'hydrate':   f'stats(group=[pitching],type=statSplits,sitCodes={sit_code},season={season})'
                })
                stats = {}
                for person in raw.get('people', []):
                    for grp in person.get('stats', []):
                        splits = grp.get('splits', [])
                        if splits:
                            stats = splits[0].get('stat', {})
                            break
                    if stats:
                        break

                ip_str = str(stats.get('inningsPitched', '0'))
                parts  = ip_str.split('.')
                ip     = float(parts[0]) + (float(parts[1]) / 3.0 if len(parts) > 1 else 0)
                
                if ip < 2:  # Minimum innings to bother tracking for this season/split
                    continue

                split_stats[hand]['k']  += int(stats.get('strikeOuts',  0) or 0) * weight
                split_stats[hand]['bb'] += int(stats.get('baseOnBalls', 0) or 0) * weight
                split_stats[hand]['hr'] += int(stats.get('homeRuns',    0) or 0) * weight
                split_stats[hand]['ip'] += ip * weight
                split_stats[hand]['w']  += weight
            except Exception:
                continue

    # 2. Fallback check: if we lack robust data for a split, fallback to global season totals
    # We do a one-time global aggregate fetch if needed
    needs_fallback = any(split_stats[h]['ip'] < 10 for h in ('L', 'R'))
    if needs_fallback:
        agg_stats = {'k': 0.0, 'bb': 0.0, 'hr': 0.0, 'ip': 0.0, 'w': 0.0}
        for season, weight in MC_WEIGHTS.items():
            try:
                raw = statsapi.get('people', {
                    'personIds': pitcher_player_id,
                    'hydrate':   f'stats(group=[pitching],type=season,season={season})'
                })
                stats = {}
                for person in raw.get('people', []):
                    for grp in person.get('stats', []):
                        splits = grp.get('splits', [])
                        if splits:
                            stats = splits[0].get('stat', {})
                            break
                    if stats:
                        break
                ip_str = str(stats.get('inningsPitched', '0'))
                parts  = ip_str.split('.')
                ip     = float(parts[0]) + (float(parts[1]) / 3.0 if len(parts) > 1 else 0)
                if ip < 1: continue
                agg_stats['k']  += int(stats.get('strikeOuts',  0) or 0) * weight
                agg_stats['bb'] += int(stats.get('baseOnBalls', 0) or 0) * weight
                agg_stats['hr'] += int(stats.get('homeRuns',    0) or 0) * weight
                agg_stats['ip'] += ip * weight
                agg_stats['w']  += weight
            except Exception:
                continue

        for hand in ('L', 'R'):
            if split_stats[hand]['ip'] < 10:
                split_stats[hand] = agg_stats

    # 3. Finalize ratios per hand
    pitcher_splits = {}
    for hand in ('L', 'R'):
        st = split_stats[hand]
        if st['ip'] == 0 or st['w'] == 0:
            pitcher_splits[hand] = dict(default_profile)
        else:
            p_k_9  = (st['k']  / st['ip']) * 9
            p_bb_9 = (st['bb'] / st['ip']) * 9
            p_hr_9 = (st['hr'] / st['ip']) * 9

            pitcher_splits[hand] = {
                'k':  max(0.5, min(1.8, p_k_9  / LEAGUE_K_PER_9)),
                'bb': max(0.5, min(2.0, p_bb_9 / LEAGUE_BB_PER_9)),
                'hr': max(0.5, min(2.5, p_hr_9 / LEAGUE_HR_PER_9)),
                'hit_mod': default_hit_mod
            }

    return pitcher_splits


if __name__ == '__main__':
    import datetime
    today = get_mlb_now().strftime('%m/%d/%Y')
    schedule = statsapi.schedule(date=today)
    if schedule:
        game = schedule[0]
        gid  = game['game_id']
        print(f"Testing lineups for game {gid}: {game['away_name']} @ {game['home_name']}")
        lineups = get_lineup_for_game(gid)
        print(f"  Away lineup IDs: {lineups['away'][:3]}...")
        print(f"  Home lineup IDs: {lineups['home'][:3]}...")
        if lineups['away']:
            pid = lineups['away'][0]
            rates = get_batter_pa_rates(pid, pitcher_hand=pitcher_hand)
            print(f"  Batter {pid} PA rates: {rates}")
