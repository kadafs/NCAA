import random
import numpy as np
from fetch_lineups import get_batter_pa_rates, get_pitcher_pa_modifiers, get_pitcher_hand
import statsapi

def adjust_batter_rates(batter_rates, pitcher_modifiers, batter_hand=None, pitcher_hand=None, tto=0, temp_scaler=1.0):
    """
    Adjusts a batter's raw outcome probabilities based on the pitcher's modifiers.
    Applies dynamic TTTO Platoon Fatigue dilution (pitcher loses control against opp-hand when tired/hot).
    """
    adjusted = {}
    
    # Apply modifiers to the specific outcomes
    adjusted['k'] = batter_rates.get('k', 0.22) * pitcher_modifiers.get('k', 1.0)
    adjusted['bb'] = batter_rates.get('bb', 0.08) * pitcher_modifiers.get('bb', 1.0)
    adjusted['hr'] = batter_rates.get('hr', 0.03) * pitcher_modifiers.get('hr', 1.0)
    
    # Pitcher's overall quality affects base hits
    hit_mod = pitcher_modifiers.get('hit_mod', 1.0)
    adjusted['single'] = batter_rates.get('single', 0.15) * hit_mod
    adjusted['double'] = batter_rates.get('double', 0.05) * hit_mod
    adjusted['triple'] = batter_rates.get('triple', 0.005) * hit_mod
    
    # Dynamic Platoon Fatigue Dilution
    # If the pitcher is fatigued (tto > 0), their disadvantage against opposite-handed batters widens
    if batter_hand and pitcher_hand and batter_hand != pitcher_hand and batter_hand != 'S':
        # tto=1 (2nd time) gives +3% base boost. tto=2 gives +6% base boost. Multiplied by heat.
        platoon_boost = 1.0 + (tto * 0.03 * temp_scaler)
        adjusted['bb'] *= platoon_boost
        adjusted['hr'] *= platoon_boost
        adjusted['single'] *= platoon_boost
    
    # Calculate the remaining probability as an out
    total_non_out = sum(adjusted.values())
    
    # Cap total non-out at 0.95 to ensure at least some outs
    if total_non_out >= 1.0:
        scale = 0.95 / total_non_out
        for k in adjusted:
            adjusted[k] *= scale
        adjusted['out_rate'] = 0.05
    else:
        adjusted['out_rate'] = 1.0 - total_non_out
        
    return adjusted

def apply_environmental_physics(batter_rates, park_factor, weather_ctx, batter_hand='R'):
    """
    Transforms environmental constants into rate scales.
    Protects the underlying event matrix from absolute float bloating.
    """
    adjusted = dict(batter_rates)
    
    # Defaults
    temp_modifier = 1.0
    wind_modifier = 1.0
    wind_lateral = None
    wind_mph = 0
    
    if weather_ctx and not weather_ctx.get('is_indoor'):
        temp = weather_ctx.get('temp', 72)
        wind_dir = weather_ctx.get('wind_dir', 'Calm')
        wind_mph = weather_ctx.get('wind_mph', 0)
        wind_lateral = weather_ctx.get('wind_lateral')
        
        # 1. Thermal Modifier: 70°F is neutral (1.0). Scales +/- 3.5% per 10 degrees.
        temp_modifier = 1.0 + ((temp - 70) / 10) * 0.035
        
        # 2. Wind Modifier: Linearly scales up to a locked physical limit at 15+ MPH
        if wind_dir == 'Out':
            wind_modifier = 1.0 + (min(wind_mph, 15) * 0.01)   # Max Cap: 1.15x
        elif wind_dir == 'In':
            wind_modifier = 1.0 - (min(wind_mph, 15) * 0.008)  # Max Penalty: 0.88x

    # 3. Apply the multiplicative rates to Home Runs
    final_hr_prob = adjusted.get('hr', 0) * park_factor * temp_modifier * wind_modifier
    
    # 4. Asymmetrical Crosswind Adjustment for HRs (Multiplicative)
    if wind_lateral and wind_mph >= 5:
        # Crosswind magnitude: up to ~5% modifier at 20+ mph
        cross_scale = 1.0 + min(wind_mph / 20.0, 1.0) * 0.05
        
        if batter_hand == 'L':
            if wind_lateral == 'L-R':  # tailwind for pulled ball
                final_hr_prob *= cross_scale
            elif wind_lateral == 'R-L': # headwind for pulled ball
                final_hr_prob /= cross_scale
        else:
            if wind_lateral == 'R-L':  # tailwind for pulled ball
                final_hr_prob *= cross_scale
            elif wind_lateral == 'L-R': # headwind for pulled ball
                final_hr_prob /= cross_scale
                
    adjusted['hr'] = max(0.0001, final_hr_prob)
    
    # 5. Apply partial scaling to doubles (50%) and triples (30%)
    double_scale = 1.0 + ((park_factor * temp_modifier * wind_modifier) - 1.0) * 0.5
    triple_scale = 1.0 + ((park_factor * temp_modifier) - 1.0) * 0.3 # wind helps less
    
    adjusted['double'] = max(0.0001, adjusted.get('double', 0) * double_scale)
    adjusted['triple'] = max(0.0001, adjusted.get('triple', 0) * triple_scale)

    # 6. Strict Structural Floor & Re-Normalization Sink
    total_non_out = sum(v for k, v in adjusted.items() if k != 'out_rate')
    adjusted['out_rate'] = max(0.0001, 1.0 - total_non_out)
    
    return adjusted

