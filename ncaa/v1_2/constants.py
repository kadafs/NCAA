# PPG+PED Hybrid Totals v1.2 Constants

# 1. Pace Modifiers (Applied to Delta from 68.0)
PACE_MODIFIERS = {
    "PACE_DELTA_WEIGHT": 0.8,     # Boost/Cut per unit of pace difference from avg
    "SLOW_TEAM_PENALTY": -2.5,    # Extra drag if a team is bottom 20% pace
    "BLOWOUT_DECEL": -1.5,        # Points reduced if spread > 15
    "CLOSE_SPREAD_ACCEL": 1.2     # Points added if spread < 3
}

# 2. Efficiency Modifiers (Applied to Delta from 105.0)
EFF_MODIFIERS = {
    "EFF_DELTA_WEIGHT": 0.6,      # Boost/Cut per unit of efficiency difference
    "STRONG_DEFENSE_DRAG": -3.0,  # If opponent def_eff < 95
    "ELITE_OFFENSE_BOOST": 2.0,   # If team off_eff > 115
    "SYSTEMIC_DAMPENER": -12.5    # Baseline reduction to ground PPG+PPG math
}

# 3. Turnover & Foul Factors (Additive)
GAME_FLOW = {
    "HIGH_TURNOVER_DRAG": -1.5,   # If TO% > 20%
    "HIGH_FOUL_BOOST": 2.0        # If FTR > 40
}

# 4. Conference Bias Normalization
CONF_BIAS = {
    # Power 6
    "ACC": 1.5, "B10": 1.5, "B12": 2.0, "BE": 1.5, "SEC": 2.0, "P12": 1.0,
    # Mid-Tier
    "Amer": 0.5, "MWC": 0.5, "A10": 0.5, "WCC": 0.5,
    # Low-Tier Fallback
    "DEFAULT": -1.0
}

# 5. Classification Thresholds
THRESHOLDS = {
    "MODE_A": 8.0,
    "MODE_B": 4.0,
    "MIN_EDGE": 0.0
}
