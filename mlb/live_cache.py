from mlb_time import get_mlb_now
"""
live_cache.py
=============
Morning Collision Cache builder for the LF5 engine.

At 10:00 AM daily (or on demand), this module computes the raw, unadjusted
interaction matrix for every potential hitter-pitcher matchup on the slate
(the "Vacuum Matrix"). 

It saves this state locally to disk using numpy's compressed .npz format,
allowing the LF5 live engine to load it into memory and execute simulations
in sub-second time without hitting external APIs for player stats during play.
"""

import os
import datetime
import numpy as np
import statsapi

# Import dependencies from our pre-game engine
from fetch_lineups import (
    get_lineup_for_game,
    get_pitcher_pa_modifiers,
    get_pitcher_hand
)
from monte_carlo_f5 import (
    generate_generic_lineup,
    apply_ttto_penalty,
    adjust_batter_rates,
    apply_environmental_physics,
    create_cdf_array
)
from weather_f5 import get_weather_modifier
from live_modifiers import MOP_UP_FIP_PENALTY

# Cache storage directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')


def _get_mop_up_pitcher_mods(pitcher_mods: dict) -> dict:
    """
    Returns a degraded pitcher modifier dict for the low-tier mop-up reliever proxy.
    This simulates the scenario where a starter exits early and the elite bullpen
    is unavailable (Scenario D).
    """
    # MOP_UP_FIP_PENALTY is roughly +1.25 FIP, which equates to a hit_mod bump
    # Let's approximate the penalty by directly inflating the existing mods
    return {
        hand: {
            'hit_mod': min(1.30, metrics.get('hit_mod', 1.0) * 1.15),
            'k':       max(0.50, metrics.get('k', 1.0) * 0.85),
            'bb':      min(1.50, metrics.get('bb', 1.0) * 1.15),
            'hr':      min(1.50, metrics.get('hr', 1.0) * 1.15)
        }
        for hand, metrics in pitcher_mods.items()
    }


