from mlb_time import get_mlb_now
import random
import numpy as np
from fetch_lineups import (
    get_batter_pa_rates, get_pitcher_pa_modifiers,
    get_batter_hand, get_pitcher_hand
)
from live_state import get_runner_speed_tier
from umpire_engine import apply_umpire_sabermetric_layer
import statsapi

# ---------------------------------------------------------------------------
# Calibration constant
# ---------------------------------------------------------------------------
# Mild global dampener to correct for slight MC OVER bias.
# Derived from season-to-date average: actual F5 / MC projected F5 ~ 0.97.
# Set to 1.0 to disable. Reassess monthly as season progresses.
MLB_F5_CALIBRATION = 0.97

# Offensive outcome keys affected by form/calibration adjustments
_OFFENSE_KEYS = ('bb', 'hr', 'single', 'double', 'triple')

def adjust_batter_rates(batter_rates, pitcher_modifiers, batter_hand=None, pitcher_hand=None, tto=0, temp_scaler=1.0, umpire_profile=None):
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
    # True baseline platoon advantages are now perfectly handled by API StatSplits.
    # This logic only applies an *additional* penalty when the pitcher is fatigued (tto > 0),
    # simulating how a tired pitcher's breaking ball flattens out against opposite-handed batters.
    if tto > 0 and batter_hand and pitcher_hand and batter_hand != pitcher_hand and batter_hand != 'S':
        # tto=1 (2nd time) gives +1.5% base boost. tto=2 gives +3% base boost. Multiplied by heat.
        platoon_boost = 1.0 + (tto * 0.015 * temp_scaler)
        adjusted['bb'] *= platoon_boost
        adjusted['hr'] *= platoon_boost
        adjusted['single'] *= platoon_boost
        
    # Safety Check: Enforce a strict Strikeout Floor (Trap 2 Fix)
    # Prevents simulated K-rates from dropping so low that it causes an unrealistic defensive meltdown
    min_k_floor = batter_rates.get('k', 0.22) * 0.70
    if adjusted['k'] < min_k_floor:
        adjusted['k'] = min_k_floor
    
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
    wind_mph = 0.0
    wind_dir = "None"
    wind_lateral = None
    
    if weather_ctx:
        # 1. Enforce the Dome/Roof Constraint
        if weather_ctx.get('is_indoor'):
            wind_mph = 0.0
            wind_dir = "None"
        else:
            temp = weather_ctx.get('temp', 72)
            wind_dir = weather_ctx.get('wind_dir', 'Calm')
            wind_mph = float(weather_ctx.get('wind_mph', 0))
            wind_lateral = weather_ctx.get('wind_lateral')
            
            # 1b. Thermal Modifier: 70°F is neutral (1.0). Scales +/- 1.5% per 10 degrees. (Dampened)
            temp_modifier = 1.0 + ((temp - 70) / 10) * 0.015

    # 2. Shift to Non-Linear Physics Scaling (Quadratic-Leaning Power Scale)
    hr_wind_modifier = 1.0
    
    if wind_mph > 0.0 and wind_dir not in ("None", "Calm", "Indoor"):
        # This prevents over-correcting minor breezes while capturing blasts. (Dampened)
        base_effect = (wind_mph**1.2) * 0.003

        # 3. Apply Directional Matrices
        if wind_dir == 'Out':
            hr_wind_modifier = min(1.10, 1.0 + base_effect)  # Capped at +10%
        elif wind_dir == 'In':
            hr_wind_modifier = max(0.90, 1.0 - (base_effect * 0.85))
        
        # 4. Asymmetrical Crosswind Physics Matrix
        if wind_lateral == 'L-R' or wind_dir == 'L-R':
            if batter_hand == 'L':  # Lefties pull with the wind vector
                hr_wind_modifier += (base_effect * 0.4)
            elif batter_hand == 'R': # Righties hit a crosswind pushing balls foul
                hr_wind_modifier -= (base_effect * 0.3)
                
        elif wind_lateral == 'R-L' or wind_dir == 'R-L':
            if batter_hand == 'R':  # Righties pull with the wind vector
                hr_wind_modifier += (base_effect * 0.4)
            elif batter_hand == 'L': # Lefties hit a crosswind pushing balls foul
                hr_wind_modifier -= (base_effect * 0.3)

    # Force pure compounding multiplication to eliminate model divergence vs grade_f5.py
    # HR: compound all three environmental factors (temp * wind * park)
    final_hr_scalar = temp_modifier * hr_wind_modifier * park_factor
    adjusted['hr'] = max(0.0001, adjusted.get('hr', 0) * final_hr_scalar)

    # 5. Apply the scaling downward through the extra-base carry matrix and BABIP (Singles)
    # Scale secondary contact metrics symmetrically using compound roots
    double_scale = temp_modifier * max(1.0, park_factor) ** 0.5
    triple_scale = temp_modifier * max(1.0, park_factor) ** 0.3
    single_scale = max(1.0, park_factor) ** 0.6 * temp_modifier ** 0.3

    # Walks and Strikeouts: derive from combined compound factor for consistency
    total_env_factor = temp_modifier * hr_wind_modifier * park_factor
    bb_scale = 1.0 + ((total_env_factor - 1.0) * 0.2)
    k_scale  = 1.0 - ((total_env_factor - 1.0) * 0.15)

    adjusted['double'] = max(0.0001, adjusted.get('double', 0) * double_scale)
    adjusted['triple'] = max(0.0001, adjusted.get('triple', 0) * triple_scale)
    adjusted['single'] = max(0.0001, adjusted.get('single', 0) * single_scale)
    adjusted['bb'] = max(0.0001, adjusted.get('bb', 0) * bb_scale)
    adjusted['k'] = max(0.0001, adjusted.get('k', 0) * k_scale)

    # 6. Strict Structural Floor & Re-Normalization Sink
    total_non_out = sum(v for k, v in adjusted.items() if k != 'out_rate')
    if total_non_out >= 0.95:
        scale = 0.95 / total_non_out
        for k in adjusted:
            if k != 'out_rate':
                adjusted[k] *= scale
        adjusted['out_rate'] = 0.05
    else:
        adjusted['out_rate'] = 1.0 - total_non_out
    
    return adjusted

