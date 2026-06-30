from mlb_time import get_mlb_now
import random
import numpy as np
from fetch_lineups import (
    get_batter_pa_rates,
    get_batter_hand, get_pitcher_hand
)
from fetch_pitcher_batted_ball import fetch_and_profile_pitcher
from defense_f5 import calculate_defensive_hit_modifier
from live_state import get_runner_speed_tier
from umpire_engine import apply_umpire_sabermetric_layer
import statsapi

# ---------------------------------------------------------------------------
# Calibration constant
# ---------------------------------------------------------------------------
# Global calibration dampener.
# Set to 1.0 after the four structural bugs (fly-ball pool leak, inverted TTO,
# vanishing basepath runners, platoon double-count) were resolved 2026-06-30.
# The model now aligns natively with top-down SIERA targets without dampening.
# Restore a non-1.0 value only if a new systematic bias is measured over 50+ games.
MLB_F5_CALIBRATION = 1.0

# Offensive outcome keys affected by form/calibration adjustments
_OFFENSE_KEYS = ('bb', 'hr', 'single', 'double', 'triple')

# Global League Environment Baselines (Update annually based on run environment)
LEAGUE_HR_FB = 0.125
LEAGUE_GB_BABIP = 0.240
LEAGUE_LD_BABIP = 0.680
LEAGUE_OFFB_BABIP = 0.150 # Outfield Fly Balls that do NOT go over the fence

def log_odds_blend(pitcher_rate: float, batter_rate: float, league_rate: float) -> float:
    """Combines pitcher and batter rates against league baseline using Log-Odds formulation."""
    pitcher_rate = max(0.001, min(0.999, pitcher_rate))
    batter_rate = max(0.001, min(0.999, batter_rate))
    league_rate = max(0.001, min(0.999, league_rate))
    
    p_odds = pitcher_rate / (1 - pitcher_rate)
    b_odds = batter_rate / (1 - batter_rate)
    l_odds = league_rate / (1 - league_rate)
    
    combined_odds = (p_odds * b_odds) / l_odds
    return combined_odds / (1 + combined_odds)

