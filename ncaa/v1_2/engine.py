# NCAA PPG+PED Hybrid Totals v1.2 Core Engine
import json
from .constants import PACE_MODIFIERS, EFF_MODIFIERS, GAME_FLOW, CONF_BIAS, THRESHOLDS

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
        Main calculation pipeline.
        game_data should be a dictionary containing the 'Master Input' columns.
        """
        self.trace = [] # Reset trace
        
        # 1. Baseline Total (Step 1)
        team_ppg = game_data.get('team_ppg', 0)
        opp_ppg = game_data.get('opp_ppg', 0)
        baseline = team_ppg + opp_ppg
        self._log(f"Step 1: Baseline Total (PPG + PPG) = {team_ppg} + {opp_ppg} = {baseline:.1f}")

        # 2. Statistics Dampeners (Steps 2-4)
        total = baseline
        
        # Pace Adjustment (Delta from 68.0)
        pace_adj = game_data.get('pace_adjustment', 68.0)
        pace_impact = (pace_adj - 68.0) * PACE_MODIFIERS['PACE_DELTA_WEIGHT']
        total += pace_impact
        self._log(f"Step 2: Pace Adjustment ({pace_adj:.1f}) -> Impact: {pace_impact:+.2f}")

        # Efficiency Adjustment (Delta from 105.0)
        eff_adj = game_data.get('efficiency_adjustment', 105.0)
        eff_impact = (eff_adj - 105.0) * EFF_MODIFIERS['EFF_DELTA_WEIGHT']
        
        # Static Modifiers
        eff_impact += EFF_MODIFIERS['SYSTEMIC_DAMPENER']
        if game_data.get('is_elite_offense'): eff_impact += EFF_MODIFIERS['ELITE_OFFENSE_BOOST']
        if game_data.get('is_strong_defense'): eff_impact += EFF_MODIFIERS['STRONG_DEFENSE_DRAG']
        
        total += eff_impact
        self._log(f"Step 3: Efficiency Impact -> {eff_impact:+.2f}")

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
