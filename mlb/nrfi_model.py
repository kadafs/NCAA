import statistics

def calculate_threat_score(pitcher_stats, batters_stats):
    """
    Calculates the YRFI Threat Score for a specific half-inning matchup.
    
    pitcher_stats: dict returned by nrfi_data.get_pitcher_first_inning_stats
    batters_stats: list of dicts returned by nrfi_data.get_batter_xwoba_vs_hand
    """
    # Fallback to league averages if data is missing
    p_xwoba = pitcher_stats['xwoba_1st'] if pitcher_stats else 0.320
    
    valid_batters = [b['xwoba_vs_hand'] for b in batters_stats if b is not None]
    if valid_batters:
        b_xwoba = statistics.mean(valid_batters)
    else:
        b_xwoba = 0.320
        
    # Baseline xwOBA is around 0.320
    # Threat score is a combination of how bad the pitcher is in the 1st
    # and how good the top of the order is against that handedness.
    # Higher score = Higher chance of YRFI (runs scored)
    # Lower score = Higher chance of NRFI (0 runs)
    
    threat_score = (p_xwoba + b_xwoba) / 2
    
    return round(threat_score, 3)

def evaluate_game(away_hitters_stats, home_sp_stats, home_hitters_stats, away_sp_stats):
    """
    Evaluates both halves of the first inning to determine an overall game recommendation.
    """
    top_inning_threat = calculate_threat_score(home_sp_stats, away_hitters_stats)
    bottom_inning_threat = calculate_threat_score(away_sp_stats, home_hitters_stats)
    
    max_threat = max(top_inning_threat, bottom_inning_threat)
    avg_threat = (top_inning_threat + bottom_inning_threat) / 2
    
    recommendation = "PASS"
    if max_threat < 0.290 and avg_threat < 0.300:
        recommendation = "STRONG NRFI"
    elif avg_threat < 0.315:
        recommendation = "LEAN NRFI"
    elif max_threat > 0.360 or avg_threat > 0.340:
        recommendation = "STRONG YRFI"
    elif avg_threat > 0.330:
        recommendation = "LEAN YRFI"
        
    return {
        'top_inning_threat': top_inning_threat,
        'bottom_inning_threat': bottom_inning_threat,
        'max_threat': max_threat,
        'avg_threat': avg_threat,
        'recommendation': recommendation
    }
