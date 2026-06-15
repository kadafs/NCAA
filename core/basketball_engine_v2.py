import json
import os
from datetime import datetime

class UniversalBasketballEngineV2:
    """
    League-agnostic deterministic forecast engine.
    Uses rate-based efficiency math scaled by game duration.
    Optimized v1.5: Fixed nesting bugs, unified regression, corrected sharp layers.
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
        
        sH = game_data.get('statsH', {})
        sA = game_data.get('statsA', {})
        
        league_avg = c.get('_avg_total', 225.0 if c.get('name') == 'NBA' else 145.5)
        market = float(market_val) if market_val is not None else league_avg
        
        # --- PHASE 1: STATISTICAL FOUNDATION ---
        pace_adj = game_data.get('pace_adjustment', c['pace_pivot'])
        
        # Step 0: Pace Multiplier
        pace_mult = c.get('conf_pace_multipliers', {}).get(conf, c.get('conf_pace_multipliers', {}).get('DEFAULT', 1.0))
        if pace_mult != 1.0:
            pace_adj *= pace_mult
            self._log(f"Step 0: Pace Multiplier ({conf}) -> {pace_adj:.1f}")

        eff_adj = game_data.get('efficiency_adjustment', c['eff_pivot'])
        
        # Step 1: Base Total Formula
        stats_total = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1: Base Total ({eff_adj:.1f} Eff @ {pace_adj:.1f} Pace) = {stats_total:.2f}")
        self._log(f"Step 2: Pace Impact DISABLED (pace embedded multiplicatively)")
        
        # Step 3: Alignment (Conf & HCA)
        if not game_data.get('is_neutral', False):
            hca = c.get('hca_total_bump', 0)
            stats_total += hca
            self._log(f"Step 3: Home Court Advantage -> +{hca:.1f}")
            
        cb = c.get('conf_bias', {}).get(conf, c.get('conf_bias', {}).get('DEFAULT', 0))
        if pace_mult != 1.0 and cb != 0:
            reduction = 0.5
            cb = cb - reduction if cb > 0 else cb + reduction
            self._log(f"Step 3b: Conf Bias Sync Gate -> Bias adjusted to {cb:+.1f}")
        
        if cb != 0:
            stats_total += cb
            self._log(f"Step 3c: Conference Bias ({conf}) -> {cb:+.1f}")

        # Step 4: UNIFIED REGRESSION (Linear blend-to-mean avoids downward bias)
        if c['name'] == "NBA":
            if stats_total < 215: reg_factor = 0.99
            elif stats_total <= 235: reg_factor = 0.97
            elif stats_total <= 250: reg_factor = 0.95
            else: reg_factor = 0.94
            # Fix: Linear blend for NBA instead of purely multiplying out
            stats_total = stats_total * reg_factor + league_avg * (1 - reg_factor)
            self._log(f"Step 4: NBA Stepped Blend Regression ({reg_factor}) -> {stats_total:.2f}")
        else:
            reg_factor = c.get('regression_factor', 0.97)
            stats_total = stats_total * reg_factor + league_avg * (1 - reg_factor)
            self._log(f"Step 4: Regression Applied ({reg_factor}) -> {stats_total:.2f}")
        
        # Step 4b: xPTS League Correction
        xpts_correction = c.get('_xpts_correction', 1.0)
        if xpts_correction != 1.0:
            stats_total *= xpts_correction
            self._log(f"Step 4b: xPTS Correction ({xpts_correction:.4f}) -> {stats_total:.2f}")

        # --- PHASE 2: SHARP LAYER ---
        sharp_total = stats_total
        notes = []
        
        if self.mode == "full":
            projected_spread = abs(game_data.get('projected_spread', 10.0))
            current_lean = "OVER" if sharp_total > market else "UNDER"

            # A. Possession/Pace Boosters
            if sp.get('possession_bonus_value') and (game_data.get('is_rebound_mismatch') or game_data.get('is_turnover_mismatch')):
                pos_bonus = sp['possession_bonus_value']
                sharp_total += pos_bonus
                self._log(f"Sharp 1: Possession Bonus -> +{pos_bonus}")

            # B. High Pace Efficiency & Elite Offense Gate
            pace_eff_bonus = 0
            if sp.get('high_pace_threshold') and pace_adj > sp['high_pace_threshold']:
                pace_eff_bonus = (pace_adj - sp['high_pace_threshold']) * sp.get('high_pace_efficiency_multiplier', 0.1)
                pace_cap = sp.get('high_pace_efficiency_cap')
                if pace_cap and pace_eff_bonus > pace_cap:
                    pace_eff_bonus = pace_cap
            
            off_threshold = sp.get('elite_offense_rating_threshold', 118.0)
            sA_off = game_data.get('statsA', {}).get('adj_off', 110)
            sH_off = game_data.get('statsH', {}).get('adj_off', 110)
            elite_off_bonus = sp.get('elite_offense_boost', 2.0) if (sA_off + sH_off > off_threshold * 2) else 0

            # --- LEAGUE SPECIFIC SHARP GATES ---
            if c['name'] == "NCAA":
                if elite_off_bonus > 0:
                    sharp_total += elite_off_bonus
                    self._log(f"Sharp 2: Elite Offense Boost -> +{elite_off_bonus:.1f}")
                    if pace_eff_bonus > 0:
                        pace_eff_bonus *= 0.5
                        self._log(f"Sharp 2b: High Pace Gate -> Pace Efficiency capped at 50%")
                if pace_eff_bonus > 0:
                    sharp_total += pace_eff_bonus
                    self._log(f"Sharp 3: High Pace Efficiency Bonus -> +{pace_eff_bonus:.2f}")

            # FIXED: Moved outside the NCAA block so it executes for the NBA
            if c['name'] == "NBA":
                # Sharp 4: 3PT Scaling
                if sp.get('three_pt_scale_factor'):
                    three_pa = game_data.get('three_pa_total', 70)
                    three_pa_100 = (three_pa / pace_adj) * 100
                    league_avg_3pa_100 = 70.0
                    diff = three_pa_100 - league_avg_3pa_100
                    if diff > 0:
                        bonus = min(diff * sp.get('three_pt_scale_factor', 0.08), sp.get('three_pt_cap', 2.0))
                        sharp_total += bonus
                        self._log(f"Sharp 4: 3PT Volume Scaling -> +{bonus:.2f}")

                # Sharp 5: Blowout Logic
                spread_threshold = sp.get('blowout_spread_threshold', 12.0)
                if projected_spread > spread_threshold:
                    fast_pace_mark = sp.get('blowout_fast_pace', 100.0)
                    slow_pace_mark = sp.get('blowout_slow_pace', 98.0)
                    if current_lean == "UNDER":
                         penalty = sp.get('blowout_under_penalty', 5.0)
                         if pace_adj < slow_pace_mark: penalty *= 0.5
                         sharp_total += penalty
                         self._log(f"Sharp 5: Blowout Adjustment (Under) -> {penalty:+.1f}")
                    else:
                        if pace_adj >= fast_pace_mark:
                            boost = sp.get('blowout_boost_fast', 4.0)
                        elif pace_adj >= slow_pace_mark:
                            boost = sp.get('blowout_boost_avg', 2.0)
                        else:
                            boost = 0
                        if boost > 0:
                            sharp_total += boost
                            self._log(f"Sharp 5: Blowout Adjustment (Over) -> +{boost:.1f}")

            # Sharp 6: Contextual Injury Impact (Added defensive context protection)
            if injury_notes:
                star_impact = 0
                leverage = c.get('star_leverage', {})
                for note in injury_notes:
                    txt = note.get('note', '').lower()
                    st = note.get('status', '').lower()
                    
                    if "out" in st or "doubtful" in st:
                        val = leverage.get('star_out', -2.5)
                        if "mvp" in txt or "superstar" in txt: val = leverage.get('mvp_out', -4.0)
                        elif "all-star" in txt: val = leverage.get('all_star_out', -2.5)
                        elif "starter" in txt: val = leverage.get('starter_out', -1.5)
                        
                        # Directional adjustment check
                        if "defense" in txt or "rim protector" in txt or "anchor" in txt:
                            val = abs(val) * 0.75  # Injury to defender raises the scoring total
                        
                        star_impact += val
                        
                impact_cap = sp.get('injury_impact_cap', 5.0)
                if impact_cap and abs(star_impact) > abs(impact_cap):
                    # Scale back while preserving the mathematical direction
                    multiplier = 1 if star_impact > 0 else -1
                    star_impact = multiplier * abs(impact_cap)
                
                sharp_total += star_impact
                self._log(f"Sharp 6: Injury Impact -> {star_impact:+.1f}")

            # Sharp 6.5: Fatigue Logic
            situational = c.get('situational', {})
            fatigue_adj = 0.0
            
            b2b_home = game_data.get('is_b2b_home', False)
            b2b_away = game_data.get('is_b2b_away', False)
            if b2b_home and b2b_away:
                fatigue_adj += situational.get('b2b_penalty_double', -2.0)
            elif b2b_home or b2b_away:
                fatigue_adj += situational.get('b2b_penalty_single', -1.0)
                
            in3in4_home = game_data.get('is_3in4_home', False)
            in3in4_away = game_data.get('is_3in4_away', False)
            if in3in4_home and in3in4_away:
                fatigue_adj += situational.get('3in4_penalty_double', -3.5)
            elif in3in4_home or in3in4_away:
                fatigue_adj += situational.get('3in4_penalty_single', -2.0)
                
            fatigue_cap = situational.get('fatigue_impact_cap', -4.0)
            sharp_total += max(fatigue_adj, fatigue_cap)

            # Sharp 7: Venue Pace Splits
            split_bonus = sp.get('pace_home_advantage_bonus', 1.5)
            if split_bonus > 0 and 'pace_home' in sH and 'pace_away' in sA:
                if sH['pace_home'] > sH.get('pace', 100) and sA['pace_away'] > sA.get('pace', 100):
                    sharp_total += split_bonus
                elif sH['pace_home'] < sH.get('pace', 100) and sA['pace_away'] < sA.get('pace', 100):
                    sharp_total -= split_bonus

            # Sharp 8: Close Game Foul Bonus
            if projected_spread < sp.get('close_game_threshold', 4.5):
                sharp_total += sp.get('close_game_foul_bonus', 2.5)

        # --- PHASE 3: FINALIZATION & CLAMPING ---
        legacy_total = stats_total
        sA_vol = game_data.get('statsA', {}).get('std_dev_totals', 15.0)
        sH_vol = game_data.get('statsH', {}).get('std_dev_totals', 15.0)
        clamp_thr = max(10.0, (sA_vol + sH_vol) / 2)
        dampener = sp.get('volatility_dampener_factor', c.get('volatility_dampener', 0.7))

        def clamp_total(val, mkt):
            edge = val - mkt
            if abs(edge) > clamp_thr:
                excess = abs(edge) - clamp_thr
                return mkt + ((1 if edge > 0 else -1) * (clamp_thr + (excess * dampener)))
            return val

        clamped_legacy = clamp_total(legacy_total, market)
        clamped_sharp = clamp_total(sharp_total, market)
        final_total = clamped_sharp if self.mode == "full" else clamped_legacy

        # v3.5 High-Total Protection Rule
        if c['name'] == "NBA" and market >= (league_avg + 7.0) and self.mode == "full":
            is_elite_context = (sA.get('rank_off', 99) <= 10 and sH.get('rank_off', 99) <= 10) or (sA.get('rank_pace', 99) <= 10 and sH.get('rank_pace', 99) <= 10)
            if is_elite_context and (final_total - market) < -6.0:
                final_total = market - 6.0

        # v3.5 Market Anchoring
        if self.mode == "full" and c['name'] == "NBA":
            final_total = (final_total * 0.65) + (market * 0.35)

        raw_edge = final_total - market
        abs_edge = abs(raw_edge)
        side = "OVER" if raw_edge > 0 else "UNDER"

        # Assignment Logic
        if c['name'] == "NBA":
            decision = "PASS" if abs_edge < 5.0 else "LEAN" if abs_edge < 8.0 else "PLAY"
            confidence = "HIGH" if abs_edge >= 8.0 else "MEDIUM" if abs_edge >= 6.5 else "LOW" if abs_edge >= 5.0 else "NO PLAY"
        else:
            if abs_edge < 4.0: decision, confidence = "PASS", "NO PLAY"
            elif abs_edge < 5.0: decision, confidence = "LEAN", "LOW"
            elif abs_edge < 7.0: decision, confidence = "PLAY", "MEDIUM"
            elif abs_edge < 9.0: decision, confidence = "LEAN", "LOW"
            else: decision, confidence = "PLAY", "HIGH"

        # Cutoffs and Filters
        if self.mode == "full" and c['name'] in ("NCAA", "NBL1") and abs_edge < c['thresholds'].get('small_edge_cutoff', 4.0):
            decision, confidence = "PASS", "NO PLAY"

        if self.mode == "full" and ((c['name'] == "NCAA" and market < 138.0) or (c['name'] == "NBL1" and market < 150.0)):
            tier_map = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NO PLAY", "NO PLAY": "NO PLAY"}
            confidence = tier_map.get(confidence, confidence)

        return {
            "final_model_total": round(final_total, 2),
            "legacy_total": round(clamped_legacy, 2),
            "sharp_total": round(clamped_sharp, 2),
            "market_total": market,
            "edge": round(raw_edge, 2),
            "abs_edge": round(abs_edge, 2),
            "side": side,
            "mode": "A" if abs_edge >= c['thresholds']['mode_a'] else "B" if abs_edge >= c['thresholds']['mode_b'] else "NONE",
            "decision": decision,
            "confidence": confidence,
            "notes": notes,
            "trace": self.trace
        }