def adjust_batter_rates(batter: dict, pitcher: dict, batter_hand=None, pitcher_hand=None, tto=0, temp_scaler=1.0, umpire_profile=None, defense_factor=1.0) -> dict:
    """
    Executes a mathematically tight 3-Tier SIERA/xFIP Hybrid Monte Carlo plate appearance simulation.
    Removes the structural probability leaks in Tier 2 and Tier 3.
    defense_factor: Multiplier for BABIP adjustments (e.g., 0.95 represents elite defense).
    """
    if pitcher is None:
        pitcher = {}
        
    pitcher_bb_rate = pitcher.get('bb_rate', 0.085)
    pitcher_k_rate = pitcher.get('k_rate', 0.225)
    pitcher_gb_rate = pitcher.get('gb_rate', 0.43)
    pitcher_ld_rate = pitcher.get('ld_rate', 0.25)
    pitcher_iffb_rate = pitcher.get('iffb_rate', 0.07)
    pitcher_offb_rate = pitcher.get('offb_rate', 0.25)
    pitcher_hr_fb_rate = pitcher.get('hr_fb_rate', 0.125)
    
    # -------------------------------------------------------------
    # TIER 1: The Plate Appearance Core Outcome
    # -------------------------------------------------------------
    # Isolate TTO modifications cleanly to prevent double-counting platoon adjustments.
    # These are applied to the BATTER's innate rates before log-odds blending with the pitcher.
    b_k = batter.get('k', 0.22)
    b_bb = batter.get('bb', 0.08)
    if tto > 0 and batter_hand and pitcher_hand and batter_hand != pitcher_hand and batter_hand != 'S':
        platoon_boost = 1.0 + (tto * 0.015 * temp_scaler)
        b_bb *= platoon_boost
        b_k *= (1.0 - (tto * 0.01 * temp_scaler))

    # Log-Odds Blending
    prob_bb = log_odds_blend(pitcher_bb_rate, b_bb, 0.085)
    prob_k = log_odds_blend(pitcher_k_rate, b_k, 0.225)
    
    # Safety Check: Enforce a strict Strikeout Floor
    min_k_floor = b_k * 0.70
    if prob_k < min_k_floor: prob_k = min_k_floor

    # Ensure total non-batted-ball events don't exceed 1.0
    if prob_bb + prob_k >= 0.95:
        scale = 0.95 / (prob_bb + prob_k)
        prob_bb *= scale
        prob_k *= scale
        
    prob_bip = 1.0 - (prob_bb + prob_k)
    
    # -------------------------------------------------------------
    # TIER 2: Batted Ball Profile Generation
    # -------------------------------------------------------------
    gb_prob = pitcher_gb_rate * prob_bip
    ld_prob = pitcher_ld_rate * prob_bip
    iffb_prob = pitcher_iffb_rate * prob_bip
    offb_prob = pitcher_offb_rate * prob_bip
    
    # -------------------------------------------------------------
    # TIER 3: The Ball-In-Play Event Resolution
    # -------------------------------------------------------------
    out_from_iffb = iffb_prob
    
    # GB
    adjusted_gb_babip = LEAGUE_GB_BABIP * defense_factor
    single_from_gb = gb_prob * adjusted_gb_babip * 0.92
    double_from_gb = gb_prob * adjusted_gb_babip * 0.08
    out_from_gb = gb_prob * (1 - adjusted_gb_babip)
    
    # LD
    adjusted_ld_babip = LEAGUE_LD_BABIP * defense_factor
    single_from_ld = ld_prob * adjusted_ld_babip * 0.75
    double_from_ld = ld_prob * adjusted_ld_babip * 0.21
    triple_from_ld = ld_prob * adjusted_ld_babip * 0.04
    out_from_ld = ld_prob * (1 - adjusted_ld_babip)
    
    # OFFB — Subtractive Window Execution
    # Stabilize HR using xFIP-mechanism (0.25 Pitcher / 0.75 League)
    regressed_hr_fb = (0.25 * pitcher_hr_fb_rate) + (0.75 * LEAGUE_HR_FB)
    
    # Platoon HR fatigue
    if tto > 0 and batter_hand and pitcher_hand and batter_hand != pitcher_hand and batter_hand != 'S':
        regressed_hr_fb *= (1.0 + (tto * 0.015 * temp_scaler))
        
    hr_from_offb = offb_prob * regressed_hr_fb
    
    # BUG FIX (2026-06-30): Deduct HR probability from the pool BEFORE applying BABIP.
    # Previously used offb_prob * (1 - regressed_hr_fb) which held the pool at HR scale,
    # inflating the singles/doubles/triples count. LEAGUE_OFFB_BABIP is calculated after
    # removing HRs, so the pool fed into it must also exclude them.
    remaining_offb_prob = max(0.0, offb_prob - hr_from_offb)
    adjusted_offb_babip = LEAGUE_OFFB_BABIP * defense_factor
    
    single_from_offb = remaining_offb_prob * adjusted_offb_babip * 0.40
    double_from_offb = remaining_offb_prob * adjusted_offb_babip * 0.52
    triple_from_offb = remaining_offb_prob * adjusted_offb_babip * 0.08
    out_from_offb = remaining_offb_prob * (1 - adjusted_offb_babip)
    
    out_rate = out_from_iffb + out_from_gb + out_from_ld + out_from_offb
    
    return {
        'k': prob_k,
        'bb': prob_bb,
        'hr': hr_from_offb,
        'single': single_from_gb + single_from_ld + single_from_offb,
        'double': double_from_gb + double_from_ld + double_from_offb,
        'triple': triple_from_ld + triple_from_offb,
        'out_rate': out_rate
    }

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
    # Threshold is 1.0 (true overflow only). Using 0.95 caused the rescaler
    # to fire in normal conditions and proportionally erase umpire/defense
    # modifiers that were applied earlier in the pipeline.
    total_non_out = sum(v for key, v in adjusted.items() if key != 'out_rate')
    if total_non_out >= 1.0:
        scale = 0.95 / total_non_out
        for key in adjusted:
            if key != 'out_rate':
                adjusted[key] *= scale
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

        # --- RULE C: SINGLES RESOLUTION (Explicit b2_holds map — no state overwrite) ---
        if np.any(ev_1b):
            idx = global_active_idx[ev_1b]

            # Anyone on 3B scores automatically
            runs[idx[base3[idx] != -1]] += 1

            # Track 2B runner advancement choices explicitly using a localized boolean map.
            # BUG FIX (2026-06-30): Original used subset index b2_idx[~advances] to set
            # base3, but the global base2[idx] np.where overwrite could erase a runner
            # who held at 3B if base1 was empty. The fix uses a full-length b2_holds mask
            # so final state commits are computed in parallel before writing to parent arrays.
            b2_mask = base2[idx] != -1
            b2_holds = np.zeros(len(idx), dtype=bool)
            if np.any(b2_mask):
                b2_idx = idx[b2_mask]
                speeds = base2[b2_idx]
                curr_outs = outs[b2_idx]
                thresholds = RUNNER_SCORE_FROM_2ND_ON_SINGLE[speeds, curr_outs]
                advances = np.random.rand(len(b2_idx)) <= thresholds
                runs[b2_idx[advances]] += 1
                b2_holds[b2_mask] = ~advances  # True if runner held up at 3B

            # Move runners sequentially using non-overlapping state mapping.
            # 3B is populated ONLY by a runner from 2B who held up.
            new_base3 = np.where(b2_holds, base2[idx], -1)
            # 2B is populated by the runner from 1B (if any).
            new_base2 = np.where(base1[idx] != -1, base1[idx], -1)
            # Commit the fresh tracking states to memory atomically.
            base3[idx] = new_base3
            base2[idx] = new_base2
            base1[idx] = batter_speeds[ev_1b]

        # --- RULE D: DOUBLES RESOLUTION (b1_holds map — no runner-erasing) ---
        if np.any(ev_2b):
            idx = global_active_idx[ev_2b]

            # Runners on 2B and 3B score automatically
            runs[idx[base3[idx] != -1]] += 1
            runs[idx[base2[idx] != -1]] += 1

            # Track 1B runner advancement choices explicitly using a localized boolean map.
            # Mirrors the Rule C b2_holds pattern to prevent a fast trailing runner from 1B
            # from overwriting a slower runner who holds at 3B on the double.
            b1_mask = base1[idx] != -1
            b1_holds = np.zeros(len(idx), dtype=bool)
            if np.any(b1_mask):
                b1_idx = idx[b1_mask]
                speeds = base1[b1_idx]
                curr_outs = outs[b1_idx]
                thresholds = RUNNER_SCORE_FROM_1ST_ON_DOUBLE[speeds, curr_outs]
                advances = np.random.rand(len(b1_idx)) <= thresholds
                runs[b1_idx[advances]] += 1
                b1_holds[b1_mask] = ~advances  # True if runner from 1B held at 3B

            # BUG FIX: Buffer new_base3 from base1 BEFORE clearing base1.
            # The user-provided code had base1[idx] = -1 first, which caused
            # np.where(b1_holds, base1[idx], -1) to always resolve to -1, silently
            # erasing every runner who held at 3B on a double.
            new_base3 = np.where(b1_holds, base1[idx], -1)

            base1[idx] = -1
            base3[idx] = new_base3
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

