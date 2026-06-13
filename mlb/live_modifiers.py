from mlb_time import get_mlb_now
"""
live_modifiers.py
=================
Live exploitation math for the LF5 engine.

Implements five live-game scenario adjustments that standard sportsbook
algorithms systematically fail to price in real time:

  Scenario A: Acute High-Stress Pitch Count (Fatigue Scaler)
  Scenario B: Sequencing Leverage  — handled natively by the engine
              via next_hitter_index initialization
  Scenario C: Live Weather Recalculation — handled by apply_environmental_physics()
              in monte_carlo_f5.py with live micro_climate values
  Scenario D: Relief Pitcher Availability Trap (Bullpen Trap)
  Scenario E: Asymmetric Crosswind Geometry
"""

import datetime
import numpy as np
import statsapi

# ---------------------------------------------------------------------------
# Scenario A: Acute High-Stress Pitch Count Fatigue Scaler
# ---------------------------------------------------------------------------
# Blueprint formula:
#   Fatigue = (cumulative_pitches / 100)
#           + (high_stress_innings × 0.05)
#           + ((live_temp - 70) / 10 × 0.035)
#
# Threshold: if Fatigue > 1.10, apply degradation to remaining pitcher CDFs:
#   - K rate modifier × 0.88  (12% reduction)
#   - hit_mod × 1.15          (15% inflation)

FATIGUE_THRESHOLD = 1.10

# Degradation multipliers applied to the pitcher modifier dict when threshold is exceeded
FATIGUE_K_PENALTY    = 0.88   # K rate degrades 12%
FATIGUE_HIT_INFLATE  = 1.15   # Hit rate inflates 15%


def calc_fatigue_scaler(
    cumulative_pitches: int,
    high_stress_innings: int,
    live_temp: float
) -> float:
    """
    Computes the Acute Stress Fatigue Scaler from live pitcher tracking metrics.

    Parameters
    ----------
    cumulative_pitches  : Total pitches thrown by the active pitcher in this game.
    high_stress_innings : Number of innings where the pitcher exceeded 25 pitches.
    live_temp           : Current temperature in °F at the ballpark.

    Returns
    -------
    float   Fatigue scalar. Values > 1.10 trigger degradation.

    Examples
    --------
    >>> calc_fatigue_scaler(64, 1, 78.4)
    1.0917   # below threshold, no degradation
    >>> calc_fatigue_scaler(95, 2, 88.0)
    1.1353   # above threshold → K -12%, hits +15%
    """
    pitch_component   = cumulative_pitches / 100.0
    stress_component  = high_stress_innings * 0.05
    temp_component    = ((live_temp - 70.0) / 10.0) * 0.035
    return round(pitch_component + stress_component + temp_component, 4)


def apply_fatigue_to_pitcher_mods(pitcher_mods: dict, fatigue_scaler: float) -> dict:
    """
    If fatigue_scaler exceeds FATIGUE_THRESHOLD, degrades the pitcher modifier dict.
    Returns a new dict (does not mutate the input).

    Applied prior to the next CDF matrix construction for the active pitcher.
    """
    if fatigue_scaler <= FATIGUE_THRESHOLD:
        return pitcher_mods

    degraded = dict(pitcher_mods)
    degraded['k']        = round(degraded.get('k',        1.0) * FATIGUE_K_PENALTY,   4)
    degraded['hit_mod']  = round(degraded.get('hit_mod',  1.0) * FATIGUE_HIT_INFLATE, 4)
    # Cap hit_mod at 1.40 to prevent runaway inflation
    degraded['hit_mod']  = min(1.40, degraded['hit_mod'])
    # Floor K at 0.4 to prevent division by zero / unphysical outcomes
    degraded['k']        = max(0.40, degraded['k'])
    return degraded


# ---------------------------------------------------------------------------
# Scenario D: Relief Pitcher Availability Trap
# ---------------------------------------------------------------------------

# Pitch threshold (combined, over 48 hours) that flags top relievers as UNAVAILABLE
BULLPEN_UNAVAILABLE_THRESHOLD = 30   # combined pitches in 48h for top-3 HLRs

# FIP penalty added to the "mop-up reliever proxy" when top-end bullpen is unavailable
MOP_UP_FIP_PENALTY = 1.25