def build_morning_cache(sport_id: int = 1, date_str: str = None) -> dict:
    """
    Builds the complete collision cache for the entire slate.
    
    Returns
    -------
    dict:
        The full nested cache dictionary keyed by game_id.
    """
    if not date_str:
        date_str = (get_mlb_now() - datetime.timedelta(hours=6)).strftime("%m/%d/%Y")
        
    print(f"Building LF5 Morning Cache for {date_str} (sportId={sport_id})...")
    schedule = statsapi.schedule(sportId=sport_id, date=date_str)
    
    if not schedule:
        print("  No games found on schedule.")
        return {}
        
    # We don't need get_probable_starters anymore; we just iterate schedule
    
    cache = {}
    
    for game in schedule:
        gid = game['game_id']
        away_team = game['away_name']
        home_team = game['home_name']
        venue     = game.get('venue_name', 'Unknown')
        
        away_abbr = game.get('away_file_code', away_team[:3].upper())
        home_abbr = game.get('home_file_code', home_team[:3].upper())
        
        print(f"  Processing {away_team} @ {home_team} (ID: {gid})")
        
        park_factor = 1.0 
        weather_ctx = get_weather_modifier(venue, away_abbr, home_abbr)
        temp_scaler = weather_ctx.get('temp_fatigue_scaler', 1.0)
        
        # 2. Pitcher Data
        away_p_name = game.get('away_probable_pitcher', 'TBD')
        home_p_name = game.get('home_probable_pitcher', 'TBD')
        
        away_p_hand = get_pitcher_hand(away_p_name, sport_id)
        home_p_hand = get_pitcher_hand(home_p_name, sport_id)
        
        away_p_id = _get_pitcher_id(away_p_name, sport_id)
        home_p_id = _get_pitcher_id(home_p_name, sport_id)
        
        away_p_fip = _get_pitcher_fip(away_p_id)
        home_p_fip = _get_pitcher_fip(home_p_id)
        
        away_p_mods = get_pitcher_pa_modifiers(away_p_fip, away_p_id, sport_id=sport_id)
        home_p_mods = get_pitcher_pa_modifiers(home_p_fip, home_p_id, sport_id=sport_id)
        
        away_mop_up_mods = _get_mop_up_pitcher_mods(away_p_mods)
        home_mop_up_mods = _get_mop_up_pitcher_mods(home_p_mods)
        
        # 3. Batter Data
        # In the morning, lineups may not be posted. We use get_lineup_for_game 
        # but fall back to the generated generic lineup.
        # Since we just need the raw dicts, we mimic what monte_carlo_f5 does.
        lineup_ids = get_lineup_for_game(gid)
        
        away_raw_lineup = _build_raw_lineup(lineup_ids['away'], home_p_hand)
        home_raw_lineup = _build_raw_lineup(lineup_ids['home'], away_p_hand)
        
        away_speed_tiers  = np.array([b['speed_tier'] for b in away_raw_lineup], dtype=np.int32)
        home_speed_tiers  = np.array([b['speed_tier'] for b in home_raw_lineup], dtype=np.int32)
        away_batter_hands = [b.get('hand', 'R') for b in away_raw_lineup]   # list of 9 'L'/'R'
        home_batter_hands = [b.get('hand', 'R') for b in home_raw_lineup]
        
        # 4. Construct TTTO CDF Matrices
        away_lineup_states = []
        home_lineup_states = []
        
        for tto in range(3):
            # Away batters face Home pitcher
            home_inning_mods = apply_ttto_penalty(home_p_mods, tto, temp_scaler)
            a_cdf_matrix = []
            for b in away_raw_lineup:
                if b.get('hand', 'R') == 'S':
                    pitcher_mod_hand = 'R' if home_p_hand == 'L' else 'L'
                else:
                    pitcher_mod_hand = b.get('hand', 'R')
                current_pitcher_mods = home_inning_mods.get(pitcher_mod_hand, home_inning_mods.get('R'))

                adj = adjust_batter_rates(b, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=home_p_hand, tto=tto, temp_scaler=temp_scaler)
                adj = apply_environmental_physics(adj, park_factor, weather_ctx, batter_hand=b['hand'])
                a_cdf_matrix.append(create_cdf_array(adj))
            away_lineup_states.append(np.array(a_cdf_matrix))
            
            # Home batters face Away pitcher
            away_inning_mods = apply_ttto_penalty(away_p_mods, tto, temp_scaler)
            h_cdf_matrix = []
            for b in home_raw_lineup:
                if b.get('hand', 'R') == 'S':
                    pitcher_mod_hand = 'R' if away_p_hand == 'L' else 'L'
                else:
                    pitcher_mod_hand = b.get('hand', 'R')
                current_pitcher_mods = away_inning_mods.get(pitcher_mod_hand, away_inning_mods.get('R'))

                adj = adjust_batter_rates(b, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=away_p_hand, tto=tto, temp_scaler=temp_scaler)
                adj = apply_environmental_physics(adj, park_factor, weather_ctx, batter_hand=b['hand'])
                h_cdf_matrix.append(create_cdf_array(adj))
            home_lineup_states.append(np.array(h_cdf_matrix))
            
        # 5. Construct Bullpen Proxy CDF Matrices (Mop-Up)
        # Assumes TTO = 0 (relievers entering fresh)
        a_bullpen_matrix = []
        for b in away_raw_lineup:
            if b.get('hand', 'R') == 'S':
                pitcher_mod_hand = 'R' if home_p_hand == 'L' else 'L'
            else:
                pitcher_mod_hand = b.get('hand', 'R')
            current_pitcher_mods = home_mop_up_mods.get(pitcher_mod_hand, home_mop_up_mods.get('R'))

            adj = adjust_batter_rates(b, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=home_p_hand, tto=0, temp_scaler=temp_scaler)
            adj = apply_environmental_physics(adj, park_factor, weather_ctx, batter_hand=b['hand'])
            a_bullpen_matrix.append(create_cdf_array(adj))
            
        h_bullpen_matrix = []
        for b in home_raw_lineup:
            if b.get('hand', 'R') == 'S':
                pitcher_mod_hand = 'R' if away_p_hand == 'L' else 'L'
            else:
                pitcher_mod_hand = b.get('hand', 'R')
            current_pitcher_mods = away_mop_up_mods.get(pitcher_mod_hand, away_mop_up_mods.get('R'))

            adj = adjust_batter_rates(b, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=away_p_hand, tto=0, temp_scaler=temp_scaler)
            adj = apply_environmental_physics(adj, park_factor, weather_ctx, batter_hand=b['hand'])
            h_bullpen_matrix.append(create_cdf_array(adj))
            
        # Store in cache dict
        cache[str(gid)] = {
            'away_lineup_states': np.stack(away_lineup_states), # shape (3, 9, 7)
            'home_lineup_states': np.stack(home_lineup_states), # shape (3, 9, 7)
            'away_bullpen_cdf':   np.array(a_bullpen_matrix),   # shape (9, 7)
            'home_bullpen_cdf':   np.array(h_bullpen_matrix),   # shape (9, 7)
            'away_speed_tiers':   away_speed_tiers,
            'home_speed_tiers':   home_speed_tiers,
            'away_batter_hands':  away_batter_hands,            # list[str] 'L'/'R' per slot
            'home_batter_hands':  home_batter_hands,
            'away_pitcher_hand':  away_p_hand,
            'home_pitcher_hand':  home_p_hand,
            'park_factor':        park_factor,
            'morning_weather':    weather_ctx,
            'away_team_name':     away_team,
            'home_team_name':     home_team,
        }
        
    print(f"Successfully cached {len(cache)} games.")
    return cache


