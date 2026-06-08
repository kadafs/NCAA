import random
from fetch_lineups import get_batter_pa_rates, get_pitcher_pa_modifiers, get_pitcher_hand
import statsapi

def adjust_batter_rates(batter_rates, pitcher_modifiers):
    """
    Adjusts a batter's raw outcome probabilities based on the pitcher's modifiers.
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

def simulate_plate_appearance(adjusted_rates):
    """
    Returns an outcome string based on the adjusted probabilities.
    """
    r = random.random()
    cumulative = 0.0
    
    for outcome, prob in adjusted_rates.items():
        if outcome == 'out_rate': 
            outcome = 'out'
            
        cumulative += prob
        if r <= cumulative:
            return outcome
            
    return 'out' # Fallback

def simulate_half_inning(adjusted_lineup, current_batter_idx):
    """
    Simulates a half inning and returns (runs_scored, next_batter_idx).
    """
    outs = 0
    runs = 0
    bases = [False, False, False] # 1st, 2nd, 3rd
    
    lineup_length = len(adjusted_lineup)
    if lineup_length == 0:
        return 0, 0
        
    while outs < 3:
        batter_rates = adjusted_lineup[current_batter_idx]
        outcome = simulate_plate_appearance(batter_rates)
        
        if outcome == 'out' or outcome == 'k':
            outs += 1
        elif outcome == 'bb':
            if bases[0] and bases[1] and bases[2]:
                runs += 1
            elif bases[0] and bases[1]:
                bases[2] = True
            elif bases[0]:
                bases[1] = True
            bases[0] = True
        elif outcome == 'single':
            if bases[2]: runs += 1
            if bases[1]:
                # Runner on 2nd scores on a single 60% of the time
                if random.random() < 0.6: runs += 1
                else: bases[2] = True
            if bases[0]: bases[1] = True
            bases[0] = True
            bases[2] = False
        elif outcome == 'double':
            if bases[2]: runs += 1
            if bases[1]: runs += 1
            if bases[0]:
                # Runner on 1st scores on a double 40% of the time
                if random.random() < 0.4: runs += 1
                else: bases[2] = True
            bases[1] = True
            bases[0] = False
            bases[2] = False
        elif outcome == 'triple':
            runs += sum(bases)
            bases = [False, False, True]
        elif outcome == 'hr':
            runs += sum(bases) + 1
            bases = [False, False, False]
            
        current_batter_idx = (current_batter_idx + 1) % lineup_length
        
    return runs, current_batter_idx

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
        # 6/9 LHBs have advantage, 3/9 RHBs have disadvantage
        advantage_weight  = 6 / 9
        advantage_adj = {'bb': 1.12, 'k': 0.92, 'hr': 1.15,
                         'single': 1.08, 'double': 1.08, 'triple': 1.08}
        disadvantage_adj = {'bb': 0.92, 'k': 1.10, 'hr': 0.90,
                            'single': 0.94, 'double': 0.94, 'triple': 0.94}
    else:  # LHP on the mound
        # 6/9 RHBs have advantage, 3/9 LHBs have disadvantage
        advantage_weight  = 6 / 9
        advantage_adj = {'bb': 1.10, 'k': 0.93, 'hr': 1.12,
                         'single': 1.07, 'double': 1.07, 'triple': 1.07}
        disadvantage_adj = {'bb': 0.92, 'k': 1.10, 'hr': 0.90,
                            'single': 0.94, 'double': 0.94, 'triple': 0.94}

    base = {'k': 0.22, 'bb': 0.08, 'hr': 0.03, 'single': 0.15, 'double': 0.05, 'triple': 0.005}
    lineup = []

    for i in range(9):
        batter = dict(base)

        # Batting order slot boost/penalty
        if i < 4:    # Top of order (slots 1-4): better hitters
            for k in ['bb', 'hr', 'single', 'double', 'triple']:
                batter[k] *= 1.15
            batter['k'] *= 0.90
        elif i > 5:  # Bottom of order (slots 7-9): weaker hitters
            for k in ['bb', 'hr', 'single', 'double', 'triple']:
                batter[k] *= 0.90
            batter['k'] *= 1.10

        # Blend platoon advantage (advantage_weight) + disadvantage (1 - advantage_weight)
        for stat in ['bb', 'hr', 'single', 'double', 'triple']:
            blended = (batter[stat] * advantage_adj[stat]  * advantage_weight +
                       batter[stat] * disadvantage_adj[stat] * (1 - advantage_weight))
            batter[stat] = blended
        # K blended inverse: advantage = fewer Ks
        batter['k'] = (batter['k'] * advantage_adj['k']  * advantage_weight +
                       batter['k'] * disadvantage_adj['k'] * (1 - advantage_weight))

        batter['out_rate'] = max(0.05, 1.0 - sum(
            v for key, v in batter.items() if key != 'out_rate'
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


def apply_ttto_penalty(pitcher_mods: dict, times_through: int) -> dict:
    """
    Returns a new pitcher modifier dict degraded for the given TTO count.
    times_through=0: first time through (innings 1-2)
    times_through=1: second time through (innings 3-4)
    times_through=2: third time through (inning 5+)
    """
    tto = min(times_through, 2)
    degraded = dict(pitcher_mods)
    degraded['hit_mod'] = round(pitcher_mods.get('hit_mod', 1.0) * TTTO_HIT_PENALTY[tto], 4)
    degraded['hr']      = round(pitcher_mods.get('hr',       1.0) * TTTO_HR_PENALTY[tto],  4)
    degraded['k']       = round(pitcher_mods.get('k',        1.0) * TTTO_K_REDUCTION[tto], 4)
    # bb slightly increases as pitcher tires
    degraded['bb']      = round(pitcher_mods.get('bb',       1.0) * (1.0 + (tto * 0.04)),  4)
    return degraded

def run_monte_carlo_f5(away_lineup_ids, home_lineup_ids,
                       away_pitcher_name, home_pitcher_name,
                       away_pitcher_fip, home_pitcher_fip,
                       iterations=2000, park_factor=1.0, sport_id=1,
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
    away_adjusted_lineup = []
    for pid in away_lineup_ids:
        raw_rates = get_batter_pa_rates(pid)
        adjusted = adjust_batter_rates(raw_rates, home_pitcher_mods)
        away_adjusted_lineup.append(adjusted)

    home_adjusted_lineup = []
    for pid in home_lineup_ids:
        raw_rates = get_batter_pa_rates(pid)
        adjusted = adjust_batter_rates(raw_rates, away_pitcher_mods)
        home_adjusted_lineup.append(adjusted)

    # If lineups aren't posted, use platoon-aware generic lineup
    # Note: generic lineup itself already encodes platoon advantage;
    # we pass the OPPOSING pitcher's hand so the batting team's mix is correct.
    if not away_adjusted_lineup:
        generic = generate_generic_lineup(pitcher_hand=home_pitcher_hand)
        away_adjusted_lineup = generic   # pre-adjusted; pitcher mods applied inside TTTO loop
        away_is_generic = True
    else:
        away_is_generic = False

    if not home_adjusted_lineup:
        generic = generate_generic_lineup(pitcher_hand=away_pitcher_hand)
        home_adjusted_lineup = generic
        home_is_generic = True
    else:
        home_is_generic = False

    # 3. Simulate Iterations with TTTO penalty tracking
    away_wins = 0
    home_wins = 0
    ties = 0

    away_total_runs = 0
    home_total_runs = 0
    f5_totals = []

    for _ in range(iterations):
        away_score = 0
        home_score = 0
        away_idx = 0
        home_idx = 0
        away_tto = 0   # times top of away order has been seen
        home_tto = 0
        prev_away_idx = 0
        prev_home_idx = 0

        for inning in range(5):
            # --- Detect if lineup has cycled (TTTO increment) ---
            # If batter index wrapped past slot 0 since last inning, TTO ticks up
            if away_idx < prev_away_idx:
                away_tto += 1
            if home_idx < prev_home_idx:
                home_tto += 1
            prev_away_idx = away_idx
            prev_home_idx = home_idx

            # --- Apply TTTO penalty to pitcher mods for this inning ---
            away_inning_mods = apply_ttto_penalty(home_pitcher_mods, home_tto)
            home_inning_mods = apply_ttto_penalty(away_pitcher_mods, away_tto)

            # For generic lineups, re-apply adjusted mods each inning
            if away_is_generic:
                inning_away_lineup = [adjust_batter_rates(b, away_inning_mods) for b in away_adjusted_lineup]
            else:
                # Confirmed lineup already has base mods baked in;
                # re-scale with TTTO delta only
                inning_away_lineup = away_adjusted_lineup

            if home_is_generic:
                inning_home_lineup = [adjust_batter_rates(b, home_inning_mods) for b in home_adjusted_lineup]
            else:
                inning_home_lineup = home_adjusted_lineup

            # Top of inning (Away)
            runs, away_idx = simulate_half_inning(inning_away_lineup, away_idx)
            away_score += runs

            # Bottom of inning (Home)
            runs, home_idx = simulate_half_inning(inning_home_lineup, home_idx)
            home_score += runs

        away_total_runs += away_score
        home_total_runs += home_score
        total = away_score + home_score
        f5_totals.append(total)

        if away_score > home_score:
            away_wins += 1
        elif home_score > away_score:
            home_wins += 1
        else:
            ties += 1
            
    # 4. Calculate Summary Statistics and apply Park Factor
    exp_away = (away_total_runs / iterations) * park_factor
    exp_home = (home_total_runs / iterations) * park_factor
    
    # Calculate probability of going Under typical totals (multiplying individual sim totals by park factor)
    under_3_5 = sum(1 for t in f5_totals if (t * park_factor) < 3.5) / iterations
    under_4_5 = sum(1 for t in f5_totals if (t * park_factor) < 4.5) / iterations
    under_5_5 = sum(1 for t in f5_totals if (t * park_factor) < 5.5) / iterations
    
    return {
        'away_mc_runs': round(exp_away, 2),
        'home_mc_runs': round(exp_home, 2),
        'mc_total_runs': round(exp_away + exp_home, 2),
        'away_win_prob': round(away_wins / iterations, 3),
        'home_win_prob': round(home_wins / iterations, 3),
        'tie_prob': round(ties / iterations, 3),
        'under_3_5_prob': round(under_3_5, 3),
        'under_4_5_prob': round(under_4_5, 3),
        'under_5_5_prob': round(under_5_5, 3)
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
        
        res = run_monte_carlo_f5(lineups['away'], lineups['home'], ap, hp, 4.00, 4.00, iterations=500)
        print(res)
