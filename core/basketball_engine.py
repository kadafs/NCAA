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
        sp = c.get('sharp_params', {})
        
        # 0. Context Extraction
        conf = game_data.get('conf', 'DEFAULT')
        
        # --- LEGACY MATH TRACK (Original Status Quo) ---
        pace_adj = game_data.get('pace_adjustment', c['pace_pivot'])
        pace_mult = c.get('conf_pace_multipliers', {}).get(conf, c.get('conf_pace_multipliers', {}).get('DEFAULT', 1.0))
        if pace_mult != 1.0:
            pace_adj *= pace_mult
            self._log(f"Step 0: Pace Multiplier ({conf}) -> {pace_adj:.1f}")

        eff_adj = game_data.get('efficiency_adjustment', c['eff_pivot'])
        
        # Baseline: ((Off + Def) / 2 * Pace) / 100 * 2
        legacy_baseline = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1 (Legacy): Baseline = {legacy_baseline:.2f}")

        # Impact & Regression
        legacy_total = legacy_baseline
        pace_delta = pace_adj - c['pace_pivot']
        legacy_total += pace_delta * c['pace_delta_weight']
        
        # Situational
        eff_mod = 0
        if game_data.get('is_elite_offense'): eff_mod += 2.0
        if game_data.get('is_strong_defense'): eff_mod -= 3.0
        legacy_total += eff_mod
        
        legacy_total *= c['regression_factor']
        
        # Final Legacy Result
        if not game_data.get('is_neutral', False):
            legacy_total += c.get('hca_total_bump', 0)
        
        # --- SHARP MATH TRACK (Experimental Improvements) ---
        sharp_total = legacy_total # Start with legacy as base
        
        # 1. Possession Multiplier (ORB% / TOV% Impact)
        # Assuming game_data might have 'off_reb_pct' or 'tov_pct' in the future
        # For now, we'll use a placeholder logic that looks for 'rebound_mismatch'
        if game_data.get('is_rebound_mismatch'):
            bonus = sp.get('possession_bonus_value', 2.0)
            sharp_total += bonus
            self._log(f"Sharp Step 1: Possession Bonus -> +{bonus:.1f}")

        # 2. High Pace Efficiency Bonus (Non-linear collapsing defense)
        high_pace_thresh = sp.get('high_pace_threshold', 1000) # Default high to disable
        if pace_adj > high_pace_thresh:
            excess_pace = pace_adj - high_pace_thresh
            pace_bonus = excess_pace * sp.get('high_pace_efficiency_multiplier', 0.2)
            sharp_total += pace_bonus
            self._log(f"Sharp Step 2: High Pace Bonus -> +{pace_bonus:.2f}")

        # 3. NBA 3PT Frequency Ratio
        if c['name'] == "NBA":
            three_pa_freq = game_data.get('three_pa_freq', 0)
            if three_pa_freq > sp.get('three_pt_freq_threshold', 0.42):
                boost = sp.get('three_pt_freq_regression_boost', 0.02)
                # Reverse some of the regression
                regression_recovery = legacy_total * boost
                sharp_total += regression_recovery
                self._log(f"Sharp Step 3: 3PT Freq Regression Recovery -> +{regression_recovery:.2f}")

        # 4. NCAA Close Game Foul Correction
        if c['name'] == "NCAA":
            projected_spread = abs(game_data.get('projected_spread', 10.0))
            if projected_spread < sp.get('close_game_threshold', 4.5):
                foul_bonus = sp.get('close_game_foul_bonus', 1.8)
                sharp_total += foul_bonus
                self._log(f"Sharp Step 4: Close Game Foul Bonus -> +{foul_bonus:.1f}")

        # Clamping & Context apply to both tracks in this engine version
        # but the USER specifically wants FULL mode to show the new logic.
        
        # Clamping
        market = game_data.get('market_total', 0)
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