# Speed Tiers: 0=Sluggish, 1=Average, 2=Elite
RUNNER_SCORE_FROM_2ND_ON_SINGLE = np.array([
    [0.30, 0.40, 0.55], # 0: Sluggish
    [0.55, 0.60, 0.80], # 1: Average
    [0.75, 0.82, 0.95]  # 2: Elite
])

RUNNER_SCORE_FROM_1ST_ON_DOUBLE = np.array([
    [0.20, 0.18, 0.35], # 0: Sluggish
    [0.40, 0.35, 0.55], # 1: Average
    [0.55, 0.50, 0.70]  # 2: Elite
])

def create_cdf_array(adjusted_rates):
    """
    Converts a batter's adjusted rates dict into a 7-element NumPy CDF array:
    [out, k, bb, single, double, triple, hr]
    """
    probs = [
        adjusted_rates.get('out_rate', 0.0),
        adjusted_rates.get('k', 0.0),
        adjusted_rates.get('bb', 0.0),
        adjusted_rates.get('single', 0.0),
        adjusted_rates.get('double', 0.0),
        adjusted_rates.get('triple', 0.0),
        adjusted_rates.get('hr', 0.0)
    ]
    # Normalize just in case of tiny float drifts
    probs = np.array(probs)
    probs /= probs.sum()
    return np.cumsum(probs)

