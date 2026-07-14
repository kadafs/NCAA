from mlb_time import get_mlb_now
import random
from fetch_lineups import get_batter_pa_rates, get_pitcher_pa_modifiers
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

def get_pitcher_id(pitcher_name):
    if not pitcher_name or pitcher_name == 'TBD': return None
    players = [p for p in statsapi.lookup_player(pitcher_name) if p.get('primaryPosition', {}).get('abbreviation') in ('P', 'TWP')]
    if players: return players[0]['id']
    return None

def generate_generic_lineup():
    """
    Generates a top-heavy generic lineup to properly model F5 runs.
    Hitters 1-4 get a 15% boost to on-base outcomes, hitters 7-9 get a 10% penalty.
    """
    base = {'k': 0.22, 'bb': 0.08, 'hr': 0.03, 'single': 0.15, 'double': 0.05, 'triple': 0.005}
    lineup = []
    
    for i in range(9):
        batter = dict(base)
        if i < 4: # Top of order (slots 1-4)
            for k in ['bb', 'hr', 'single', 'double', 'triple']: batter[k] *= 1.15
            batter['k'] *= 0.90 # 10% fewer Ks
        elif i > 5: # Bottom of order (slots 7-9)
            for k in ['bb', 'hr', 'single', 'double', 'triple']: batter[k] *= 0.90
            batter['k'] *= 1.10 # 10% more Ks
            
        batter['out_rate'] = max(0.05, 1.0 - sum(batter.values()))
        lineup.append(batter)
        
    return lineup

def run_monte_carlo_f5(away_lineup_ids, home_lineup_ids, away_pitcher_name, home_pitcher_name, away_pitcher_fip, home_pitcher_fip, iterations=2000, park_factor=1.0):
    """
    Runs Monte Carlo simulation for the F5 innings.
    Returns expected runs, win probabilities, and total distribution.
    """
    # 1. Fetch Pitcher Modifiers
    away_pitcher_id = get_pitcher_id(away_pitcher_name)
    home_pitcher_id = get_pitcher_id(home_pitcher_name)
    
    away_pitcher_mods = get_pitcher_pa_modifiers(away_pitcher_fip, away_pitcher_id) 
    home_pitcher_mods = get_pitcher_pa_modifiers(home_pitcher_fip, home_pitcher_id)
    
    # 2. Fetch Batter Rates and Adjust
    away_adjusted_lineup = []
    for pid in away_lineup_ids:
        raw_rates = get_batter_pa_rates(pid)
        adjusted = adjust_batter_rates(raw_rates, home_pitcher_mods.get('R'))
        away_adjusted_lineup.append(adjusted)
        
    home_adjusted_lineup = []
    for pid in home_lineup_ids:
        raw_rates = get_batter_pa_rates(pid)
        adjusted = adjust_batter_rates(raw_rates, away_pitcher_mods.get('R'))
        home_adjusted_lineup.append(adjusted)
        
    # If lineups aren't posted, use generic lineup, adjusted for pitchers
    if not away_adjusted_lineup:
        away_adjusted_lineup = [adjust_batter_rates(b, home_pitcher_mods.get('R')) for b in generate_generic_lineup()]
    if not home_adjusted_lineup:
        home_adjusted_lineup = [adjust_batter_rates(b, away_pitcher_mods.get('R')) for b in generate_generic_lineup()]

    # 3. Simulate Iterations
    away_wins = 0
    home_wins = 0
    ties = 0
    
    away_total_runs = 0
    home_total_runs = 0
    
    # Track distributions
    f5_totals = []
    
    for _ in range(iterations):
        away_score = 0
        home_score = 0
        away_idx = 0
        home_idx = 0
        
        for inning in range(5):
            # Top of inning (Away)
            runs, away_idx = simulate_half_inning(away_adjusted_lineup, away_idx)
            away_score += runs
            
            # Bottom of inning (Home)
            runs, home_idx = simulate_half_inning(home_adjusted_lineup, home_idx)
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
        
        res = run_monte_carlo_f5(lineups['away'], lineups['home'], ap, hp, 4.00, 4.00, iterations=500)
        print(res)
