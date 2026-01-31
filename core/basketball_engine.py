# Universal Basketball Engine v1.4
import json
import os
from datetime import datetime

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
        self.trace = [f"Audit Session: {datetime.now().strftime('%H:%M:%S')}"]
        c = self.config
        sp = c.get('sharp_params', {})
        conf = game_data.get('conf', 'DEFAULT')
        market = float(game_data.get('market_total', 145.5))
        
        # --- LEGACY MATH TRACK (Original Status Quo) ---
        pace_adj = game_data.get('pace_adjustment', c['pace_pivot'])
        
        # Step 0: Pace Multiplier
        pace_mult = c.get('conf_pace_multipliers', {}).get(conf, c.get('conf_pace_multipliers', {}).get('DEFAULT', 1.0))
        if pace_mult != 1.0:
            pace_adj *= pace_mult
            self._log(f"Step 0: Pace Multiplier ({conf}) -> {pace_adj:.1f}")

        eff_adj = game_data.get('efficiency_adjustment', c['eff_pivot'])
        
        # Formula: ((Off + Def) / 2 * Pace) / 100 * 2
        legacy_baseline = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1 (Legacy): Baseline ({eff_adj:.1f} Eff @ {pace_adj:.1f} Pace) = {legacy_baseline:.2f}")

        # Impact & Regression
        legacy_total = legacy_baseline
        pace_delta = pace_adj - c['pace_pivot']
        pace_impact = pace_delta * c['pace_delta_weight']
        legacy_total += pace_impact
        self._log(f"Step 2: Pace Impact ({pace_adj:.1f} vs {c['pace_pivot']}) -> {pace_impact:+.2f}")
        
        # Eff Modifiers
        eff_mod = 0
        if game_data.get('is_elite_offense'): 
            eff_mod += 2.0
            self._log("Step 2b: Elite Offense Bonus -> +2.0")
        if game_data.get('is_strong_defense'): 
            eff_mod -= 3.0
            self._log("Step 2c: Strong Defense Drag -> -3.0")
        legacy_total += eff_mod
        
        # Regression
        reg_factor = c.get('regression_factor', 0.97)
        old_val = legacy_total
        legacy_total *= reg_factor
        self._log(f"Step 3: Regression Applied ({reg_factor}) -> {legacy_total:.2f}")
        
        # Situational
        if not game_data.get('is_neutral', False):
            hca = c.get('hca_total_bump', 0)
            legacy_total += hca
            self._log(f"Step 4: Home Court Advantage -> {hca:+.1f}")
            
        cb = c.get('conf_bias', {}).get(conf, c.get('conf_bias', {}).get('DEFAULT', 0))
        if cb != 0:
            legacy_total += cb
            self._log(f"Step 5: Conference Bias ({conf}) -> {cb:+.1f}")

        self._log(f"Step 6: Final Legacy Result -> {legacy_total:.2f}")

        # --- SHARP MATH TRACK (Experimental Improvements) ---
        sharp_total = legacy_total  # Start with legacy as base
        
        if self.mode == "full":
            self._log("--- Applying Sharp Adjustments ---")
            
            # 1. Possession Multiplier (Sharp Adjustment)
            if sp.get('possession_bonus_value'):
                if game_data.get('is_rebound_mismatch') or game_data.get('is_turnover_mismatch'):
                    sharp_total += sp['possession_bonus_value']
                    self._log(f"Sharp 1: Possession Bonus -> +{sp['possession_bonus_value']}")
            
            # 2. High Pace Efficiency Bonus
            if sp.get('high_pace_threshold'):
                if pace_adj > sp['high_pace_threshold']:
                    bonus = (pace_adj - sp['high_pace_threshold']) * sp.get('high_pace_efficiency_multiplier', 0.1)
                    sharp_total += bonus
                    self._log(f"Sharp 2: High Pace Bonus ({pace_adj:.1f} > {sp['high_pace_threshold']}) -> +{bonus:.2f}")

            # 3. NBA 3PT Frequency Ratio
            if c['name'] == "NBA" and sp.get('three_pa_threshold'):
                three_pa = game_data.get('three_pa_total', 70)
                if three_pa > sp['three_pa_threshold']:
                    bonus = (three_pa - sp['three_pa_threshold']) * 0.05
                    sharp_total += bonus
                    self._log(f"Sharp 3: 3PT Volume Bonus ({three_pa} > {sp['three_pa_threshold']}) -> +{bonus:.2f}")

            # 4. NCAA Close Game Foul Correction
            if c['name'] == "NCAA":
                projected_spread = abs(game_data.get('projected_spread', 10.0))
                if projected_spread < sp.get('close_game_threshold', 4.5):
                    sharp_total += sp.get('close_game_foul_bonus', 1.5)
                    self._log(f"Sharp 4: Close Game Foul Correction ({projected_spread:.1f} < {sp.get('close_game_threshold')}) -> +{sp.get('close_game_foul_bonus')}")

            if sharp_total == legacy_total:
                self._log("No Sharp Adjustments triggered.")
        else:
            # We still need to calculate the sharp_total for the return dict even if not logging
            # (Though in Safe mode the dashboard might not use it, the return dict expects it)
            if sp.get('possession_bonus_value'):
                if game_data.get('is_rebound_mismatch') or game_data.get('is_turnover_mismatch'):
                    sharp_total += sp['possession_bonus_value']
            
            if sp.get('high_pace_threshold'):
                if pace_adj > sp['high_pace_threshold']:
                    sharp_total += (pace_adj - sp['high_pace_threshold']) * sp.get('high_pace_efficiency_multiplier', 0.1)

            if c['name'] == "NBA" and sp.get('three_pa_threshold'):
                three_pa = game_data.get('three_pa_total', 70)
                if three_pa > sp['three_pa_threshold']:
                    sharp_total += (three_pa - sp['three_pa_threshold']) * 0.05

            if c['name'] == "NCAA":
                projected_spread = abs(game_data.get('projected_spread', 10.0))
                if projected_spread < sp.get('close_game_threshold', 4.5):
                    sharp_total += sp.get('close_game_foul_bonus', 1.5)

        # Clamping & Context apply to both tracks in this engine version
        # but the USER specifically wants FULL mode to show the new logic.
        
        # Clamping
        # market = game_data.get('market_total', 0) # Already defined at the top
        threshold = c.get('volatility_threshold', 15.0)
        
        def clamp_total(val, mkt):
            edge = val - mkt
            if abs(edge) > threshold:
                excess = abs(edge) - threshold
                clamped_excess = excess * c.get('volatility_dampener', 0.7)
                multiplier = 1 if edge > 0 else -1
                return mkt + (multiplier * (threshold + clamped_excess))
            return val

        legacy_total = clamp_total(legacy_total, market)
        sharp_total = clamp_total(sharp_total, market)

        # Star Impact (Full Mode Only)
        star_impact = 0
        if self.mode == "full" and injury_notes:
            for note in injury_notes:
                st = note.get('status', '').lower()
                if "out" in st or "doubtful" in st:
                    star_impact += c.get('star_leverage', {}).get('star_out', -2.5)
            legacy_total += star_impact
            sharp_total += star_impact
            self._log(f"Context Impact: {star_impact:+.2f}")

        # Final decision logic uses Sharp if in Full mode or Legacy if in Safe
        # To maintain the Dashboard behavior: we return ALL and let bridge pick.
        return {
            "final_model_total": round(sharp_total, 2), # Default sharp for full
            "legacy_total": round(legacy_total, 2),
            "sharp_total": round(sharp_total, 2),
            "market_total": market,
            "edge": round(sharp_total - market, 2),
            "legacy_edge": round(legacy_total - market, 2),
            "mode": "A" if abs(sharp_total - market) >= c['thresholds']['mode_a'] else "B" if abs(sharp_total - market) >= c['thresholds']['mode_b'] else "NONE",
            "decision": "PLAY" if abs(sharp_total - market) >= c['thresholds']['mode_b'] else "PASS",
            "lean": "OVER" if (sharp_total - market) > 0 else "UNDER",
            "trace": self.trace
        }