def simulate_half_inning_vectorized(active_games, lineup_states, batter_indices, outs, runs, base1, base2, base3, lineup_speed_tiers, tto_states):
    """
    Simulates plate appearances for all currently active games until all have 3 outs.
    Modifies arrays IN PLACE.
    
    active_games: boolean mask of shape (iterations,)
    lineup_states: list of CDF arrays [shape (9, 7)] for each TTTO state.
    batter_indices: int array of shape (iterations,)
    outs: int array of shape (iterations,)
    runs: int array of shape (iterations,)
    base1, base2, base3: int arrays of shape (iterations,) representing runner speed tiers (-1 if empty)
    lineup_speed_tiers: int array of shape (9,) for the active lineup.
    tto_states: int array of shape (iterations,) tracking TTTO penalty state for the pitcher.
    """
    lineup_length = len(lineup_speed_tiers)
    if lineup_length == 0: return
    
    stacked_lineups = np.stack(lineup_states) # shape (3, 9, 7)
    
    while np.any(active_games):
        num_active = np.count_nonzero(active_games)
        
        # 1. Fetch CDFs for the current batter in each active game
        active_tto = tto_states[active_games]
        active_batters = batter_indices[active_games]
        active_cdfs = stacked_lineups[active_tto, active_batters] # shape (num_active, 7)
        
        # 2. Roll random numbers and resolve events
        r = np.random.rand(num_active)
        events = (r[:, None] > active_cdfs).sum(axis=1) # 0=out, 1=k, 2=bb, 3=1b, 4=2b, 5=3b, 6=hr
        
        # 3. Apply events to states using subsets
        a_outs = outs[active_games]
        a_runs = runs[active_games]
        a_b1 = base1[active_games]
        a_b2 = base2[active_games]
        a_b3 = base3[active_games]
        batter_speeds = lineup_speed_tiers[active_batters]
        
        ev_out = (events == 0) | (events == 1)
        ev_bb  = (events == 2)
        ev_1b  = (events == 3)
        ev_2b  = (events == 4)
        ev_3b  = (events == 5)
        ev_hr  = (events == 6)
        
        if np.any(ev_out):
            a_outs[ev_out] += 1
            
        if np.any(ev_bb):
            bb_loaded = ev_bb & (a_b1 != -1) & (a_b2 != -1) & (a_b3 != -1)
            a_runs[bb_loaded] += 1
            a_b3[bb_loaded] = a_b2[bb_loaded]
            a_b2[bb_loaded] = a_b1[bb_loaded]
            a_b1[bb_loaded] = batter_speeds[bb_loaded]
            
            bb_12 = ev_bb & (a_b1 != -1) & (a_b2 != -1) & (a_b3 == -1)
            a_b3[bb_12] = a_b2[bb_12]
            a_b2[bb_12] = a_b1[bb_12]
            a_b1[bb_12] = batter_speeds[bb_12]
            
            bb_1 = ev_bb & (a_b1 != -1) & (a_b2 == -1)
            a_b2[bb_1] = a_b1[bb_1]
            a_b1[bb_1] = batter_speeds[bb_1]
            
            bb_empty = ev_bb & (a_b1 == -1)
            a_b1[bb_empty] = batter_speeds[bb_empty]
            
        if np.any(ev_1b):
            b3_scores = ev_1b & (a_b3 != -1)
            a_runs[b3_scores] += 1
            a_b3[ev_1b] = -1
            
            b2_exists = ev_1b & (a_b2 != -1)
            if np.any(b2_exists):
                speeds = a_b2[b2_exists]
                curr_outs = a_outs[b2_exists]
                thresholds = RUNNER_SCORE_FROM_2ND_ON_SINGLE[speeds, curr_outs]
                advances = np.random.rand(len(speeds)) <= thresholds
                
                b2_scores = np.zeros_like(b2_exists)
                b2_scores[b2_exists] = advances
                a_runs[b2_scores] += 1
                
                b2_holds = np.zeros_like(b2_exists)
                b2_holds[b2_exists] = ~advances
                a_b3[b2_holds] = a_b2[b2_holds]
                
            a_b2[ev_1b] = -1
            
            b1_exists = ev_1b & (a_b1 != -1)
            a_b2[b1_exists] = a_b1[b1_exists]
            a_b1[ev_1b] = batter_speeds[ev_1b]
            
        if np.any(ev_2b):
            b3_scores = ev_2b & (a_b3 != -1)
            a_runs[b3_scores] += 1
            a_b3[ev_2b] = -1
            
            b2_scores = ev_2b & (a_b2 != -1)
            a_runs[b2_scores] += 1
            a_b2[ev_2b] = -1
            
            b1_exists = ev_2b & (a_b1 != -1)
            if np.any(b1_exists):
                speeds = a_b1[b1_exists]
                curr_outs = a_outs[b1_exists]
                thresholds = RUNNER_SCORE_FROM_1ST_ON_DOUBLE[speeds, curr_outs]
                advances = np.random.rand(len(speeds)) <= thresholds
                
                b1_scores = np.zeros_like(b1_exists)
                b1_scores[b1_exists] = advances
                a_runs[b1_scores] += 1
                
                b1_holds = np.zeros_like(b1_exists)
                b1_holds[b1_exists] = ~advances
                a_b3[b1_holds] = a_b1[b1_holds]
                
            a_b1[ev_2b] = -1
            a_b2[ev_2b] = batter_speeds[ev_2b]
            
        if np.any(ev_3b):
            a_runs[ev_3b] += (a_b1[ev_3b] != -1).astype(int) + (a_b2[ev_3b] != -1).astype(int) + (a_b3[ev_3b] != -1).astype(int)
            a_b1[ev_3b] = -1
            a_b2[ev_3b] = -1
            a_b3[ev_3b] = batter_speeds[ev_3b]
            
        if np.any(ev_hr):
            a_runs[ev_hr] += (a_b1[ev_hr] != -1).astype(int) + (a_b2[ev_hr] != -1).astype(int) + (a_b3[ev_hr] != -1).astype(int) + 1
            a_b1[ev_hr] = -1
            a_b2[ev_hr] = -1
            a_b3[ev_hr] = -1
            
        # 4. Write modified slices back
        outs[active_games] = a_outs
        runs[active_games] = a_runs
        base1[active_games] = a_b1
        base2[active_games] = a_b2
        base3[active_games] = a_b3
        
        # Advance batter index
        batter_indices[active_games] = (batter_indices[active_games] + 1) % lineup_length
        
        # Recalculate mask (active_games is modified in place technically, but we're creating a new boolean array)
        active_games = outs < 3