def save_cache(cache: dict, date_str: str = None) -> str:
    """
    Serializes the cache to an .npz file.
    Returns the file path.
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        
    if date_str is None:
        date_str = get_mlb_now().strftime("%Y-%m-%d")
    else:
        # Convert mm/dd/yyyy to yyyy-mm-dd for filesystem
        try:
            d = datetime.datetime.strptime(date_str, "%m/%d/%Y")
            date_str = d.strftime("%Y-%m-%d")
        except:
            pass
            
    filepath = os.path.join(CACHE_DIR, f"lf5_cache_{date_str}.npz")
    
    # np.savez expects kwargs, we'll serialize the cache dict into arrays
    # Since our cache has nested dicts per game, we flatten the keys:
    # "12345_away_lineup_states": np.array(...)
    # "12345_morning_weather": np.array(...) [using object arrays for dicts]
    
    flat_data = {}
    for gid, game_data in cache.items():
        for key, value in game_data.items():
            flat_key = f"{gid}_{key}"
            if isinstance(value, dict) or isinstance(value, str) or isinstance(value, float):
                # Wrap scalars/dicts in an object array so numpy can save it
                flat_data[flat_key] = np.array(value, dtype=object)
            else:
                # Numpy arrays (states, speed tiers, etc)
                flat_data[flat_key] = value
                
    np.savez_compressed(filepath, **flat_data)
    print(f"Saved LF5 cache to {filepath}")
    return filepath


def load_cache(filepath: str) -> dict | None:
    """
    Deserializes an .npz file back into the nested cache dict.
    """
    if not os.path.exists(filepath):
        print(f"Cache file not found: {filepath}")
        return None
        
    try:
        with np.load(filepath, allow_pickle=True) as data:
            cache = {}
            for flat_key in data.files:
                # flat_key format: "12345_away_lineup_states"
                parts = flat_key.split('_', 1)
                if len(parts) != 2: continue
                gid, key = parts[0], parts[1]
                
                if gid not in cache:
                    cache[gid] = {}
                    
                val = data[flat_key]
                # Unwrap object arrays back to their native python types
                if val.dtype == object:
                    cache[gid][key] = val.item()
                else:
                    cache[gid][key] = val
                    
            return cache
    except Exception as e:
        print(f"Error loading cache {filepath}: {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pitcher_id(pitcher_name: str, sport_id: int = 1) -> int | None:
    if not pitcher_name or pitcher_name == 'TBD': return None
    try:
        players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
        if players: return players[0]['id']
    except:
        pass
    return None

def _get_pitcher_fip(pitcher_id: int | None) -> float:
    if not pitcher_id: return 4.20
    try:
        data = statsapi.get('people', {'personIds': pitcher_id, 'hydrate': 'stats(group=[pitching],type=season,season=2026)'})
        for p in data.get('people', []):
            for g in p.get('stats', []):
                for s in g.get('splits', []):
                    st = s.get('stat', {})
                    ip_str = str(st.get('inningsPitched', '0'))
                    parts = ip_str.split('.')
                    ip = float(parts[0]) + (float(parts[1]) / 3.0 if len(parts) > 1 else 0)
                    if ip < 1: continue
                    hr = int(st.get('homeRuns', 0))
                    bb = int(st.get('baseOnBalls', 0))
                    hbp = int(st.get('hitBatsmen', 0))
                    k = int(st.get('strikeOuts', 0))
                    return ((13 * hr) + (3 * (bb + hbp)) - (2 * k)) / ip + 3.20
    except Exception:
        pass
    return 4.20

def _build_raw_lineup(lineup_ids: list, opp_pitcher_hand: str, sport_id: int = 1) -> list:
    """
    Fetches real PA rates if IDs exist, else returns generic platoon-aware lineup.
    Also resolves real batter handedness from the Stats API when IDs are available.
    """
    from fetch_lineups import get_batter_pa_rates
    
    if not lineup_ids:
        return generate_generic_lineup(pitcher_hand=opp_pitcher_hand)
        
    raw_lineup = []
    for pid in lineup_ids:
        raw = get_batter_pa_rates(pid, sport_id=sport_id)
        raw['hand'] = _get_batter_hand(pid)   # Real handedness, fallback 'R'
        
        from live_state import get_runner_speed_tier
        raw['speed_tier'] = get_runner_speed_tier(pid)
        
        raw_lineup.append(raw)
        
    return raw_lineup


def _get_batter_hand(player_id: int) -> str:
    """Delegates to the canonical fetch_lineups.get_batter_hand()."""
    from fetch_lineups import get_batter_hand
    return get_batter_hand(player_id)


if __name__ == '__main__':
    # Test morning cache build
    print("Testing LF5 Morning Cache Builder...")
    cache = build_morning_cache()
    if cache:
        path = save_cache(cache)
        loaded = load_cache(path)
        if loaded:
            print(f"Successfully loaded {len(loaded)} games from cache.")
            first_key = list(loaded.keys())[0]
            print(f"Sample game ({first_key}):")
            print(f"  Away lineup shape: {loaded[first_key]['away_lineup_states'].shape}")
            print(f"  Speed tiers: {loaded[first_key]['away_speed_tiers']}")