def fip_to_bullpen_batted_ball_profile(fip: float) -> dict:
    fip = max(2.80, min(6.50, fip))
    delta = fip - _LEAGUE_FIP
    
    # Delta > 0 means pitcher is WORSE than league average
    # Higher FIP -> lower K, higher BB, higher HR/FB, lower GB%, higher LD%
    
    k_rate = max(0.10, 0.225 + (delta * -0.015))
    bb_rate = max(0.02, 0.085 + (delta * 0.008))
    hr_fb_rate = max(0.05, 0.125 + (delta * 0.015))
    gb_rate = max(0.30, min(0.60, 0.43 + (delta * -0.02)))
    ld_rate = max(0.15, min(0.35, 0.25 + (delta * 0.015)))
    
    return {
        'bb_rate': bb_rate,
        'k_rate': k_rate,
        'gb_rate': gb_rate,
        'ld_rate': ld_rate,
        'iffb_rate': 0.07,
        'offb_rate': 1.0 - (gb_rate + ld_rate + 0.07),
        'hr_fb_rate': hr_fb_rate
    }

def _build_bullpen_lineup_states(
    raw_lineup: list,
    opposing_bp_fip: float,
    park_factor: float = 1.0,
    weather_context: dict = None,
    umpire_profile: dict = None,
    is_home: bool = False,
) -> list:
    bp_profile = fip_to_bullpen_batted_ball_profile(opposing_bp_fip)
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
                
        adj = adjust_batter_rates(b_adj, bp_profile, batter_hand=b.get('hand', 'R'), pitcher_hand='R', tto=0)
        adj = apply_environmental_physics(adj, park_factor, weather_context, batter_hand=b.get('hand', 'R'))
        cdf_matrix.append(create_cdf_array(adj))
    return [np.array(cdf_matrix)]

# Home field advantage: home batters score ~3% more runs on average league-wide
# Applied as a uniform lift to all positive offensive outcomes for home lineup
HOME_ADVANTAGE_FACTOR = 1.03