def get_pitcher_id(pitcher_name, sport_id=1):
    if not pitcher_name or pitcher_name == 'TBD': return None
    players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
    if players: return players[0]['id']
    return None

def generate_generic_lineup(pitcher_hand: str = 'R') -> list:
    """
    Generates a platoon-aware generic 9-batter lineup.

    When the opposing pitcher is RHP, left-handed batters have a platoon
    advantage (+BB, +HR, +hits, -K). When the pitcher is LHP, right-handed
    batters benefit. The generic lineup models a typical MLB team's
    L/R mix: roughly 5-6 opposite-handed bats in a full lineup.

    Platoon adjustments (documented MLB split averages):
      LHB vs RHP (advantage):  BB+12%, K-8%,  HR+15%, Hits+8%
      RHB vs LHP (advantage):  BB+10%, K-7%,  HR+12%, Hits+7%
      Same-hand (disadvantage): BB-8%, K+10%, HR-10%, Hits-6%

    Slot weights (top-of-order boost, bottom-of-order penalty) unchanged.
    """
    # Proportion of the lineup that has the platoon ADVANTAGE
    # Typical MLB team stacks 5-6 opposite-handed bats vs any given SP
    if pitcher_hand == 'R':
        advantage_adj = {'bb': 1.12, 'k': 0.92, 'hr': 1.15,
                         'single': 1.08, 'double': 1.08, 'triple': 1.08}
        disadvantage_adj = {'bb': 0.92, 'k': 1.10, 'hr': 0.90,
                            'single': 0.94, 'double': 0.94, 'triple': 0.94}
        opp_hand = 'L'
    else:  # LHP on the mound
        advantage_adj = {'bb': 1.10, 'k': 0.93, 'hr': 1.12,
                         'single': 1.07, 'double': 1.07, 'triple': 1.07}
        disadvantage_adj = {'bb': 0.92, 'k': 1.10, 'hr': 0.90,
                            'single': 0.94, 'double': 0.94, 'triple': 0.94}
        opp_hand = 'R'

    # Realistic MLB league-average per-PA rates (2022-2025 MLB averages)
    # BB ~8.5%, K ~22%, HR ~3.0%, 1B ~15%, 2B ~4.8%, 3B ~0.5%
    # Non-out (true OBP excl K) = .085+.030+.150+.048+.005 = .318 → realistic
    base = {'k': 0.220, 'bb': 0.085, 'hr': 0.030, 'single': 0.150, 'double': 0.048, 'triple': 0.005}
    lineup = []

    for i in range(9):
        batter = dict(base)
        
        # Only top 3 slots get the opposite-hand (platoon advantage) assignment.
        # Real MLB lineups stack 3-4 platoon-favourable bats at the top of the order.
        # 3/9 = 33% opposite-hand → weighted lineup OBP ≈ 0.319, matching MLB average.
        batter['hand'] = opp_hand if i < 3 else pitcher_hand
        
        # Apply strict platoon advantage/disadvantage based on assigned hand
        adj = advantage_adj if batter['hand'] == opp_hand else disadvantage_adj
        
        for stat in ['bb', 'hr', 'single', 'double', 'triple']:
            batter[stat] *= adj[stat]
        batter['k'] *= adj['k']

        # Batting order slot boost/penalty — kept modest (1.08x) to avoid
        # over-inflation when compounded with platoon and pitcher FIP mods.
        if i < 4:    # Top of order (slots 1-4): better hitters
            for k in ['bb', 'hr', 'single', 'double', 'triple']:
                batter[k] *= 1.08
            batter['k'] *= 0.94
            batter['speed_tier'] = 2 if i < 3 else 1  # 2: Elite, 1: Average
        elif i > 5:  # Bottom of order (slots 7-9): weaker hitters
            for k in ['bb', 'hr', 'single', 'double', 'triple']:
                batter[k] *= 0.93
            batter['k'] *= 1.07
            batter['speed_tier'] = 0 if i > 6 else 1  # 0: Sluggish, 1: Average
        else:
            batter['speed_tier'] = 1  # 1: Average

        batter['out_rate'] = max(0.0001, 1.0 - sum(
            v for key, v in batter.items() if key not in ('out_rate', 'hand', 'speed_tier')
        ))
        lineup.append(batter)

    return lineup


