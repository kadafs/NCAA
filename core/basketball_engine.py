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
        market_val = game_data.get('market_total')
        if market_val is None:
            # Safety defaults if market is missing
            market = 230.0 if c.get('name') == 'NBA' else 145.5
        else:
            market = float(market_val)
        
        # --- PHASE 1: SHARED STATISTICAL BASELINE ---
        pace_adj = game_data.get('pace_adjustment', c['pace_pivot'])
        
        # Step 0: Pace Multiplier
        pace_mult = c.get('conf_pace_multipliers', {}).get(conf, c.get('conf_pace_multipliers', {}).get('DEFAULT', 1.0))
        if pace_mult != 1.0:
            pace_adj *= pace_mult
            self._log(f"Step 0: Pace Multiplier ({conf}) -> {pace_adj:.1f}")

        eff_adj = game_data.get('efficiency_adjustment', c['eff_pivot'])
        
        # Formula: ((Off + Def) / 2 * Pace) / 100 * 2
        legacy_baseline = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1: Raw Baseline ({eff_adj:.1f} Eff @ {pace_adj:.1f} Pace) = {legacy_baseline:.2f}")

        # Impact & Regression
        stats_total = legacy_baseline
        pace_delta = pace_adj - c['pace_pivot']
        pace_impact = pace_delta * c['pace_delta_weight']
        stats_total += pace_impact
        self._log(f"Step 2: Pace Impact ({pace_adj:.1f} vs {c['pace_pivot']}) -> {pace_impact:+.2f}")
        
        # Eff Modifiers (Basic/Conservative)
        eff_mod = 0
        if game_data.get('is_elite_offense'): 
            eff_mod += 2.0
            self._log("Step 2b: Elite Offense Factor -> +2.0")
        if game_data.get('is_strong_defense'): 
            eff_mod -= 3.0
            self._log("Step 2c: Strong Defense Drag -> -3.0")
        stats_total += eff_mod
        
        # Regression
        reg_factor = c.get('regression_factor', 0.97)
        stats_total *= reg_factor
        self._log(f"Step 3: Regression Applied ({reg_factor}) -> {stats_total:.2f}")
        
        # Situational (Standard)
        if not game_data.get('is_neutral', False):
            hca = c.get('hca_total_bump', 0)
            stats_total += hca
            self._log(f"Step 4: Home Court Advantage -> {hca:+.1f}")
            
        cb = c.get('conf_bias', {}).get(conf, c.get('conf_bias', {}).get('DEFAULT', 0))
        if cb != 0:
            stats_total += cb
            self._log(f"Step 5: Conference Bias ({conf}) -> {cb:+.1f}")

        # Basic Sharp additions allowed in SAFE (Pace/Possession)
        if sp.get('possession_bonus_value'):
            if game_data.get('is_rebound_mismatch') or game_data.get('is_turnover_mismatch'):
                stats_total += sp['possession_bonus_value']
                self._log(f"Step 6: Possession Bonus -> +{sp['possession_bonus_value']}")
        
        if sp.get('high_pace_threshold'):
            if pace_adj > sp['high_pace_threshold']:
                bonus = (pace_adj - sp['high_pace_threshold']) * sp.get('high_pace_efficiency_multiplier', 0.1)
                stats_total += bonus
                self._log(f"Step 7: High Pace Bonus -> +{bonus:.2f}")

        self._log(f"--- Shared Stats Baseline: {stats_total:.2f} ---")
        
        # FINAL SAFE TOTAL
        legacy_total = stats_total 

        # --- PHASE 2: FULL MODE LAYER (BOOSTERS & INJURIES) ---
        sharp_total = stats_total
        notes = []
        
        if self.mode == "full":
            self._log("--- Applying Sharp Situational Boosters (FULL MODE) ---")
            
            # 1. 3PT Volume (NBA Specific)
            if c['name'] == "NBA" and sp.get('three_pa_threshold'):
                three_pa = game_data.get('three_pa_total', 70)
                if three_pa > sp['three_pa_threshold']:
                    bonus = (three_pa - sp['three_pa_threshold']) * 0.05
                    sharp_total += bonus
                    self._log(f"Sharp 3: 3PT Volume Bonus -> +{bonus:.2f}")

            # 2. Situational Modifiers (Elite Offense, Blowout, Close Game)
            projected_spread = abs(game_data.get('projected_spread', 10.0))
            current_lean = "OVER" if sharp_total > market else "UNDER"

            if c['name'] == "NCAA":
                # A. Elite Offense
                off_threshold = sp.get('elite_offense_rating_threshold', 118.0)
                if game_data.get('statsA', {}).get('adj_off', 110) + game_data.get('statsH', {}).get('adj_off', 110) > off_threshold * 2:
                    bonus = sp.get('elite_offense_boost', 3.0)
                    sharp_total += bonus
                    self._log(f"Sharp 4A: Elite Offense Boost -> +{bonus:.2f}")
                    notes.append(f"Sharp Adjustment: Elite Offense Booster (+{bonus:.1f} pts)")
                # B. Blowout Volatility
                spread_threshold = sp.get('blowout_spread_threshold', 9.0)
                if projected_spread > spread_threshold:
                    penalty = sp.get('blowout_under_penalty', 3.5) if current_lean == "UNDER" else sp.get('blowout_over_boost', 2.5)
                    sharp_total += penalty
                    self._log(f"Sharp 4B: Blowout Adjustment -> +{penalty}")
                    notes.append(f"Sharp Adjustment: Blowout Volatility Correction (+{penalty:.1f} pts)")
                # C. Close Game
                if projected_spread < sp.get('close_game_threshold', 4.5):
                    bonus = sp.get('close_game_foul_bonus', 1.8)
                    sharp_total += bonus
                    self._log(f"Sharp 4C: Close Game Foul Correction -> +{bonus}")
                    notes.append(f"Sharp Adjustment: Close Game Foul Bonus (+{bonus:.1f} pts)")

            if c['name'] == "NBA":
                # A. Elite Offense
                off_threshold = sp.get('elite_offense_rating_threshold', 121.0)
                sA_off = game_data.get('statsA', {}).get('adj_off', 115)
                sH_off = game_data.get('statsH', {}).get('adj_off', 115)
                if sA_off + sH_off > off_threshold * 2:
                    bonus = sp.get('elite_offense_boost', 4.5)
                    sharp_total += bonus
                    self._log(f"Sharp NBA 5A: Elite Offense Boost -> +{bonus:.2f}")
                    notes.append(f"Sharp Adjustment: Elite Offense Booster (+{bonus:.1f} pts)")
                # B. Blowout Volatility
                spread_threshold = sp.get('blowout_spread_threshold', 12.0)
                if projected_spread > spread_threshold:
                    penalty = sp.get('blowout_under_penalty', 5.0) if current_lean == "UNDER" else sp.get('blowout_over_boost', 3.5)
                    sharp_total += penalty
                    self._log(f"Sharp NBA 5B: Blowout Adjustment -> +{penalty}")
                    notes.append(f"Sharp Adjustment: Blowout Volatility Correction (+{penalty:.1f} pts)")
                # C. Close Game
                if projected_spread < sp.get('close_game_threshold', 4.5):
                    bonus = sp.get('close_game_foul_bonus', 2.5)
                    sharp_total += bonus
                    self._log(f"Sharp NBA 5C: Close Game Foul Correction -> +{bonus}")
                    notes.append(f"Sharp Adjustment: Close Game Foul Bonus (+{bonus:.1f} pts)")

            # 3. Injury Impact (FULL MODE ONLY)
            star_impact = 0
            if injury_notes:
                self._log("--- Calculating Context Impact (Injuries) ---")
                for note in injury_notes:
                    st = note.get('status', '').lower()
                    if "out" in st or "doubtful" in st:
                        star_impact += c.get('star_leverage', {}).get('star_out', -2.5)
                
                # Apply Cap
                impact_cap = sp.get('injury_impact_cap')
                if impact_cap and abs(star_impact) > impact_cap:
                    self._log(f"Injury Impact capped: {star_impact:.2f} -> -{impact_cap:.2f}")
                    star_impact = -impact_cap

                sharp_total += star_impact
                self._log(f"Context Impact Applied: {star_impact:+.2f}")
                if star_impact != 0:
                    notes.append(f"Context Impact: {star_impact:+.1f} pts (Injury Related)")

            # 4. Compare tracks and add explanatory notes if Full < Safe
            if sharp_total < stats_total:
                diff = round(stats_total - sharp_total, 1)
                notes.append(f"Full Mode correction: Injury drag ({abs(star_impact)}) outweighing situational boosters. Total lowered by {diff} pts relative to baseline.")

        # --- PHASE 3: FINALIZATION & CLAMPING ---
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

        final_total = sharp_total
        final_edge = abs(final_total - market)
        
        decision = "PLAY" if final_edge >= c['thresholds']['mode_b'] else "PASS"
        
        # NCAA FULL Mode Overrides (v1.4)
        confidence = "LOW"
        if self.mode == "full" and c['name'] == "NCAA":
            cutoff = c['thresholds'].get('small_edge_cutoff', 0)
            if final_edge < cutoff:
                decision = "PASS"
                notes.append(f"Auto-Pass: Edge ({final_edge:.1f}) below threshold ({cutoff})")
                confidence = "NO PLAY"
            else:
                if final_edge >= 8.0: confidence = "HIGH"
                elif final_edge >= 5.0: confidence = "MEDIUM"
                else: confidence = "LOW"
                if final_edge < c['thresholds']['mode_b']: decision = "PASS"
        else:
            confidence = "HIGH" if final_edge >= c['thresholds']['mode_a'] else "MEDIUM" if final_edge >= c['thresholds']['mode_b'] else "LOW"

        return {
            "final_model_total": round(final_total, 2),
            "legacy_total": round(legacy_total, 2), # SAFE Result
            "sharp_total": round(sharp_total, 2),   # FULL Result
            "market_total": market,
            "edge": round(final_total - market, 2),
            "legacy_edge": round(legacy_total - market, 2),
            "mode": "A" if final_edge >= c['thresholds']['mode_a'] else "B" if final_edge >= c['thresholds']['mode_b'] else "NONE",
            "decision": decision,
            "lean": "OVER" if (final_total - market) > 0 else "UNDER",
            "confidence": confidence,
            "notes": notes,
            "trace": self.trace
        }