def apply_ttto_penalty(pitcher_profile: dict, times_through: int, temp_scaler: float = 1.0) -> dict:
    tto = min(times_through, 2)
    hit_pen = 1.0 + ((TTTO_HIT_PENALTY[tto] - 1.0) * temp_scaler)
    hr_pen  = 1.0 + ((TTTO_HR_PENALTY[tto] - 1.0) * temp_scaler)
    k_red = 1.0 - ((1.0 - TTTO_K_REDUCTION[tto]) * temp_scaler)
    bb_pen = 1.0 + ((tto * 0.04) * temp_scaler)
    
    # To penalize hits in the batted ball model, we decrease GB% and increase LD%/OFFB%
    gb_red = 1.0 - ((1.0 - TTTO_K_REDUCTION[tto]) * temp_scaler * 0.5)

    return {
        'bb_rate': pitcher_profile.get('bb_rate', 0.085) * bb_pen,
        'k_rate': pitcher_profile.get('k_rate', 0.225) * k_red,
        'gb_rate': pitcher_profile.get('gb_rate', 0.43) * gb_red,
        'ld_rate': pitcher_profile.get('ld_rate', 0.25) * hit_pen,
        'iffb_rate': pitcher_profile.get('iffb_rate', 0.07),
        'offb_rate': pitcher_profile.get('offb_rate', 0.25) * hit_pen,
        'hr_fb_rate': pitcher_profile.get('hr_fb_rate', 0.125) * hr_pen
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
    away_team_name: str = None,
    home_team_name: str = None,
    venue_name: str = None,
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
    # The Away Pitcher pitches to the Home Batters. The defense backing him up is the Away Team.
    away_pitcher_id = get_pitcher_id(away_pitcher_name, sport_id)
    home_pitcher_id = get_pitcher_id(home_pitcher_name, sport_id)

    away_pitcher_mods = fetch_and_profile_pitcher(away_pitcher_id)
    home_pitcher_mods = fetch_and_profile_pitcher(home_pitcher_id)
    
    away_defense_factor = calculate_defensive_hit_modifier(away_pitcher_id, away_team_name, venue_name)
    home_defense_factor = calculate_defensive_hit_modifier(home_pitcher_id, home_team_name, venue_name)

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
            current_pitcher_mods = away_inning_mods

            # Scale away batter input rates down symmetrically (0.97x) before normalization
            b_scaled = dict(b)
            for key in _HFA_KEYS:
                if key in b_scaled:
                    b_scaled[key] = b_scaled[key] * _AWAY_SCALE
            adj = adjust_batter_rates(b_scaled, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=home_pitcher_hand, tto=tto, temp_scaler=temp_scaler, umpire_profile=umpire_profile, defense_factor=home_defense_factor)
            adj = apply_environmental_physics(adj, park_factor, weather_context, batter_hand=b['hand'])
            a_cdf_matrix.append(create_cdf_array(adj))
        away_lineup_states.append(np.array(a_cdf_matrix))
        
        h_cdf_matrix = []
        for b in home_raw_lineup:
            current_pitcher_mods = home_inning_mods

            # Scale home batter input rates up (1.03x) BEFORE adjust_batter_rates().
            # This lets the existing out_rate normalization proportionally shrink ALL
            # outcomes including k, preserving strikeout ratios correctly.
            b_scaled = dict(b)
            for key in _HFA_KEYS:
                if key in b_scaled:
                    b_scaled[key] = b_scaled[key] * HOME_ADVANTAGE_FACTOR
            adj = adjust_batter_rates(b_scaled, current_pitcher_mods, batter_hand=b['hand'], pitcher_hand=away_pitcher_hand, tto=tto, temp_scaler=temp_scaler, umpire_profile=umpire_profile, defense_factor=away_defense_factor)
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

        # Update TTO only if facing starter.
        # BUG FIX (2026-06-30, Bug 4 part 2): The guard conditions were also inverted.
        # away_tto tracks how many times the AWAY lineup has wrapped against the HOME starter.
        # It must increment while the home starter is still pitching (not use_away_bp),
        # and reset when the home starter exits (use_away_bp=True) so it stays 0
        # when the 1-state bullpen CDF is used.
        if not use_away_bp:
            away_tto += (away_idx < prev_away_idx).astype(np.int32)
            away_tto = np.minimum(away_tto, 2)
        else:
            away_tto.fill(0)
            
        # home_tto tracks how many times the HOME lineup has wrapped against the AWAY starter.
        # Resets when the away starter exits.
        if not use_home_bp:
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
        
        # Top of inning (Away bats against Home pitcher)
        # BUG FIX (2026-06-30): The TTO state passed here represents how many times the
        # HOME pitcher has been through the batting order. That counter is away_tto
        # (incremented each time the away lineup wraps). Passing home_tto was inverted.
        simulate_half_inning_vectorized(
            active_games, current_away_states, away_idx, outs, away_total_runs,
            base1, base2, base3, away_speed_tiers, away_tto
        )
        
        # Reset half inning states
        outs.fill(0)
        base1.fill(-1)
        base2.fill(-1)
        base3.fill(-1)
        active_games.fill(True)
        
        # Bottom of inning (Home bats against Away pitcher)
        # BUG FIX (2026-06-30): Symmetrically, the AWAY pitcher's TTO is home_tto
        # (incremented when the home lineup wraps). Passing away_tto was inverted.
        simulate_half_inning_vectorized(
            active_games, current_home_states, home_idx, outs, home_total_runs,
            base1, base2, base3, home_speed_tiers, home_tto
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