# ---------------------------------------------------------------------------
# Rule 2: Time Through the Order (TTTO) Penalty
# ---------------------------------------------------------------------------
# Each time the batting lineup cycles back past the top (position 0),
# the starting pitcher degrades meaningfully:
#   - Hits and HRs become easier to give up
#   - Strikeouts become harder to generate
#
# Multipliers derived from published TTO research (Tango, Baumer, etc.)
TTTO_HIT_PENALTY  = {0: 1.00, 1: 1.12, 2: 1.22}   # hit_mod multiplier per TTO
TTTO_HR_PENALTY   = {0: 1.00, 1: 1.09, 2: 1.18}   # hr multiplier per TTO
TTTO_K_REDUCTION  = {0: 1.00, 1: 0.93, 2: 0.87}   # k multiplier per TTO (decreasing)


def apply_ttto_penalty(pitcher_mods: dict, times_through: int, temp_scaler: float = 1.0) -> dict:
    """
    Returns a new pitcher modifier dict degraded for the given TTO count.
    times_through=0: first time through (innings 1-2)
    times_through=1: second time through (innings 3-4)
    times_through=2: third time through (inning 5+)
    temp_scaler accelerates or decelerates fatigue based on weather.
    """
    tto = min(times_through, 2)
    degraded = dict(pitcher_mods)
    
    # Apply temp_scaler to the penalties (base 1.0, so we scale the part above 1.0)
    hit_pen = 1.0 + ((TTTO_HIT_PENALTY[tto] - 1.0) * temp_scaler)
    hr_pen  = 1.0 + ((TTTO_HR_PENALTY[tto] - 1.0) * temp_scaler)
    # K reduction (base 1.0, scale the reduction)
    k_red = 1.0 - ((1.0 - TTTO_K_REDUCTION[tto]) * temp_scaler)
    bb_pen = 1.0 + ((tto * 0.04) * temp_scaler)

    degraded['hit_mod'] = round(pitcher_mods.get('hit_mod', 1.0) * hit_pen, 4)
    degraded['hr']      = round(pitcher_mods.get('hr',       1.0) * hr_pen,  4)
    degraded['k']       = round(pitcher_mods.get('k',        1.0) * k_red,   4)
    degraded['bb']      = round(pitcher_mods.get('bb',       1.0) * bb_pen,  4)
    return degraded