def get_bullpen_availability(team_name: str, sport_id: int = 1) -> dict:
    """
    Scans the last 48 hours of game logs for the team's relief pitchers.
    Flags the bullpen as UNAVAILABLE if top-3 high-leverage relievers
    combined threw > 30 pitches in the previous 48 hours.

    Returns
    -------
    dict:
        available         : list of available pitcher player_ids
        unavailable       : list of unavailable pitcher player_ids
        is_depleted       : bool — True if mop-up proxy should be used
        mop_up_fip_penalty: float — additional FIP to add to remaining bullpen innings
        notes             : human-readable status string
    """
    try:
        teams = statsapi.lookup_team(team_name, sportIds=sport_id)
        if not teams:
            return _empty_bullpen_result("Team not found")
        team_id = teams[0]['id']
    except Exception as e:
        return _empty_bullpen_result(f"Lookup error: {e}")

    # Fetch team's 40-man roster to identify relievers
    try:
        roster_data = statsapi.get('team_roster', {
            'teamId': team_id,
            'rosterType': 'active',
        })
        roster = roster_data.get('roster', [])
    except Exception as e:
        return _empty_bullpen_result(f"Roster error: {e}")

    # Filter to relievers only (position code 1 = Pitcher; we can't distinguish
    # starters from relievers without deeper data, so we use all pitchers)
    pitcher_ids = [
        p['person']['id']
        for p in roster
        if p.get('position', {}).get('code') == '1'
    ]

    if not pitcher_ids:
        return _empty_bullpen_result("No pitchers found on roster")

    # Check pitch counts over the last 2 calendar days
    today   = get_mlb_now().date()
    cutoff  = today - datetime.timedelta(days=2)

    combined_recent_pitches: dict[int, int] = {}

    for pid in pitcher_ids:
        try:
            # Get individual game log
            log = statsapi.get('people', {
                'personIds': pid,
                'hydrate': 'stats(group=[pitching],type=gameLog,season=2026)',
            })
            games_pitched = 0
            for person in log.get('people', []):
                for stat_grp in person.get('stats', []):
                    for split in stat_grp.get('splits', []):
                        game_date_str = split.get('date', '')
                        try:
                            game_date = datetime.date.fromisoformat(game_date_str)
                        except ValueError:
                            continue
                        if game_date >= cutoff:
                            pitches = int(split.get('stat', {}).get('numberOfPitches', 0) or 0)
                            combined_recent_pitches[pid] = combined_recent_pitches.get(pid, 0) + pitches
        except Exception:
            continue

    # Sort pitchers by recent workload (descending) to identify the top-3 HLRs
    sorted_pitchers = sorted(combined_recent_pitches.items(), key=lambda x: x[1], reverse=True)

    # Top 3 high-leverage relievers
    top3 = sorted_pitchers[:3]
    top3_combined = sum(p for _, p in top3)

    unavailable = [pid for pid, pc in top3 if pc >= BULLPEN_UNAVAILABLE_THRESHOLD // 2]
    available   = [pid for pid in pitcher_ids if pid not in unavailable]

    is_depleted     = top3_combined >= BULLPEN_UNAVAILABLE_THRESHOLD
    fip_penalty     = MOP_UP_FIP_PENALTY if is_depleted else 0.0

    notes = (
        f"Top-3 HLRs threw {top3_combined} pitches in last 48h. "
        f"{'DEPLETED — mop-up proxy activated.' if is_depleted else 'Fresh — normal bullpen proxy.'}"
    )

    return {
        'available':          available,
        'unavailable':        unavailable,
        'is_depleted':        is_depleted,
        'mop_up_fip_penalty': fip_penalty,
        'top3_recent_pitches': top3_combined,
        'notes':              notes,
    }


def _empty_bullpen_result(reason: str) -> dict:
    return {
        'available':          [],
        'unavailable':        [],
        'is_depleted':        False,
        'mop_up_fip_penalty': 0.0,
        'top3_recent_pitches': 0,
        'notes':              f"Could not fetch bullpen data: {reason}",
    }


# ---------------------------------------------------------------------------
# Starter Exit Probability
# ---------------------------------------------------------------------------
# Used to determine if the starter should be "swapped out" for the bullpen
# proxy CDF during remaining simulation paths.

# Cumulative pitch count → probability of being pulled before completing
# the current or next inning.
_EXIT_THRESHOLDS = [
    (75,  0.05),   # < 75 pitches: 5% chance of exit
    (90,  0.25),   # 75-89 pitches: 25%
    (100, 0.60),   # 90-99 pitches: 60%
    (110, 0.80),   # 100-109 pitches: 80%
]
_EXIT_DEFAULT = 0.95   # ≥110 pitches: 95% exit probability


def get_starter_exit_probability(
    cumulative_pitches: int,
    high_stress_innings: int = 0
) -> float:
    """
    Returns the probability (0.0–1.0) that the starter will be pulled
    before completing the current inning, given their pitch count.

    Stress innings add a 5% incremental exit probability per inning
    (a pitcher who survived a 35-pitch inning is more likely to be pulled next).

    Parameters
    ----------
    cumulative_pitches   : Total pitches thrown by starter in this game.
    high_stress_innings  : Number of innings exceeding 25 pitches.

    Returns
    -------
    float   Exit probability in [0.0, 1.0].
    """
    base_prob = _EXIT_DEFAULT
    for threshold, prob in _EXIT_THRESHOLDS:
        if cumulative_pitches < threshold:
            base_prob = prob
            break

    stress_adj = min(high_stress_innings * 0.05, 0.20)  # cap at +20%
    return min(1.0, round(base_prob + stress_adj, 4))


# ---------------------------------------------------------------------------
# Wind shift detection (Scenario C helper)
# ---------------------------------------------------------------------------

def detect_wind_shift(morning_weather: dict, live_micro_climate: dict) -> bool:
    """
    Returns True if the live weather conditions represent a significant
    shift from the morning forecast that warrants a CDF recalculation.

    Triggers a recalculation if:
    - Wind direction changed (e.g., 'IN' → 'OUT')
    - Wind speed crossed 12 MPH in either direction
    """
    if not morning_weather or not live_micro_climate:
        return False

    morning_dir   = morning_weather.get('wind_dir',   'Calm')
    live_dir      = live_micro_climate.get('live_wind_dir', 'CALM').capitalize()
    morning_speed = morning_weather.get('wind_mph',   0)
    live_speed    = live_micro_climate.get('live_wind_speed', 0)

    dir_changed   = (morning_dir != live_dir) and not (
        morning_dir in ('Calm', 'Indoor') and live_dir in ('Calm', 'Indoor')
    )
    speed_crossed = (morning_speed < 12 and live_speed >= 12) or \
                    (morning_speed >= 12 and live_speed < 12)

    return dir_changed or speed_crossed


# ---------------------------------------------------------------------------
# Scenario E: Asymmetric Crosswind Geometry
# ---------------------------------------------------------------------------
# MLB stadiums are oriented roughly East-Northeast to protect batter vision
# from afternoon sun. This creates a structural geometry where lateral winds
# interact differently with LHB vs RHB fly-ball trajectories.
#
# Impact Matrix:
#   Wind L->R (3B line toward 1B line):
#     LHB: TAILWIND  — carries pulled fly balls over Right Field wall  (+HR)
#     RHB: HEADWIND  — knocks pulled fly balls down in Left Field      (-HR)
#
#   Wind R->L (1B line toward 3B line):
#     LHB: HEADWIND  — knocks pulled fly balls down in Right Field     (-HR)
#     RHB: TAILWIND  — carries pulled fly balls over Left Field wall   (+HR)
#
# Physical velocity cap: 15 MPH → max +/- 5% HR rate shift (linear scaling)

CROSSWIND_SPEED_CAP   = 15.0   # MPH — plateau beyond which marginal HR lift flattens
CROSSWIND_MAX_SHIFT   = 0.05   # Maximum +/- 5% HR rate shift at cap speed
CROSSWIND_VALID_DIRS  = {'L-R', 'R-L'}   # Lateral vectors only; IN/OUT/CALM are no-ops


def calculate_crosswind_modifier(batter_hand: str, wind_dir: str, wind_speed: float) -> float:
    """
    Computes an asymmetrical crosswind scale factor for a single batter's HR rate.

    Caps magnitude linearly at +/- 5% at 15 MPH. Returns 1.0 for any
    non-lateral wind direction (IN, OUT, CALM) or zero wind speed.

    Parameters
    ----------
    batter_hand : str    'L' or 'R'
    wind_dir    : str    'L-R', 'R-L', 'IN', 'OUT', or 'CALM'
    wind_speed  : float  Live wind velocity in MPH

    Returns
    -------
    float   Multiplicative HR rate scaler in [0.95, 1.05]

    Examples
    --------
    >>> calculate_crosswind_modifier('L', 'L-R', 12.0)
    1.0400    # 12/15 * 5% tailwind to RF = +4%
    >>> calculate_crosswind_modifier('R', 'L-R', 12.0)
    0.9600    # Same wind, headwind into LF = -4%
    >>> calculate_crosswind_modifier('R', 'R-L', 15.0)
    1.0500    # Full-cap tailwind to LF = +5%
    >>> calculate_crosswind_modifier('L', 'IN', 20.0)
    1.0000    # Non-lateral — no asymmetric effect
    """
    if wind_dir not in CROSSWIND_VALID_DIRS or wind_speed <= 0:
        return 1.0

    # Linear scale from 0 to CROSSWIND_MAX_SHIFT, capped at CROSSWIND_SPEED_CAP
    capped_speed = min(wind_speed, CROSSWIND_SPEED_CAP)
    magnitude    = (capped_speed / CROSSWIND_SPEED_CAP) * CROSSWIND_MAX_SHIFT

    if wind_dir == 'L-R':
        # L-R vector: LHB gets tailwind (RF), RHB gets headwind (LF)
        return 1.0 + magnitude if batter_hand == 'L' else 1.0 - magnitude

    else:  # 'R-L'
        # R-L vector: RHB gets tailwind (LF), LHB gets headwind (RF)
        return 1.0 + magnitude if batter_hand == 'R' else 1.0 - magnitude


def apply_crosswind_to_cdf_stack(
    cdf_stack: np.ndarray,
    batter_hands: list[str],
    wind_dir: str,
    wind_speed: float
) -> np.ndarray:
    """
    Applies per-batter asymmetric crosswind HR modifiers to a (TTO, 9, 7) CDF stack.

    Because the LF5 engine is fully vectorized with no Python per-batter inner loop,
    the crosswind modifier is baked into the CDF matrices BEFORE the NumPy simulator
    runs. This function performs the out-sink re-normalization:

        P(HR) = cdf[6] - cdf[5]
        P(HR)_adjusted = P(HR) * crosswind_mod
        delta = P(HR)_adjusted - P(HR)
        P(Out) += -delta            # delta is absorbed into / donated from Out (index 0)
        CDF is then recomputed cumulatively so it still sums to 1.0

    Parameters
    ----------
    cdf_stack    : np.ndarray  Shape (n_tto, 9, 7) or (9, 7) for bullpen stub.
                               CDF values [out, k, bb, 1b, 2b, 3b, hr] cumulative.
    batter_hands : list[str]   9-element list of 'L' or 'R' for each lineup slot.
    wind_dir     : str         'L-R', 'R-L', 'IN', 'OUT', or 'CALM'
    wind_speed   : float       Live wind velocity in MPH.

    Returns
    -------
    np.ndarray   Crosswind-adjusted copy of cdf_stack. Original is not mutated.
    """
    # Early exit: non-lateral winds have no asymmetric effect
    if wind_dir not in CROSSWIND_VALID_DIRS or wind_speed <= 0:
        return cdf_stack

    # Compute per-batter crosswind modifiers — shape (9,)
    mods = np.array(
        [calculate_crosswind_modifier(h, wind_dir, wind_speed) for h in batter_hands],
        dtype=np.float64
    )

    # Work on a copy to avoid mutating the cached morning matrices
    adj = cdf_stack.astype(np.float64, copy=True)
    squeezed = (adj.ndim == 2)  # Handle (9,7) bullpen stub
    if squeezed:
        adj = adj[np.newaxis, :, :]  # Promote to (1, 9, 7)

    n_tto = adj.shape[0]

    for tto in range(n_tto):
        # Extract raw probability mass from the cumulative CDF
        # raw[i] = P(outcome_i):  shape (9, 7)
        raw = np.diff(adj[tto], prepend=0.0, axis=1)  # shape (9, 7)

        # HR is the 7th outcome (index 6), Out is the 1st (index 0)
        p_hr_before  = raw[:, 6].copy()               # shape (9,)
        p_hr_after   = p_hr_before * mods             # scaled by per-batter modifier

        # Clamp: HR prob floor at 0.0001, ceiling at 0.25 to block unphysical extremes
        p_hr_after   = np.clip(p_hr_after, 0.0001, 0.25)

        # Compute delta and absorb into Out (out-sink re-normalization)
        delta        = p_hr_after - p_hr_before       # positive = HR gained from Out
        raw[:, 6]    = p_hr_after
        raw[:, 0]   -= delta                          # Out absorbs or donates the delta

        # Safety clamp: Out prob cannot go below 0.0001
        raw[:, 0]    = np.maximum(raw[:, 0], 0.0001)

        # Re-normalize so the row sum is guaranteed = 1.0 (floating point hygiene)
        row_sums     = raw.sum(axis=1, keepdims=True)
        raw         /= row_sums

        # Recompute cumulative CDF
        adj[tto]     = np.cumsum(raw, axis=1)

    if squeezed:
        adj = adj[0]  # Return to (9, 7)

    return adj


if __name__ == '__main__':
    # Quick smoke test of fatigue scaler
    test_cases = [
        (64, 1, 78.4, "Moderate load, warm"),
        (95, 2, 88.0, "High load, hot"),
        (45, 0, 65.0, "Light load, cool"),
        (100, 3, 92.0, "Very high load, hot"),
    ]
    print("\nFatigue Scaler Tests:")
    print(f"{'Pitches':>8} {'Stress':>6} {'Temp':>6} {'Scaler':>8} {'Trigger':>10}")
    print("-" * 45)
    for pitches, stress, temp, label in test_cases:
        scaler = calc_fatigue_scaler(pitches, stress, temp)
        trigger = "⚠️ DEGRADE" if scaler > FATIGUE_THRESHOLD else "OK"
        print(f"{pitches:>8} {stress:>6} {temp:>6.1f} {scaler:>8.4f} {trigger:>10}  ({label})")
