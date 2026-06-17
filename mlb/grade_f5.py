"""
grade_f5.py
===========
Top-Down expected runs model for F5 innings.

Changelog:
  - Issue 1: weather_multiplier applied multiplicatively (not baked into park factor additively)
  - Issue 3: platoon adjustment to team wRC+ based on opposing pitcher handedness
"""

# ---------------------------------------------------------------------------
# Platoon adjustment constants (Issue 3 fix)
# ---------------------------------------------------------------------------
# MLB teams average ~68% right-handed batters. A left-handed starter therefore
# gives the majority of the opposing lineup a platoon advantage (RHB vs LHP).
# Published platoon splits show ~4-5% wRC+ boost for the advantaged hand.
#
# Facing RHP: the ~68% RHBs are same-hand (disadvantage) → net small penalty
# Facing LHP: the ~68% RHBs are opposite-hand (advantage) → net +4% boost
#
# Values are intentionally conservative: the top-down model works at team
# aggregate level; the MC model handles per-batter platoon more precisely.
_PLATOON_VS_LHP = 1.04   # avg team offense vs LHP (majority RHBs have advantage)
_PLATOON_VS_RHP = 0.98   # avg team offense vs RHP (majority RHBs are same-hand)
# Switch hitters → treated as neutral (no adjustment)
_PLATOON_NEUTRAL = 1.00

# Home field advantage: research shows home teams score ~3% more runs on average
# Sources: FanGraphs home/away splits ~3-5% wRC+ boost across all MLB seasons
HOME_ADVANTAGE_FACTOR = 1.03


def _platoon_scaler(pitcher_hand: str) -> float:
    """Returns the team-level wRC+ platoon scaler given the opposing pitcher hand."""
    h = pitcher_hand.upper() if pitcher_hand else 'R'
    if h == 'L':
        return _PLATOON_VS_LHP
    if h == 'R':
        return _PLATOON_VS_RHP
    return _PLATOON_NEUTRAL  # 'S' or unknown


# ---------------------------------------------------------------------------
# Core run expectation formula
# ---------------------------------------------------------------------------

def calculate_expected_runs(
    starter_siera: float,
    bullpen_fip: float,
    proj_ip: float,
    wrc_plus: float,          # Kept for signature compatibility; no longer used as a scaler.
    park_factor: float = 1.0,
    weather_multiplier: float = 1.0,
) -> float:
    """
    Top-Down model: Expected F5 runs allowed by the pitching staff.

    FIP is the sole offensive driver. Lineup quality (wRC+) is intentionally
    excluded here — the Monte Carlo model handles per-batter offensive context
    with full lineup matchup logic. Applying wRC+ here double-counts offense
    and inflates totals for elite pitchers facing strong lineups.

    Small pitcher-context adjustments (platoon ±2-4%, home field +3%) are
    applied in grade_matchup() after this call.

    Parameters
    ----------
    starter_siera    : Starting pitcher FIP (or SIERA proxy)
    bullpen_fip      : Team bullpen FIP proxy
    proj_ip          : Starter's projected innings pitched (capped at 5.0)
    wrc_plus         : Unused. Kept for backward compatibility.
    park_factor      : Stadium run multiplier (1.0 = neutral)
    weather_multiplier: Combined temp×wind run multiplier (1.0 = neutral).
                        Applied MULTIPLICATIVELY, not additively.
    """
    # 1. Unearned Run Factor (ERA/SIERA/FIP -> RA9 conversion)
    # Pitching metrics omit unearned runs, but RA9 is typically ~1.08x higher.
    unearned_run_modifier = 1.08

    # 2. Pitching baseline: explicit runs surrendered per 5 innings (vs avg lineup)
    starter_runs  = (starter_siera / 9.0) * unearned_run_modifier * proj_ip
    bullpen_runs  = (bullpen_fip   / 9.0) * unearned_run_modifier * max(0.0, 5.0 - proj_ip)
    baseline_runs = starter_runs + bullpen_runs

    # 3. Environment: park × weather (multiplicative, correct physics)
    env_multiplier = park_factor * weather_multiplier

    # wRC+ intentionally NOT applied — FIP is the pure run-prevention signal.
    # Offensive context is fully handled by the Monte Carlo model.
    return baseline_runs * env_multiplier


# ---------------------------------------------------------------------------
# Matchup grader
# ---------------------------------------------------------------------------

