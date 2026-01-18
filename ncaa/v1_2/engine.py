# NCAA PPG+PED Hybrid Totals v1.2 Core Engine
import json
try:
    from .constants import PACE_MODIFIERS, EFF_MODIFIERS, GAME_FLOW, CONF_BIAS, THRESHOLDS
except (ImportError, ValueError):
    from constants import PACE_MODIFIERS, EFF_MODIFIERS, GAME_FLOW, CONF_BIAS, THRESHOLDS

class TotalsEngine:
    """
    Deterministic forecast engine for NCAA basketball totals.
    Implements Safe Mode (stats only) and Full Mode (stats + context).
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
        pace_adj = game_data.get('pace_adjustment', 68.0)
        eff_adj = game_data.get('efficiency_adjustment', 105.0)
        
        # Baseline = (Composite Efficiency * Pace) / 100 * 2 (for 2 teams)
        baseline = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1: Rate-Based Baseline ({eff_adj:.1f} Eff @ {pace_adj:.1f} Pace) = {baseline:.2f}")

        # 2. Statistics Dampeners & Regression
        total = baseline
        
        # Pace Adjustment (Delta from 68.0)
        pace_impact = (pace_adj - 68.0) * PACE_MODIFIERS['PACE_DELTA_WEIGHT']
        total += pace_impact
        # self._log(f"Step 2: Pace Impact ({pace_adj:.1f}) -> {pace_impact:+.2f}")

        # Efficiency Modifiers (Additive logic for elite/strong)
        eff_mod = 0
        if game_data.get('is_elite_offense'): eff_mod += EFF_MODIFIERS['ELITE_OFFENSE_BOOST']
        if game_data.get('is_strong_defense'): eff_mod += EFF_MODIFIERS['STRONG_DEFENSE_DRAG']
        
        total += eff_mod
        
        # Percentage-Based Regression (v1.3 Refinement)
        reg_factor = EFF_MODIFIERS.get('REGRESSION_FACTOR', 0.97)
        regressed_total = total * reg_factor
        self._log(f"Step 3: Regression Applied ({reg_factor}x) -> {regressed_total:.2f}")
        total = regressed_total

        # Home Court Advantage (v1.3 Refinement)
        hca_bump = 0
        if not game_data.get('is_neutral', False):
            hca_bump = EFF_MODIFIERS.get('HCA_TOTAL_BUMP', 3.0)
            total += hca_bump
            self._log(f"Step 3.5: Home Court Advantage -> +{hca_bump:.1f}")

        # Game Flow (Turnovers/Fouls)
        flow_impact = 0
        if game_data.get('turnover_adjustment', 0) > 20: 
            flow_impact += GAME_FLOW['HIGH_TURNOVER_DRAG']
        if game_data.get('foul_adjustment', 0) > 35:
            flow_impact += GAME_FLOW['HIGH_FOUL_BOOST']
        
        total += flow_impact
        self._log(f"Step 4: Game Flow (TO/Fouls) Impact -> {flow_impact:.2f}")

        # 3. Conference Bias (Step 5)
        conf = game_data.get('conf', 'DEFAULT')
        bias = CONF_BIAS.get(conf, CONF_BIAS['DEFAULT'])
        total += bias
        self._log(f"Step 5: Conference Bias ({conf}) -> {bias:+.1f}")

        final_safe_total = total
        self._log(f"Safe Mode Result: {final_safe_total:.2f}")

        # 4. Context Layer (Full Mode Only)
        final_total = final_safe_total
        notes_applied = False

        if self.mode == "full" and injury_notes:
            context_adj = 0
            for note in injury_notes:
                # Logic to parse injury impact from notes
                # This could be star player out (-3 pts) etc.
                if "out" in note.get('status', '').lower():
                    context_adj -= 1.5 # Simplified baseline impact per player
            
            final_total += context_adj
            notes_applied = True
            self._log(f"Step 6: Contextual Adjustments (Full Mode) -> {context_adj:+.2f}")

        # 5. Edge Calculation
        market = game_data.get('market_total', 0)
        edge = final_total - market
        
        # Classification
        mode_label = "NONE"
        if abs(edge) >= THRESHOLDS['MODE_A']:
            mode_label = "A"
        elif abs(edge) >= THRESHOLDS['MODE_B']:
            mode_label = "B"
            
        decision = "PLAY" if mode_label != "NONE" else "PASS"
        
        # Section 6.3 Enforcement: Notes cannot flip a PASS to a PLAY
        safe_edge = final_safe_total - market
        if mode_label != "NONE" and abs(safe_edge) < THRESHOLDS['MODE_B']:
            decision = "PASS (Contextual Filter)"
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
