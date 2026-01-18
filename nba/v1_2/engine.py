# NBA PPG+PED Hybrid Totals v1.2 Core Engine
import json
try:
    from .constants import (
        LEAGUE_AVG_PACE, LEAGUE_AVG_EFF, 
        PACE_MODIFIERS, EFF_MODIFIERS, 
        PRO_SITUATIONAL, STAR_LEVERAGE, 
        THRESHOLDS
    )
except (ImportError, ValueError):
    from constants import (
        LEAGUE_AVG_PACE, LEAGUE_AVG_EFF, 
        PACE_MODIFIERS, EFF_MODIFIERS, 
        PRO_SITUATIONAL, STAR_LEVERAGE, 
        THRESHOLDS
    )

class NBATotalsEngine:
    """
    Deterministic forecast engine for NBA basketball totals.
    Adapted for 48-minute pro-level efficiency and situational fatigue.
    """

    def __init__(self, mode="safe"):
        self.mode = mode.lower()
        self.trace = []

    def _log(self, message):
        self.trace.append(message)

    def calculate_total(self, game_data, injury_notes=None):
        """
        Main calculation pipeline v1.3.
        Transitioned to rate-based baseline and regression logic.
        """
        self.trace = [] # Reset trace
        
        # 1. Rate-Based Baseline (v1.3 Refinement)
        pace_adj = game_data.get('pace_adjustment', LEAGUE_AVG_PACE)
        eff_adj = game_data.get('efficiency_adjustment', LEAGUE_AVG_EFF)
        
        # Baseline = (Composite Efficiency * Pace) / 100 * 2 (for 2 teams)
        baseline = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1: Rate-Based Baseline ({eff_adj:.1f} Eff @ {pace_adj:.1f} Pace) = {baseline:.2f}")

        # 2. Statistics Dampeners & Regression
        total = baseline
        
        # Pace Acceleration (Delta from Pivot)
        pace_delta = pace_adj - LEAGUE_AVG_PACE
        pace_impact = pace_delta * PACE_MODIFIERS['PACE_DELTA_WEIGHT']
        total += pace_impact
        # self._log(f"Step 2: Pace Impact ({pace_adj:.1f}) -> {pace_impact:+.2f}")

        # Percentage-Based Regression (v1.3 Refinement)
        reg_factor = EFF_MODIFIERS.get('REGRESSION_FACTOR', 0.96)
        regressed_total = total * reg_factor
        self._log(f"Step 3: Regression Applied ({reg_factor}x) -> {regressed_total:.2f}")
        total = regressed_total

        # Home Court Advantage (v1.3 Refinement)
        hca_bump = 0
        if not game_data.get('is_neutral', False):
            hca_bump = EFF_MODIFIERS.get('HCA_TOTAL_BUMP', 2.5)
            total += hca_bump
            self._log(f"Step 3.5: Home Court Advantage -> +{hca_bump:.1f}")

        # 4. Pro Situational Factors (Step 4-5)
        situational_impact = 0
        
        # 3P Volume
        three_pa = game_data.get('three_pa_total', 70)
        if three_pa > 75:
            situational_impact += PRO_SITUATIONAL['THREE_PT_VOL_BOOST']
            self._log(f"Step 4: High 3P Volume ({three_pa:.1f}) -> +{PRO_SITUATIONAL['THREE_PT_VOL_BOOST']}")
        elif three_pa < 65:
            situational_impact += PRO_SITUATIONAL['THREE_PT_VOL_DRAG']
            self._log(f"Step 4: Low 3P Volume ({three_pa:.1f}) -> {PRO_SITUATIONAL['THREE_PT_VOL_DRAG']}")

        # Fatigue (B2B)
        if game_data.get('is_b2b_both'):
            situational_impact += PRO_SITUATIONAL['DOUBLE_B2B_PENALTY']
            self._log(f"Step 5: Double Back-to-Back -> {PRO_SITUATIONAL['DOUBLE_B2B_PENALTY']}")
        elif game_data.get('is_b2b_team') or game_data.get('is_b2b_opp'):
            situational_impact += PRO_SITUATIONAL['B2B_FATIGUE_PENALTY']
            self._log(f"Step 5: Fatigue (B2B) -> {PRO_SITUATIONAL['B2B_FATIGUE_PENALTY']}")

        total += situational_impact
        
        final_safe_total = total
        self._log(f"Safe Mode Result: {final_safe_total:.2f}")

        # 5. Star Leverage Layer (Full Mode Only)
        final_total = final_safe_total
        notes_applied = False

        if self.mode == "full" and injury_notes:
            star_impact = 0
            for note in injury_notes:
                # Basic heuristic for STAR exclusion in NBA
                st = note.get('status', '').lower()
                if "out" in st or "doubtful" in st:
                    # In a real model, we'd check player rank. 
                    # Here we default to "STAR_OUT" for identified players in notes.
                    star_impact += STAR_LEVERAGE['STAR_OUT']
            
            final_total += star_impact
            notes_applied = True
            self._log(f"Step 6: Star Leverage (Full Mode) -> {star_impact:+.2f}")

        # 6. Edge Calculation
        market = game_data.get('market_total', 230.0) # NBA Default
        edge = final_total - market
        
        # Classification
        mode_label = "NONE"
        if abs(edge) >= THRESHOLDS['MODE_A']:
            mode_label = "A"
        elif abs(edge) >= THRESHOLDS['MODE_B']:
            mode_label = "B"
            
        decision = "PLAY" if mode_label != "NONE" else "PASS"
        
        # Governance Enforcement: Notes cannot flip a PASS to a PLAY
        safe_edge = final_safe_total - market
        if mode_label != "NONE" and abs(safe_edge) < THRESHOLDS['MODE_B']:
            decision = "PASS (Governance Filter)"
            self._log("Governance: Decision reverted to PASS as Safe Mode edge was insufficient.")

        return {
            "final_model_total": round(final_total, 2),
            "safe_total": round(final_safe_total, 2),
            "market_total": market,
            "edge": round(edge, 2),
            "mode": mode_label,
            "decision": decision,
            "lean": "OVER" if edge > 0 else "UNDER" if edge < 0 else "NONE",
            "notes_applied": notes_applied,
            "trace": self.trace
        }
