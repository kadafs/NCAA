"""
grade_f5.py
===========
Top-Down expected runs model for F5 innings.

Changelog:
  - Upgraded to SIERA base for precise run prevention (Top-Down only)
  - Upgraded from static 4% platoon scalers to explicit team-level wRC+ vs LHP/RHP profiles
"""

HOME_ADVANTAGE_FACTOR = 1.03

def calculate_expected_runs_siera(
    starter_siera: float,
    bullpen_fip: float,
    proj_ip: float,
    park_factor: float = 1.0,
    weather_multiplier: float = 1.0,
) -> float:
    """
    Top-Down Model: Uses SIERA as the elite predictive run-prevention driver.
    """
    unearned_run_modifier = 1.07 # SIERA captures slightly more structural context than FIP
    
    # Calculate linear run expectations against an average lineup
    starter_runs  = (starter_siera / 9.0) * unearned_run_modifier * proj_ip
    bullpen_runs  = (bullpen_fip   / 9.0) * unearned_run_modifier * max(0.0, 5.0 - proj_ip)
    baseline_runs = starter_runs + bullpen_runs

    # Environmental compound stacking
    return baseline_runs * (park_factor * weather_multiplier)

def grade_matchup_v6(
    away_team: str, away_siera: float, away_bp: float, away_ip: float,
    away_vs_rhp_wrc: float, away_vs_lhp_wrc: float, # Pass actual team split profilers
    home_team: str, home_siera: float, home_bp: float, home_ip: float,
    home_vs_rhp_wrc: float, home_vs_lhp_wrc: float,
    park_factor: float = 1.0, weather_multiplier: float = 1.0,
    away_pitcher_hand: str = 'R', home_pitcher_hand: str = 'R'
) -> dict:
    """
    Grades the matchup by matching the team's authentic wRC+ split 
    against the specific hand of the starting pitcher.
    """
    # Dynamically extract the exact split capability of the offense
    away_split_wrc = away_vs_lhp_wrc if home_pitcher_hand.upper() == 'L' else away_vs_rhp_wrc
    home_split_wrc = home_vs_lhp_wrc if away_pitcher_hand.upper() == 'L' else home_vs_rhp_wrc
    
    # Scale offensive capabilities defensively using predictive roots
    away_offense_scalar = (away_split_wrc / 100.0) ** 0.7
    home_offense_scalar = (home_split_wrc / 100.0) ** 0.7

    # Run the base SIERA engine and overlay offense + home advantages
    away_expected = calculate_expected_runs_siera(home_siera, home_bp, home_ip, park_factor, weather_multiplier) * away_offense_scalar
    home_expected = calculate_expected_runs_siera(away_siera, away_bp, away_ip, park_factor, weather_multiplier) * home_offense_scalar * HOME_ADVANTAGE_FACTOR

    return {
        'away_team': away_team, 'home_team': home_team,
        'away_expected_f5_runs': round(away_expected, 2),
        'home_expected_f5_runs': round(home_expected, 2),
        'projected_f5_total': round(away_expected + home_expected, 2),
        'projected_f5_margin': round(home_expected - away_expected, 2),
    }

if __name__ == '__main__':
    result = grade_matchup_v6(
        away_team='NYY', away_siera=3.20, away_bp=3.50, away_ip=5.0,
        away_vs_rhp_wrc=110, away_vs_lhp_wrc=130,
        home_team='BOS', home_siera=4.00, home_bp=4.00, home_ip=4.5,
        home_vs_rhp_wrc=105, home_vs_lhp_wrc=95,
        park_factor=1.0, weather_multiplier=1.0,
        away_pitcher_hand='R', home_pitcher_hand='L'
    )
    print(result)