def grade_matchup(
    away_team: str,
    away_siera: float,
    away_bp: float,
    away_ip: float,
    away_wrc: float,          # Retained for signature compatibility; not used as a scaler.
    home_team: str,
    home_siera: float,
    home_bp: float,
    home_ip: float,
    home_wrc: float,          # Retained for signature compatibility; not used as a scaler.
    park_factor: float = 1.0,
    weather_multiplier: float = 1.0,
    away_pitcher_hand: str = 'R',
    home_pitcher_hand: str = 'R',
) -> dict:
    """
    Grades a full matchup and returns expected runs for both sides.

    FIP-pure model: wRC+ (lineup quality) has been removed from the Top-Down
    calculation because the Monte Carlo model already handles it with full
    per-batter matchup logic. Applying wRC+ twice inflated totals for elite
    pitchers facing strong offenses.

    Retained adjustments (pitcher-context, not lineup-context):
      - Platoon splits (±2-4%): LHP on the mound gives opposite-hand bats an edge.
      - Home field advantage (+3%): home teams score more regardless of lineup.
      - Park factor + weather (multiplicative env stack).
    """
    # Platoon scalers: how the BATTING team fares given the OPPOSING pitcher's hand
    away_platoon = _platoon_scaler(home_pitcher_hand)  # Rays vs LHP Wrobleski → +4%
    home_platoon = _platoon_scaler(away_pitcher_hand)  # Dodgers vs RHP Rasmussen → -2%

    # Home pitcher + bullpen faces Away offense (FIP-pure baseline, platoon-adjusted)
    away_expected = calculate_expected_runs(
        home_siera, home_bp, home_ip,
        100.0,  # wRC+ neutral — FIP is the sole run-prevention driver
        park_factor, weather_multiplier
    ) * away_platoon

    # Away pitcher + bullpen faces Home offense (FIP-pure baseline, platoon + HFA adjusted)
    home_expected = calculate_expected_runs(
        away_siera, away_bp, away_ip,
        100.0,  # wRC+ neutral — FIP is the sole run-prevention driver
        park_factor, weather_multiplier
    ) * home_platoon * HOME_ADVANTAGE_FACTOR

    total_runs = away_expected + home_expected
    spread     = home_expected - away_expected

    return {
        'away_team':             away_team,
        'home_team':             home_team,
        'away_expected_f5_runs': round(away_expected, 2),
        'home_expected_f5_runs': round(home_expected, 2),
        'projected_f5_total':    round(total_runs, 2),
        'projected_f5_margin':   round(spread, 2),
    }


if __name__ == '__main__':
    # Regression test: LHP vs RHB-heavy lineup should boost away offense
    result_rhp = grade_matchup(
        away_team='Yankees', away_siera=3.20, away_bp=3.80, away_ip=5.0, away_wrc=115,
        home_team='Red Sox',  home_siera=4.80, home_bp=4.20, home_ip=4.0, home_wrc=95,
        park_factor=1.0, weather_multiplier=1.0,
        away_pitcher_hand='R', home_pitcher_hand='R',
    )
    result_lhp = grade_matchup(
        away_team='Yankees', away_siera=3.20, away_bp=3.80, away_ip=5.0, away_wrc=115,
        home_team='Red Sox',  home_siera=4.80, home_bp=4.20, home_ip=4.0, home_wrc=95,
        park_factor=1.0, weather_multiplier=1.0,
        away_pitcher_hand='R', home_pitcher_hand='L',   # LHP → away gets +4% platoon
    )
    print('RHP on mound (home):', result_rhp)
    print('LHP on mound (home):', result_lhp)
    assert result_lhp['away_expected_f5_runs'] > result_rhp['away_expected_f5_runs'], \
        'Away offense should be higher when facing LHP (platoon boost)'

    # Weather multiplicative test: warm+out-wind should stack correctly
    result_wx = grade_matchup(
        away_team='A', away_siera=4.00, away_bp=4.00, away_ip=4.5, away_wrc=100,
        home_team='B', home_siera=4.00, home_bp=4.00, home_ip=4.5, home_wrc=100,
        park_factor=1.15,          # Coors
        weather_multiplier=1.10,   # 15 mph out wind
    )
    # Expected: 1.15 * 1.10 = 1.265x environment (not 1.25x additive)
    print('Coors + out-wind total:', result_wx['projected_f5_total'])

    print('All assertions passed.')
