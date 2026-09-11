"""
core/xgot_engine.py
===================
Empirical Expected Goals on Target (xGOT) & Goalkeeper Shot-Stopping Engine.
Calculates post-shot threat based on on-target attempts, box distribution,
and goalkeeper performance metrics.
"""

def calculate_xgot(
    shots_on_goal: int,
    total_shots: int = 0,
    shots_insidebox: int = 0,
    shots_outsidebox: int = 0,
    base_xg: float = None,
    goals: int = 0
) -> float:
    """
    Calculate Empirical Post-Shot Expected Goals on Target (xGOT).
    """
    sot = max(0, int(shots_on_goal or 0))
    g = max(0, int(goals or 0))
    
    if sot == 0:
        return round(float(g) * 0.75, 2) if g > 0 else 0.0

    tot = max(sot, int(total_shots or 0))
    ibox = max(0, int(shots_insidebox or 0))
    
    # Estimate on-target shots inside box vs outside box
    if ibox > 0 and tot > 0:
        box_ratio = min(1.0, ibox / tot)
        sot_inside = sot * box_ratio
        sot_outside = sot * (1.0 - box_ratio)
    else:
        # Standard distribution: 65% of shots on target originate inside the penalty box
        sot_inside = sot * 0.65
        sot_outside = sot * 0.35

    # Pre-shot quality multiplier
    if base_xg is not None and tot > 0 and base_xg > 0:
        avg_shot_quality = float(base_xg) / tot
        # Standard shot quality baseline is ~0.11 xG/shot
        quality_factor = max(0.70, min(1.45, avg_shot_quality / 0.11))
    else:
        quality_factor = 1.0

    # Inside-box on-target threat ~ 0.34; Outside-box on-target threat ~ 0.14
    val_inside = sot_inside * (0.34 * quality_factor)
    val_outside = sot_outside * (0.14 * quality_factor)
    raw_xgot = val_inside + val_outside

    # Reconcile with actual goals scored
    # A shot that became a goal represents a very high post-shot threat (0.70+ average)
    min_xgot_from_goals = g * 0.70
    reconciled_xgot = max(raw_xgot, min_xgot_from_goals)

    # Ceiling cap: cannot exceed shots on target * 0.95
    max_cap = sot * 0.95 + (0.3 if g > 0 else 0.0)
    final_xgot = min(reconciled_xgot, max_cap)

    return round(final_xgot, 2)


def evaluate_gk_shot_stopping(xgot_faced: float, goals_conceded: int) -> dict:
    """
    Calculate goalkeeper shot stopping metrics.
    goals_prevented = xgot_faced - goals_conceded
    """
    xgot = float(xgot_faced or 0.0)
    gc = int(goals_conceded or 0)
    prevented = round(xgot - gc, 2)
    
    tier = "NORMAL"
    if prevented >= 1.5:
        tier = "MASTERCLASS"
    elif prevented >= 0.8:
        tier = "STRONG"
    elif prevented <= -1.2:
        tier = "LEAKY"

    return {
        "xgot_faced": round(xgot, 2),
        "goals_conceded": gc,
        "goals_prevented": prevented,
        "performance_tier": tier
    }


def compute_match_xgot(
    home_stats: dict,
    away_stats: dict,
    goals_h: int,
    goals_a: int,
    pre_xg_home: float = None,
    pre_xg_away: float = None
) -> dict:
    """
    Compute full match xGOT and GK performance for both teams.
    home_stats & away_stats expect dicts with keys:
    - shots_on_goal
    - total_shots
    - shots_insidebox
    - shots_outsidebox
    - saves
    """
    hs = home_stats or {}
    as_ = away_stats or {}

    xgot_h = calculate_xgot(
        shots_on_goal=hs.get("shots_on_goal", 0),
        total_shots=hs.get("total_shots", 0),
        shots_insidebox=hs.get("shots_insidebox", 0),
        shots_outsidebox=hs.get("shots_outsidebox", 0),
        base_xg=pre_xg_home,
        goals=goals_h
    )

    xgot_a = calculate_xgot(
        shots_on_goal=as_.get("shots_on_goal", 0),
        total_shots=as_.get("total_shots", 0),
        shots_insidebox=as_.get("shots_insidebox", 0),
        shots_outsidebox=as_.get("shots_outsidebox", 0),
        base_xg=pre_xg_away,
        goals=goals_a
    )

    xgot_total = round(xgot_h + xgot_a, 2)

    # Home goalkeeper faces Away xGOT and concedes goals_a
    home_gk = evaluate_gk_shot_stopping(xgot_faced=xgot_a, goals_conceded=goals_a)
    # Away goalkeeper faces Home xGOT and concedes goals_h
    away_gk = evaluate_gk_shot_stopping(xgot_faced=xgot_h, goals_conceded=goals_h)

    # Finishing deltas (positive = clinical finish above xGOT)
    finishing_h = round(goals_h - xgot_h, 2)
    finishing_a = round(goals_a - xgot_a, 2)

    insights = []
    if away_gk["performance_tier"] == "MASTERCLASS":
        insights.append(f"AWAY_GK_MASTERCLASS (+{away_gk['goals_prevented']} prevented)")
    if home_gk["performance_tier"] == "MASTERCLASS":
        insights.append(f"HOME_GK_MASTERCLASS (+{home_gk['goals_prevented']} prevented)")
    if xgot_total >= 2.8 and (goals_h + goals_a) <= 1:
        insights.append("UNLUCKY_LOW_SCORING (High On-Target Threat)")
    if finishing_h >= 1.2 or finishing_a >= 1.2:
        insights.append("CLINICAL_FINISHING")

    return {
        "xgot_home": xgot_h,
        "xgot_away": xgot_a,
        "xgot_total": xgot_total,
        "home_gk_prevented": home_gk["goals_prevented"],
        "away_gk_prevented": away_gk["goals_prevented"],
        "home_gk_tier": home_gk["performance_tier"],
        "away_gk_tier": away_gk["performance_tier"],
        "home_finishing_delta": finishing_h,
        "away_finishing_delta": finishing_a,
        "insights": insights
    }
