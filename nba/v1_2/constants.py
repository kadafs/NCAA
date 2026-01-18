# NBA PPG+PED Hybrid Totals v1.2 Constants

# 1. League Baselines (NBA Gravity)
LEAGUE_AVG_PACE = 100.0
LEAGUE_AVG_EFF = 115.0

# 2. Pace Modifiers (Applied to Delta from 100.0)
PACE_MODIFIERS = {
    "PACE_DELTA_WEIGHT": 1.5,     # Aggressive weighting for NBA transitions
    "FAST_BREAK_ACCEL": 1.2,      # Bonus for top 5 pace teams
    "POST_ASG_DECEL": -1.0        # Historical late-season intensity drag
}

# 3. Efficiency Modifiers (Applied to Delta from 115.0)
EFF_MODIFIERS = {
    "EFF_DELTA_WEIGHT": 0.8,      # Scaled for 48-minute consistency
    "REGRESSION_FACTOR": 0.92,    # Percentage based regression to mean
    "HCA_TOTAL_BUMP": 2.5         # Additive points for non-neutral games
}

# 4. Pro Factors (Additive)
PRO_SITUATIONAL = {
    "THREE_PT_VOL_BOOST": 1.5,    # If 3PA > 40
    "THREE_PT_VOL_DRAG": -2.0,     # If 3PA < 30
    "B2B_FATIGUE_PENALTY": -2.0,  # Single team on Back-to-Back
    "DOUBLE_B2B_PENALTY": -4.0    # Both teams on Back-to-Back
}

# 5. Star Leverage (Injury Impact)
STAR_LEVERAGE = {
    "SUPERSTAR_OUT": -4.5,        # Tier 1 (All-NBA talent)
    "STAR_OUT": -2.5,             # Tier 2 (Primary starter)
    "ROTATION_OUT": -1.0          # Tier 3 (Utility player)
}

# 6. Classification Thresholds
THRESHOLDS = {
    "MODE_A": 7.5,
    "MODE_B": 4.5,
    "MIN_EDGE": 0.0
}
