def calculate_expected_runs(starter_siera, bullpen_fip, proj_ip, wrc_plus, park_factor=1.0):
    """
    Top-Down model to calculate Expected F5 Runs.
    
    Variables:
    - starter_siera: Starting Pitcher's FIP/SIERA
    - bullpen_fip: Team's overall/bullpen FIP proxy
    - proj_ip: Starter's projected innings (capped at 5.0)
    - wrc_plus: Team's wRC+ (100 is average, higher is better)
    - park_factor: Stadium effect (1.0 is average)
    """
    # Baseline expected runs split between starter and bullpen
    starter_runs = (starter_siera / 9.0) * proj_ip
    bullpen_runs = (bullpen_fip / 9.0) * max(0.0, 5.0 - proj_ip)
    baseline_f5_runs = starter_runs + bullpen_runs
    
    # Offensive multiplier (wRC+ of 100 = 1.0 multiplier)
    offensive_multiplier = wrc_plus / 100.0
    
    # Calculate projected runs
    expected_f5_runs = baseline_f5_runs * offensive_multiplier * park_factor
    return expected_f5_runs

def grade_matchup(away_team, away_siera, away_bp, away_ip, away_wrc, home_team, home_siera, home_bp, home_ip, home_wrc, park_factor=1.0):
    # Home pitcher/bullpen pitches against Away offense
    away_expected_runs = calculate_expected_runs(home_siera, home_bp, home_ip, away_wrc, park_factor)
    
    # Away pitcher/bullpen pitches against Home offense
    home_expected_runs = calculate_expected_runs(away_siera, away_bp, away_ip, home_wrc, park_factor)
    
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
        away_team="Yankees", away_siera=3.20, away_bp=3.80, away_ip=5.0, away_wrc=115,
        home_team="Red Sox", home_siera=4.80, home_bp=4.20, home_ip=4.0, home_wrc=95
    )
    
    print("Test Matchup Projection:")
    for k, v in result.items():
        print(f"{k}: {v}")
