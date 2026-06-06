def calculate_expected_runs(siera, wrc_plus, park_factor=1.0):
    """
    Very basic V1 Top-Down model to calculate Expected F5 Runs.
    
    Variables:
    - siera: Pitcher's SIERA (lower is better, league avg ~4.00)
    - wrc_plus: Team's wRC+ (100 is average, higher is better)
    - park_factor: Stadium effect (1.0 is average)
    """
    # Baseline expected runs allowed by this pitcher over 5 innings
    baseline_f5_runs = (siera / 9.0) * 5.0
    
    # Offensive multiplier (wRC+ of 100 = 1.0 multiplier)
    offensive_multiplier = wrc_plus / 100.0
    
    # Calculate projected runs
    expected_f5_runs = baseline_f5_runs * offensive_multiplier * park_factor
    return expected_f5_runs

def grade_matchup(away_team, away_siera, away_wrc, home_team, home_siera, home_wrc, park_factor=1.0):
    # Home pitcher pitches against Away offense
    away_expected_runs = calculate_expected_runs(home_siera, away_wrc, park_factor)
    
    # Away pitcher pitches against Home offense
    home_expected_runs = calculate_expected_runs(away_siera, home_wrc, park_factor)
    
    total_runs = away_expected_runs + home_expected_runs
    spread = home_expected_runs - away_expected_runs
    
    return {
        'away_team': away_team,
        'home_team': home_team,
        'away_expected_f5_runs': round(away_expected_runs, 2),
        'home_expected_f5_runs': round(home_expected_runs, 2),
        'projected_f5_total': round(total_runs, 2),
        'projected_f5_margin': round(spread, 2)
    }

if __name__ == "__main__":
    # Test example
    result = grade_matchup(
        away_team="Yankees", away_siera=3.20, away_wrc=115,
        home_team="Red Sox", home_siera=4.80, home_wrc=95
    )
    
    print("Test Matchup Projection:")
    for k, v in result.items():
        print(f"{k}: {v}")