# Speed Tiers: 0=Sluggish, 1=Average, 2=Elite
RUNNER_SCORE_FROM_2ND_ON_SINGLE = np.array([
    [0.25, 0.35, 0.50], # 0: Sluggish
    [0.50, 0.55, 0.75], # 1: Average
    [0.65, 0.70, 0.85]  # 2: Elite
])

RUNNER_SCORE_FROM_1ST_ON_DOUBLE = np.array([
    [0.15, 0.15, 0.30], # 0: Sluggish
    [0.30, 0.30, 0.45], # 1: Average
    [0.45, 0.40, 0.60]  # 2: Elite
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
    Simulates plate appearances for all currently active games using high-performance
    direct-parent memory index arrays. Eliminates all intermediate masked array copies
    to prevent NumPy boolean-mask slice-copy leakage and base-clearing ordering bugs.

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
    if lineup_length == 0:
        return

    stacked_lineups = np.stack(lineup_states)  # Shape (3, 9, 7)

    while np.any(active_games):
        # 1. Isolate game indices that are actively playing (< 3 outs)
        global_active_idx = np.where(active_games)[0]

        active_tto = tto_states[global_active_idx]
        active_batters = batter_indices[global_active_idx]
        active_cdfs = stacked_lineups[active_tto, active_batters]  # shape (num_active, 7)

        # 2. Roll random variables across the active dimension
        r = np.random.rand(len(global_active_idx))
        events = (r[:, None] > active_cdfs).sum(axis=1)  # 0=out, 1=k, 2=bb, 3=1b, 4=2b, 5=3b, 6=hr

        # 3. Create sub-event boolean masks relative to the active slice
        ev_out = (events == 0) | (events == 1)
        ev_bb  = (events == 2)
        ev_1b  = (events == 3)
        ev_2b  = (events == 4)
        ev_3b  = (events == 5)
        ev_hr  = (events == 6)

        batter_speeds = lineup_speed_tiers[active_batters]

        # --- RULE A: OUTS RESOLUTION (Direct parent-array manipulation) ---
        if np.any(ev_out):
            outs[global_active_idx[ev_out]] += 1

        # --- RULE B: WALKS RESOLUTION (Reverse chronological shift prevents overwrite) ---
        if np.any(ev_bb):
            idx = global_active_idx[ev_bb]

            # Runs score only if bases are fully loaded
            bb_loaded = (base1[idx] != -1) & (base2[idx] != -1) & (base3[idx] != -1)
            runs[idx[bb_loaded]] += 1

            # Step backward through basepaths to prevent state overwriting
            base3[idx] = np.where((base1[idx] != -1) & (base2[idx] != -1), base2[idx], base3[idx])
            base2[idx] = np.where(base1[idx] != -1, base1[idx], base2[idx])
            base1[idx] = batter_speeds[ev_bb]

        # --- RULE C: SINGLES RESOLUTION (Chronological isolation, no blanket clears) ---
        if np.any(ev_1b):
            idx = global_active_idx[ev_1b]

            # Anyone on 3B scores automatically
            runs[idx[base3[idx] != -1]] += 1
            base3[idx] = -1  # 3B cleared; will be re-populated by 2B runner if they hold

            # Evaluate runner on 2B advancement
            b2_mask = base2[idx] != -1
            if np.any(b2_mask):
                b2_idx = idx[b2_mask]
                speeds = base2[b2_idx]
                curr_outs = outs[b2_idx]
                thresholds = RUNNER_SCORE_FROM_2ND_ON_SINGLE[speeds, curr_outs]
                advances = np.random.rand(len(b2_idx)) <= thresholds
                runs[b2_idx[advances]] += 1
                base3[b2_idx[~advances]] = base2[b2_idx[~advances]]  # holds at 3rd

            # Advance runner on 1B to 2B safely, isolated before 2B is cleared
            base2[idx] = np.where(base1[idx] != -1, base1[idx], -1)
            base1[idx] = batter_speeds[ev_1b]

        # --- RULE D: DOUBLES RESOLUTION ---
        if np.any(ev_2b):
            idx = global_active_idx[ev_2b]

            # Runners on 2B and 3B score automatically
            runs[idx[base3[idx] != -1]] += 1
            runs[idx[base2[idx] != -1]] += 1
            base3[idx] = -1
            base2[idx] = -1

            # Evaluate runner on 1B advancement
            b1_mask = base1[idx] != -1
            if np.any(b1_mask):
                b1_idx = idx[b1_mask]
                speeds = base1[b1_idx]
                curr_outs = outs[b1_idx]
                thresholds = RUNNER_SCORE_FROM_1ST_ON_DOUBLE[speeds, curr_outs]
                advances = np.random.rand(len(b1_idx)) <= thresholds
                runs[b1_idx[advances]] += 1
                base3[b1_idx[~advances]] = base1[b1_idx[~advances]]  # holds at 3rd

            base1[idx] = -1
            base2[idx] = batter_speeds[ev_2b]

        # --- RULE E: TRIPLES RESOLUTION ---
        if np.any(ev_3b):
            idx = global_active_idx[ev_3b]
            runs[idx] += ((base1[idx] != -1).astype(np.int32) +
                          (base2[idx] != -1).astype(np.int32) +
                          (base3[idx] != -1).astype(np.int32))
            base1[idx] = -1
            base2[idx] = -1
            base3[idx] = batter_speeds[ev_3b]

        # --- RULE F: HOME RUNS RESOLUTION ---
        if np.any(ev_hr):
            idx = global_active_idx[ev_hr]
            runs[idx] += ((base1[idx] != -1).astype(np.int32) +
                          (base2[idx] != -1).astype(np.int32) +
                          (base3[idx] != -1).astype(np.int32) + 1)
            base1[idx] = -1
            base2[idx] = -1
            base3[idx] = -1

        # 4. Cycle batting lineups forward and recalculate mask directly on parent memory
        batter_indices[active_games] = (batter_indices[active_games] + 1) % lineup_length
        active_games &= (outs < 3)

def get_pitcher_id(pitcher_name, sport_id=1):
    if not pitcher_name or pitcher_name == 'TBD': return None
    players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
    if players: return players[0]['id']
    return None

def generate_generic_lineup(pitcher_hand: str = 'R') -> list:
    """
    Generates a platoon-aware generic 9-batter lineup using league-average
    per-PA rates. Does NOT scale by team wRC+ — team offensive quality is
    captured exclusively by the Top-Down model to avoid double-counting.

    When the opposing pitcher is RHP, left-handed batters have a platoon
    advantage (+BB, +HR, +hits, -K). When the pitcher is LHP, right-handed
    batters benefit. The generic lineup models a typical MLB team's
    L/R mix: roughly 5-6 opposite-handed bats in a full lineup.

    Platoon adjustments (documented MLB split averages):
      LHB vs RHP (advantage):  BB+12%, K-8%,  HR+15%, Hits+8%
      RHB vs LHP (advantage):  BB+10%, K-7%,  HR+12%, Hits+7%
      Same-hand (disadvantage): BB-8%, K+10%, HR-10%, Hits-6%

    Slot boosts/penalties reflect real MLB lineup construction:
      Batters 1-4 (top of order): ×1.08 on all positive outcomes, K×0.94
      Batters 7-9 (bottom of order): ×0.93 on all positive outcomes, K×1.07
    """
    # Platoon advantage/disadvantage magnitudes match published MLB split averages.
    # These are intentionally NOT toned down — team quality is handled by the
    # Top-Down model, not here. Reducing them here caused under-projection.
    if pitcher_hand == 'R':
        advantage_adj    = {'bb': 1.12, 'k': 0.92, 'hr': 1.15,
                            'single': 1.08, 'double': 1.08, 'triple': 1.08}
        disadvantage_adj = {'bb': 0.92, 'k': 1.10, 'hr': 0.90,
                            'single': 0.94, 'double': 0.94, 'triple': 0.94}
        opp_hand = 'L'
    else:  # LHP on the mound
        advantage_adj    = {'bb': 1.10, 'k': 0.93, 'hr': 1.12,
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
        batter['hand'] = opp_hand if i < 3 else pitcher_hand

        # Apply platoon advantage/disadvantage based on assigned hand vs pitcher hand
        adj = advantage_adj if batter['hand'] == opp_hand else disadvantage_adj
        for stat in ['bb', 'hr', 'single', 'double', 'triple']:
            batter[stat] *= adj[stat]
        batter['k'] *= adj['k']

        # Slot boost/penalty: reflects that better hitters bat at the top of the order.
        # These magnitudes were validated against real confirmed lineup projections.
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
            batter['speed_tier'] = 1  # 1: Average (slots 5-6)

        # NOTE: No wRC+ scaling here. Team offensive quality is accounted for
        # by the Top-Down model (grade_matchup). Scaling here caused double-
        # counting and large divergences vs confirmed lineup projections.

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

# ---------------------------------------------------------------------------
# Bullpen Integration
# ---------------------------------------------------------------------------

_LEAGUE_FIP     = 4.30
_BP_BASE_K      = 0.225
_BP_BASE_BB     = 0.082
_BP_BASE_HR     = 0.030
_BP_BASE_SINGLE = 0.145
_BP_BASE_DOUBLE = 0.040
_BP_BASE_TRIPLE = 0.004

_FIP_K_SENSITIVITY      = -0.012
_FIP_BB_SENSITIVITY     =  0.008
_FIP_HR_SENSITIVITY     =  0.005
_FIP_SINGLE_SENSITIVITY =  0.010
_FIP_DOUBLE_SENSITIVITY =  0.003
_FIP_TRIPLE_SENSITIVITY =  0.001

def fip_to_bullpen_pa_rates(fip: float) -> dict:
    fip = max(2.80, min(6.50, fip))
    delta = fip - _LEAGUE_FIP

    k      = max(0.10, _BP_BASE_K      + (delta * _FIP_K_SENSITIVITY))
    bb     = max(0.02, _BP_BASE_BB     + (delta * _FIP_BB_SENSITIVITY))
    hr     = max(0.01, _BP_BASE_HR     + (delta * _FIP_HR_SENSITIVITY))
    single = max(0.05, _BP_BASE_SINGLE + (delta * _FIP_SINGLE_SENSITIVITY))
    double = max(0.01, _BP_BASE_DOUBLE + (delta * _FIP_DOUBLE_SENSITIVITY))
    triple = max(0.00, _BP_BASE_TRIPLE + (delta * _FIP_TRIPLE_SENSITIVITY))

    total = k + bb + hr + single + double + triple
    if total > 0.95:
        scale = 0.95 / total
        k *= scale; bb *= scale; hr *= scale
        single *= scale; double *= scale; triple *= scale
        out_rate = 0.05
    else:
        out_rate = max(0.0001, 1.0 - total)

    return {
        'bb': bb, 'k': k, 'hr': hr, 'single': single, 'double': double,
        'triple': triple, 'out_rate': out_rate, 'hand': 'R', 'speed_tier': 1,
    }

def _build_bullpen_lineup_states(
    raw_lineup: list,
    opposing_bp_fip: float,
    park_factor: float = 1.0,
    weather_context: dict = None,
    umpire_profile: dict = None,
    is_home: bool = False,
) -> list:
    bp_rates = fip_to_bullpen_pa_rates(opposing_bp_fip)
    
    def _bp_to_mods(bp: dict) -> dict:
        return {
            'hit_mod': bp['single'] / _BP_BASE_SINGLE,
            'hr': bp['hr'] / _BP_BASE_HR,
            'k': bp['k'] / _BP_BASE_K,
            'bb': bp['bb'] / _BP_BASE_BB,
        }
    bp_mods = _bp_to_mods(bp_rates)
    cdf_matrix = []
    
    _HFA_KEYS = ('single', 'double', 'triple', 'hr', 'bb')
    _AWAY_SCALE = 2.0 - HOME_ADVANTAGE_FACTOR
    
    for b in raw_lineup:
        b_adj = apply_umpire_sabermetric_layer(dict(b), umpire_profile)
        if is_home:
            for key in _HFA_KEYS:
                if key in b_adj: b_adj[key] *= HOME_ADVANTAGE_FACTOR
        else:
            for key in _HFA_KEYS:
                if key in b_adj: b_adj[key] *= _AWAY_SCALE
                
        adj = adjust_batter_rates(b_adj, bp_mods, batter_hand=b.get('hand', 'R'), pitcher_hand='R', tto=0)
        adj = apply_environmental_physics(adj, park_factor, weather_context, batter_hand=b.get('hand', 'R'))
        cdf_matrix.append(create_cdf_array(adj))
    return [np.array(cdf_matrix)]

# Home field advantage: home batters score ~3% more runs on average league-wide
# Applied as a uniform lift to all positive offensive outcomes for home lineup
HOME_ADVANTAGE_FACTOR = 1.03


def apply_ttto_penalty(pitcher_mods: dict, times_through: int, temp_scaler: float = 1.0) -> dict:
    """
    Safely applies TTTO penalties across a dual-keyed dictionary 
    without causing in-place reference mutations.
    """
    tto = min(times_through, 2)
    
    # Apply temp_scaler to the penalties (base 1.0, so we scale the part above 1.0)
    hit_pen = 1.0 + ((TTTO_HIT_PENALTY[tto] - 1.0) * temp_scaler)
    hr_pen  = 1.0 + ((TTTO_HR_PENALTY[tto] - 1.0) * temp_scaler)
    # K reduction (base 1.0, scale the reduction)
    k_red = 1.0 - ((1.0 - TTTO_K_REDUCTION[tto]) * temp_scaler)
    bb_pen = 1.0 + ((tto * 0.04) * temp_scaler)

    return {
        hand: {
            'hit_mod': round(metrics.get('hit_mod', 1.0) * hit_pen, 4),
            'hr':      round(metrics.get('hr',       1.0) * hr_pen,  4),
            'k':       round(metrics.get('k',        1.0) * k_red,   4),
            'bb':      round(metrics.get('bb',       1.0) * bb_pen,  4)
        }
        for hand, metrics in pitcher_mods.items()
    }

def run_monte_carlo_f5(
    away_lineup_ids: list,
    home_lineup_ids: list,
    away_pitcher_name: str,
    home_pitcher_name: str,
    away_pitcher_fip: float,
    home_pitcher_fip: float,
    iterations: int = 10000,
    park_factor: float = 1.0,
    weather_context: dict = None,
    sport_id: int = 1,
    away_pitcher_hand: str = 'R',
    home_pitcher_hand: str = 'R',
    umpire_profile: dict = None,
    away_wrc: float = 100.0,
    home_wrc: float = 100.0,
    away_bp_fip: float = None,
    home_bp_fip: float = None,
    away_projected_ip: float = 5.0,
    home_projected_ip: float = 5.0,
) -> dict:
    """
    Runs Monte Carlo simulation for the F5 innings.
    Returns expected runs, win probabilities, and total distribution.

    away_pitcher_hand / home_pitcher_hand: 'L' or 'R'.
    If None, fetched automatically from the API.
    umpire_profile: dict from umpire_engine.load_umpire_profile().
    If None, no umpire adjustment is applied.
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
    # ── Audit Fix #6 & #7: Real handedness + real speed tiers ───────────────
    # Previously both were hardcoded: hand='R', speed_tier=1.
    # This disabled platoon splits and runner advancement for confirmed lineups.
    # Both are now resolved per player from the Stats API (with session caching).
    # API calls are batched once per player per session — no per-iteration overhead.
    away_raw_lineup = []
    for pid in away_lineup_ids:
        raw = get_batter_pa_rates(pid, pitcher_hand=home_pitcher_hand)
        raw['hand']       = get_batter_hand(int(pid))         # 'L', 'R' (switch→'R')
        raw['speed_tier'] = get_runner_speed_tier(int(pid))   # 0=Sluggish,1=Avg,2=Elite
        # Umpire Layer: applied to raw talent rates BEFORE fatigue/environment
        raw = apply_umpire_sabermetric_layer(raw, umpire_profile)
        away_raw_lineup.append(raw)

    home_raw_lineup = []
    for pid in home_lineup_ids:
        raw = get_batter_pa_rates(pid, pitcher_hand=away_pitcher_hand)
        raw['hand']       = get_batter_hand(int(pid))
        raw['speed_tier'] = get_runner_speed_tier(int(pid))
        # Umpire Layer: applied to raw talent rates BEFORE fatigue/environment
        raw = apply_umpire_sabermetric_layer(raw, umpire_profile)
        home_raw_lineup.append(raw)

    # If lineups aren't posted, use platoon-aware league-average generic lineup.
    # The umpire layer is NOT applied to generic batters (statistical constructs,
    # not real players with individual tendencies).
    # wRC+ scaling IS now applied: differentiates team offensive quality without
    # double-counting the Top-Down model (which handles pitcher-level suppression).
    # Dampened square-root scaling keeps extremes in check: √(wRC+/100).
    _WRC_KEYS = ('bb', 'hr', 'single', 'double', 'triple')
    if not away_raw_lineup:
        away_raw_lineup = generate_generic_lineup(pitcher_hand=home_pitcher_hand)
        if away_wrc and away_wrc != 100.0:
            wrc_scale = (away_wrc / 100.0) ** 0.5
            for b in away_raw_lineup:
                for k in _WRC_KEYS:
                    b[k] *= wrc_scale
                b['out_rate'] = max(0.0001, 1.0 - sum(
                    v for key, v in b.items() if key not in ('out_rate', 'hand', 'speed_tier')))
        away_is_generic = True
    else:
        away_is_generic = False

    if not home_raw_lineup:
        home_raw_lineup = generate_generic_lineup(pitcher_hand=away_pitcher_hand)
        if home_wrc and home_wrc != 100.0:
            wrc_scale = (home_wrc / 100.0) ** 0.5
            for b in home_raw_lineup:
                for k in _WRC_KEYS:
                    b[k] *= wrc_scale
                b['out_rate'] = max(0.0001, 1.0 - sum(
                    v for key, v in b.items() if key not in ('out_rate', 'hand', 'speed_tier')))
        home_is_generic = True
    else:
        home_is_generic = False

    # ── Calibration ─────────────────────────────────────────
    # Applied AFTER wRC+ scaling, BEFORE TTTO pre-computation.
    # Global calibration constant to correct for MC's slight OVER bias.
    if MLB_F5_CALIBRATION != 1.0:
        for b in away_raw_lineup:
            for k in _OFFENSE_KEYS:
                if k in b:
                    b[k] *= MLB_F5_CALIBRATION
            b['out_rate'] = max(0.0001, 1.0 - sum(
                v for key, v in b.items() if key not in ('out_rate', 'hand', 'speed_tier')))

        for b in home_raw_lineup:
            for k in _OFFENSE_KEYS:
                if k in b:
                    b[k] *= MLB_F5_CALIBRATION
            b['out_rate'] = max(0.0001, 1.0 - sum(
                v for key, v in b.items() if key not in ('out_rate', 'hand', 'speed_tier')))
    # ─────────────────────────────────────────────────────────────────────────

    temp_scaler = weather_context.get('temp_fatigue_scaler', 1.0) if weather_context else 1.0

    # --- Pre-compute TTTO CDF Matrices ---
    away_lineup_states = []
    home_lineup_states = []
    
    # HFA input scaling keys: only offensive contact/walk outcomes, NOT strikeouts.
    # Applying at input level keeps k-rate ratios intact through the existing normalization.
    _HFA_KEYS = ('single', 'double', 'triple', 'hr', 'bb')
    _AWAY_SCALE = 2.0 - HOME_ADVANTAGE_FACTOR  # 0.97 — symmetric suppression

    for tto in range(3):
        away_inning_mods = apply_ttto_penalty(home_pitcher_mods, tto, temp_scaler)
        home_inning_mods = apply_ttto_penalty(away_pitcher_mods, tto, temp_scaler)
        
        a_cdf_matrix = []
        for b in away_raw_lineup:
            if b.get('hand', 'R') == 'S':
                pitcher_mod_hand = 'R' if home_pitcher_hand == 'L' else 'L'
            else:
                pitcher_mod_hand = b.get('hand', 'R')
            current_pitcher_mods = away_inning_mods.get(pitcher_mod_hand, away_inning_mods.get('R'))  # Away batters face HOME pitcher (away_inning_mods = home SP + TTTO)

            # Scale away batter input rates down symmetrically (0.97x) before normalization
            b_scaled = dict(b)
            for key in _HFA_KEYS:
                if key in b_scaled:
                    b_scaled[key] = b_scaled[key] * _AWAY_SCALE
            adj = adjust_batter_rates(b_scaled, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=home_pitcher_hand, tto=tto, temp_scaler=temp_scaler)
            adj = apply_environmental_physics(adj, park_factor, weather_context, batter_hand=b['hand'])
            a_cdf_matrix.append(create_cdf_array(adj))
        away_lineup_states.append(np.array(a_cdf_matrix))
        
        h_cdf_matrix = []
        for b in home_raw_lineup:
            if b.get('hand', 'R') == 'S':
                pitcher_mod_hand = 'R' if away_pitcher_hand == 'L' else 'L'
            else:
                pitcher_mod_hand = b.get('hand', 'R')
            current_pitcher_mods = home_inning_mods.get(pitcher_mod_hand, home_inning_mods.get('R'))  # Home batters face AWAY pitcher (home_inning_mods = away SP + TTTO)

            # Scale home batter input rates up (1.03x) BEFORE adjust_batter_rates().
            # This lets the existing out_rate normalization proportionally shrink ALL
            # outcomes including k, preserving strikeout ratios correctly.
            b_scaled = dict(b)
            for key in _HFA_KEYS:
                if key in b_scaled:
                    b_scaled[key] = b_scaled[key] * HOME_ADVANTAGE_FACTOR
            adj = adjust_batter_rates(b_scaled, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=away_pitcher_hand, tto=tto, temp_scaler=temp_scaler)
            adj = apply_environmental_physics(adj, park_factor, weather_context, batter_hand=b['hand'])
            h_cdf_matrix.append(create_cdf_array(adj))
        home_lineup_states.append(np.array(h_cdf_matrix))

    if away_bp_fip is not None and home_bp_fip is not None:
        away_bp_states = _build_bullpen_lineup_states(
            away_raw_lineup, home_bp_fip, park_factor, weather_context, umpire_profile, is_home=False
        )
        home_bp_states = _build_bullpen_lineup_states(
            home_raw_lineup, away_bp_fip, park_factor, weather_context, umpire_profile, is_home=True
        )
    else:
        away_bp_states = None
        home_bp_states = None
        
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
        # Check if starters have exited based on projected IP
        use_away_bp = (away_bp_states is not None) and ((inning + 1) > home_projected_ip)
        use_home_bp = (home_bp_states is not None) and ((inning + 1) > away_projected_ip)
        
        current_away_states = away_bp_states if use_away_bp else away_lineup_states
        current_home_states = home_bp_states if use_home_bp else home_lineup_states

        # Update TTO only if facing starter
        if not use_home_bp:
            away_tto += (away_idx < prev_away_idx).astype(np.int32)
            away_tto = np.minimum(away_tto, 2)
        else:
            away_tto.fill(0)
            
        if not use_away_bp:
            home_tto += (home_idx < prev_home_idx).astype(np.int32)
            home_tto = np.minimum(home_tto, 2)
        else:
            home_tto.fill(0)
        
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
            active_games, current_away_states, away_idx, outs, away_total_runs,
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
            active_games, current_home_states, home_idx, outs, home_total_runs,
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
    today = get_mlb_now().strftime('%m/%d/%Y')
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