def run_monte_carlo_f5(away_lineup_ids, home_lineup_ids,
                       away_pitcher_name, home_pitcher_name,
                       away_pitcher_fip, home_pitcher_fip,
                       iterations=2000, park_factor=1.0, weather_context=None, sport_id=1,
                       away_pitcher_hand=None, home_pitcher_hand=None):
    """
    Runs Monte Carlo simulation for the F5 innings.
    Returns expected runs, win probabilities, and total distribution.

    away_pitcher_hand / home_pitcher_hand: 'L' or 'R'.
    If None, fetched automatically from the API.
    """
    # 1. Fetch Pitcher Modifiers
    away_pitcher_id = get_pitcher_id(away_pitcher_name, sport_id)
    home_pitcher_id = get_pitcher_id(home_pitcher_name, sport_id)

    away_pitcher_mods = get_pitcher_pa_modifiers(away_pitcher_fip, away_pitcher_id)
    home_pitcher_mods = get_pitcher_pa_modifiers(home_pitcher_fip, home_pitcher_id)

    # Resolve pitcher handedness (used for generic lineup platoon logic)
    if away_pitcher_hand is None:
        away_pitcher_hand = get_pitcher_hand(away_pitcher_name, sport_id)
    if home_pitcher_hand is None:
        home_pitcher_hand = get_pitcher_hand(home_pitcher_name, sport_id)

    # 2. Fetch Batter Rates and Adjust
    # We now store RAW rates and adjust them dynamically inside the inning loop 
    # to perfectly simulate TTTO degradation.
    away_raw_lineup = []
    for pid in away_lineup_ids:
        raw = get_batter_pa_rates(pid)
        # Approximate batter hand: statsapi doesn't return hand in simple lineup lookup,
        # but we assume R for crosswind if unknown, or we could fetch it.
        # For performance, we assume 'R' if unknown, but ideally we'd pass it in.
        raw['hand'] = 'R' 
        raw['speed_tier'] = 1  # 1: Average
        away_raw_lineup.append(raw)

    home_raw_lineup = []
    for pid in home_lineup_ids:
        raw = get_batter_pa_rates(pid)
        raw['hand'] = 'R'
        raw['speed_tier'] = 1  # 1: Average
        home_raw_lineup.append(raw)

    # If lineups aren't posted, use platoon-aware generic lineup
    if not away_raw_lineup:
        generic = generate_generic_lineup(pitcher_hand=home_pitcher_hand)
        away_raw_lineup = generic
        away_is_generic = True
    else:
        away_is_generic = False

    if not home_raw_lineup:
        generic = generate_generic_lineup(pitcher_hand=away_pitcher_hand)
        home_raw_lineup = generic
        home_is_generic = True
    else:
        home_is_generic = False
        
    temp_scaler = weather_context.get('temp_fatigue_scaler', 1.0) if weather_context else 1.0

    # --- Pre-compute TTTO CDF Matrices ---
    away_lineup_states = []
    home_lineup_states = []
    
    for tto in range(3):
        away_inning_mods = apply_ttto_penalty(home_pitcher_mods, tto, temp_scaler)
        home_inning_mods = apply_ttto_penalty(away_pitcher_mods, tto, temp_scaler)
        
        a_cdf_matrix = []
        for b in away_raw_lineup:
            adj = adjust_batter_rates(b, away_inning_mods, batter_hand=b['hand'], pitcher_hand=home_pitcher_hand, tto=tto, temp_scaler=temp_scaler)
            adj = apply_environmental_physics(adj, park_factor, weather_context, batter_hand=b['hand'])
            a_cdf_matrix.append(create_cdf_array(adj))
        away_lineup_states.append(np.array(a_cdf_matrix))
        
        h_cdf_matrix = []
        for b in home_raw_lineup:
            adj = adjust_batter_rates(b, home_inning_mods, batter_hand=b['hand'], pitcher_hand=away_pitcher_hand, tto=tto, temp_scaler=temp_scaler)
            adj = apply_environmental_physics(adj, park_factor, weather_context, batter_hand=b['hand'])
            h_cdf_matrix.append(create_cdf_array(adj))
        home_lineup_states.append(np.array(h_cdf_matrix))
        
    away_speed_tiers = np.array([b['speed_tier'] for b in away_raw_lineup])
    home_speed_tiers = np.array([b['speed_tier'] for b in home_raw_lineup])

    # --- Vectorized Simulation Engine ---
    away_total_runs = np.zeros(iterations, dtype=np.int32)
    home_total_runs = np.zeros(iterations, dtype=np.int32)
    
    away_idx = np.zeros(iterations, dtype=np.int32)
    home_idx = np.zeros(iterations, dtype=np.int32)
    
    away_tto = np.zeros(iterations, dtype=np.int32)
    home_tto = np.zeros(iterations, dtype=np.int32)
    
    prev_away_idx = np.zeros(iterations, dtype=np.int32)
    prev_home_idx = np.zeros(iterations, dtype=np.int32)
    
    # Pre-allocate state arrays for the loop
    outs = np.zeros(iterations, dtype=np.int32)
    base1 = np.full(iterations, -1, dtype=np.int32)
    base2 = np.full(iterations, -1, dtype=np.int32)
    base3 = np.full(iterations, -1, dtype=np.int32)
    active_games = np.ones(iterations, dtype=bool)
    
    for inning in range(5):
        # Update TTO
        away_tto += (away_idx < prev_away_idx).astype(np.int32)
        home_tto += (home_idx < prev_home_idx).astype(np.int32)
        # Cap TTO at 2
        away_tto = np.minimum(away_tto, 2)
        home_tto = np.minimum(home_tto, 2)
        
        prev_away_idx[:] = away_idx
        prev_home_idx[:] = home_idx
        
        # Reset half inning states
        outs.fill(0)
        base1.fill(-1)
        base2.fill(-1)
        base3.fill(-1)
        active_games.fill(True)
        
        # Top of inning (Away)
        simulate_half_inning_vectorized(
            active_games, away_lineup_states, away_idx, outs, away_total_runs,
            base1, base2, base3, away_speed_tiers, home_tto
        )
        
        # Reset half inning states
        outs.fill(0)
        base1.fill(-1)
        base2.fill(-1)
        base3.fill(-1)
        active_games.fill(True)
        
        # Bottom of inning (Home)
        simulate_half_inning_vectorized(
            active_games, home_lineup_states, home_idx, outs, home_total_runs,
            base1, base2, base3, home_speed_tiers, away_tto
        )

    # --- Calculate Summary Statistics ---
    exp_away = np.mean(away_total_runs)
    exp_home = np.mean(home_total_runs)
    
    f5_totals = away_total_runs + home_total_runs
    
    away_wins = np.sum(away_total_runs > home_total_runs)
    home_wins = np.sum(home_total_runs > away_total_runs)
    ties = np.sum(away_total_runs == home_total_runs)
    
    return {
        'away_mc_runs': float(round(exp_away, 2)),
        'home_mc_runs': float(round(exp_home, 2)),
        'mc_total_runs': float(round(exp_away + exp_home, 2)),
        'away_win_prob': float(round(away_wins / iterations, 3)),
        'home_win_prob': float(round(home_wins / iterations, 3)),
        'tie_prob': float(round(ties / iterations, 3)),
        'under_3_5_prob': float(round(np.mean(f5_totals < 3.5), 3)),
        'under_4_5_prob': float(round(np.mean(f5_totals < 4.5), 3)),
        'under_5_5_prob': float(round(np.mean(f5_totals < 5.5), 3))
    }

if __name__ == '__main__':
    # Test MC Engine
    from fetch_lineups import get_lineup_for_game
    import datetime
    today = datetime.datetime.now().strftime('%m/%d/%Y')
    schedule = statsapi.schedule(date=today)
    if schedule:
        game = schedule[0]
        gid = game['game_id']
        away = game['away_name']
        home = game['home_name']
        ap = game.get('away_probable_pitcher', 'TBD')
        hp = game.get('home_probable_pitcher', 'TBD')
        
        print(f"Testing Monte Carlo for {away} vs {home}")
        lineups = get_lineup_for_game(gid)
        
        res = run_monte_carlo_f5(lineups['away'], lineups['home'], ap, hp, 4.00, 4.00, iterations=10000)
        print(res)
