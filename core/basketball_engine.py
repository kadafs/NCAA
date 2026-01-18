# Universal Basketball Engine v1.4
import json
import os

class UniversalBasketballEngine:
    """
    League-agnostic deterministic forecast engine.
    Uses rate-based efficiency math scaled by game duration.
    """

    def __init__(self, config_path, mode="safe"):
        self.mode = mode.lower()
        self.trace = []
        self.config = self._load_config(config_path)
        
    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path, "r") as f:
            return json.load(f)

    def _log(self, message):
        self.trace.append(message)

    def calculate_total(self, game_data, injury_notes=None):
        self.trace = []
        c = self.config
        
        # 0. Time Scaling Factor (Normalize to Pivot duration)
        # If league is 40m but we have 48m data (rare) or vice versa.
        # Most data is already per-session, but pace is per-duration.
        
        # 1. Rate-Based Baseline (Step 1)
        pace_adj = game_data.get('pace_adjustment', c['pace_pivot'])
        eff_adj = game_data.get('efficiency_adjustment', c['eff_pivot'])
        
        # Formula: ((Off + Def) / 2 * Pace) / 100 * 2
        baseline = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1: Rate-Based Baseline ({eff_adj:.1f} Eff @ {pace_adj:.1f} Pace) = {baseline:.2f}")

        # 2. Statistics Dampeners & Regression
        total = baseline
        
        # Pace Adjustment (Delta from Pivot)
        pace_delta = pace_adj - c['pace_pivot']
        pace_impact = pace_delta * c['pace_delta_weight']
        total += pace_impact
        self._log(f"Step 2: Pace Impact ({pace_adj:.1f} vs {c['pace_pivot']}) -> {pace_impact:+.2f}")

        # Efficiency Modifiers (Additive logic)
        eff_mod = 0
        if game_data.get('is_elite_offense'): 
            eff_mod += c.get('situational', {}).get('ELITE_OFFENSE_BOOST', 2.0)
        if game_data.get('is_strong_defense'): 
            eff_mod += c.get('situational', {}).get('STRONG_DEFENSE_DRAG', -3.0)
        
        total += eff_mod
        
        # Percentage-Based Regression
        reg_factor = c['regression_factor']
        regressed_total = total * reg_factor
        self._log(f"Step 3: Regression Applied ({reg_factor}x) -> {regressed_total:.2f}")
        total = regressed_total

        # 3. Situational Factors (League-Specific)
        sit_total = 0
        
        # Home Court Advantage
        if not game_data.get('is_neutral', False):
            hca = c.get('hca_total_bump', 0)
            sit_total += hca
            self._log(f"Step 4: Home Court Advantage -> +{hca:.1f}")
            
        # 3P Volume (NBA specific example)
        if c['name'] == "NBA":
            three_pa = game_data.get('three_pa_total', 70)
            if three_pa > 75: sit_total += c['situational']['three_pt_vol_boost']
            elif three_pa < 65: sit_total += c['situational']['three_pt_vol_drag']
            
        # Fatigue / B2B
        if game_data.get('is_b2b_both'): sit_total += c['situational'].get('double_b2b_penalty', 0)
        elif game_data.get('is_b2b_team') or game_data.get('is_b2b_opp'):
            sit_total += c['situational'].get('b2b_fatigue_penalty', 0)
            
        # Conference Bias (NCAA)
        if c['name'] == "NCAA":
            conf = game_data.get('conf', 'DEFAULT')
            bias = c.get('conf_bias', {}).get(conf, c.get('conf_bias', {}).get('DEFAULT', 0))
            sit_total += bias
            self._log(f"Step 5: Conference Bias ({conf}) -> {bias:+.1f}")

        total += sit_total
        
        final_safe_total = total
        self._log(f"Safe Mode Result: {final_safe_total:.2f}")

        # 4. Context Layer (Full Mode)
        final_total = final_safe_total
        notes_applied = False
        
        if self.mode == "full" and injury_notes:
            star_impact = 0
            for note in injury_notes:
                st = note.get('status', '').lower()
                if "out" in st or "doubtful" in st:
                    # Use league star leverage
                    star_impact += c.get('star_leverage', {}).get('star_out', -2.5)
            
            final_total += star_impact
            notes_applied = True
            self._log(f"Step 6: Contextual Adjustment (Full) -> {star_impact:+.2f}")

        # 5. Result Object
        market = game_data.get('market_total', 0)
        edge = final_total - market
        
        # Classification
        mode_label = "NONE"
        if abs(edge) >= c['thresholds']['mode_a']: mode_label = "A"
        elif abs(edge) >= c['thresholds']['mode_b']: mode_label = "B"
            
        decision = "PLAY" if mode_label != "NONE" else "PASS"
        
        # Governance
        safe_edge = final_safe_total - market
        if mode_label != "NONE" and abs(safe_edge) < c['thresholds']['mode_b']:
            decision = "PASS (Governance Filter)"
            self._log("Governance: Safe Mode edge insufficient.")

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
