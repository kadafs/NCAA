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
            market = 230.0 if c.get('name') == 'NBA' else 145.5
        else:
            market = float(market_val)
        
        # --- PHASE 1: STATISTICAL FOUNDATION ---
        pace_adj = game_data.get('pace_adjustment', c['pace_pivot'])
        
        # Step 0: Pace Multiplier
        pace_mult = c.get('conf_pace_multipliers', {}).get(conf, c.get('conf_pace_multipliers', {}).get('DEFAULT', 1.0))
        if pace_mult != 1.0:
            pace_adj *= pace_mult
            self._log(f"Step 0: Pace Multiplier ({conf}) -> {pace_adj:.1f}")

        eff_adj = game_data.get('efficiency_adjustment', c['eff_pivot'])
        
        # Step 1: Base Total
        stats_total = ((eff_adj * pace_adj) / 100) * 2
        self._log(f"Step 1: Raw Base ({eff_adj:.1f} Eff @ {pace_adj:.1f} Pace) = {stats_total:.2f}")

        # Step 2: Pace Impact (v3.0: DISABLED for NBA to avoid double-counting)
        if c['name'] != "NBA":
            pace_delta = pace_adj - c['pace_pivot']
            pace_impact = pace_delta * c['pace_delta_weight']
            stats_total += pace_impact
            self._log(f"Step 2: Pace Impact ({pace_adj:.1f} vs {c['pace_pivot']}) -> {pace_impact:+.2f}")
        else:
            self._log(f"Step 2: Pace Impact SKIPPED (v3.0 NBA: pace already in base formula)")
        
        # Step 3: Alignment (Conf & HCA) -> BEFORE Regression
        # HCA Gate: Disable if neutral
        if not game_data.get('is_neutral', False):
            hca = c.get('hca_total_bump', 0)
            stats_total += hca
            self._log(f"Step 3: Home Court Advantage -> +{hca:.1f}")
            
        # Conference Sync Gate: Reduce bias if pace multiplier used
        cb = c.get('conf_bias', {}).get(conf, c.get('conf_bias', {}).get('DEFAULT', 0))
        if pace_mult != 1.0 and cb != 0:
            reduction = 0.5
            cb = cb - reduction if cb > 0 else cb + reduction
            self._log(f"Step 3b: Conf Bias Sync Gate (Pace Mult used) -> Bias reduced to {cb:+.1f}")
        
        if cb != 0:
            stats_total += cb
            self._log(f"Step 3c: Conference Bias ({conf}) -> {cb:+.1f}")

        # Step 4: REGRESSION -> v3.0 DYNAMIC for NBA, static for NCAA
        if c['name'] == "NBA":
            # Dynamic regression: stronger for extreme totals
            if stats_total < 215:
                reg_factor = 0.98
            elif stats_total <= 235:
                reg_factor = 0.96
            elif stats_total <= 250:
                reg_factor = 0.94
            else:
                reg_factor = 0.92
            self._log(f"Step 4: Dynamic Regression (NBA v3.0, total={stats_total:.1f}) -> factor={reg_factor}")
        else:
            reg_factor = c.get('regression_factor', 0.97)
        stats_total *= reg_factor
        self._log(f"Step 4: Regression Applied ({reg_factor}) -> {stats_total:.2f} (Stats Baseline)")
        
        # --- PHASE 2: SHARP LAYER (BOOSTERS & INJURIES) ---
        sharp_total = stats_total
        notes = []
        
        # A. Possession/Pace Boosters (Shared Baseline in v2.0 logic)
        pos_bonus = 0
        if sp.get('possession_bonus_value'):
            if game_data.get('is_rebound_mismatch') or game_data.get('is_turnover_mismatch'):
                pos_bonus = sp['possession_bonus_value']
                sharp_total += pos_bonus
                self._log(f"Sharp 1: Possession Bonus -> +{pos_bonus}")

        # B. High Pace Efficiency Gate
        pace_eff_bonus = 0
        if sp.get('high_pace_threshold') and pace_adj > sp['high_pace_threshold']:
            pace_eff_bonus = (pace_adj - sp['high_pace_threshold']) * sp.get('high_pace_efficiency_multiplier', 0.1)
        
        # Elite Offense Gate
        elite_off_bonus = 0
        off_threshold = sp.get('elite_offense_rating_threshold', 118.0)
        sA_off = game_data.get('statsA', {}).get('adj_off', 110)
        sH_off = game_data.get('statsH', {}).get('adj_off', 110)
        if sA_off + sH_off > off_threshold * 2:
            elite_off_bonus = sp.get('elite_offense_boost', 2.0)
            
        if self.mode == "full":
            projected_spread = abs(game_data.get('projected_spread', 10.0))
            current_lean = "OVER" if sharp_total > market else "UNDER"

            if c['name'] == "NCAA":
                # Sharp 2: Elite Offense
                if elite_off_bonus > 0:
                    sharp_total += elite_off_bonus
                    notes.append(f"Sharp Adjustment: Elite Offense Booster (+{elite_off_bonus:.1f} pts)")
                    self._log(f"Sharp 2: Elite Offense Boost -> +{elite_off_bonus:.1f}")
                    # Pace Conflict Gate: Cap Pace Eff at 50%
                    if pace_eff_bonus > 0:
                        pace_eff_bonus *= 0.5
                        self._log(f"Sharp 2b: High Pace Gate (Elite Offense active) -> Pace Efficiency capped at 50%")
                
                # Sharp 3: High Pace Eff
                if pace_eff_bonus > 0:
                    sharp_total += pace_eff_bonus
                    self._log(f"Sharp 3: High Pace Efficiency Bonus -> +{pace_eff_bonus:.2f}")

                # Sharp 4: Blowout Volatility
                spread_threshold = sp.get('blowout_spread_threshold', 9.0)
                if projected_spread > spread_threshold:
                    penalty = sp.get('blowout_under_penalty', 3.5) if current_lean == "UNDER" else sp.get('blowout_over_boost', 2.5)
                    sharp_total += penalty
                    self._log(f"Sharp 4: Blowout Adjustment (NCAA) -> {penalty:+.1f}")
                    notes.append(f"Sharp Adjustment: Blowout Volatility Correction (+{penalty:.1f} pts)")

                # Sharp v2.1 Change #1: Soft Foul Layer
                # Trigger: competitive (Spread <= 7), mid-tempo range (138-155), non-static pace (>= 67)
                # v2.5 Low-Total Protection Gate: Disable for model_total < 138
                if sharp_total >= 138.0 and projected_spread <= 7.0 and 138.0 <= sharp_total <= 155.0 and pace_adj >= 67.0:
                    soft_foul_bonus = 1.2
                    sharp_total += soft_foul_bonus
                    self._log(f"Sharp v2.1: Soft Foul Layer Applied -> +{soft_foul_bonus}")
                    notes.append(f"Sharp Adjustment: Soft Foul Probability Correction (+{soft_foul_bonus} pts)")
                elif sharp_total < 138.0 and projected_spread <= 7.0:
                    self._log(f"Sharp v2.5: Low-Total Protection Gate -> Soft Foul Layer DISABLED (model_total {sharp_total:.1f} < 138)")

                # Sharp v2.1 Change #2: Mid-range Volatility Boost
                # Trigger: high-chaos band (145-155), high volatility context (NRE >= 50)
                # v2.5 Low-Total Protection Gate: Disable for model_total < 138
                nre_val = game_data.get('nre', 50) # Fallback to mid
                if sharp_total >= 138.0 and 145.0 <= sharp_total <= 155.0 and nre_val >= 50:
                    mid_vol_boost = 1.0
                    sharp_total += mid_vol_boost
                    self._log(f"Sharp v2.1: Mid-range Volatility Boost -> +{mid_vol_boost}")
                    notes.append(f"Sharp Adjustment: Mid-range Volatility Correction (+{mid_vol_boost} pts)")

            if c['name'] == "NBA":
                # Sharp 2: Elite Offense
                if elite_off_bonus > 0:
                    sharp_total += elite_off_bonus
                    notes.append(f"Sharp Adjustment: Elite Offense Booster (+{elite_off_bonus:.1f} pts)")
                    self._log(f"Sharp 2: Elite Offense Boost -> +{elite_off_bonus:.1f}")
                    # Pace Conflict Gate: Cap Pace Eff at 50%
                    if pace_eff_bonus > 0:
                        pace_eff_bonus *= 0.5
                        self._log(f"Sharp 2b: High Pace Gate (Elite Offense active) -> Pace Efficiency capped at 50%")
                
                # Sharp 3: High Pace Eff
                if pace_eff_bonus > 0:
                    sharp_total += pace_eff_bonus
                    self._log(f"Sharp 3: High Pace Efficiency Bonus -> +{pace_eff_bonus:.2f}")

                # Sharp 4: NBA 3PT Volume
                if sp.get('three_pa_threshold'):
                    three_pa = game_data.get('three_pa_total', 70)
                    if three_pa > sp['three_pa_threshold']:
                        bonus = (three_pa - sp['three_pa_threshold']) * 0.05
                        sharp_total += bonus
                        self._log(f"Sharp 4: 3PT Volume Bonus -> +{bonus:.2f}")

                # Sharp 5: Blowout Volatility
                spread_threshold = sp.get('blowout_spread_threshold', 12.0)
                if projected_spread > spread_threshold:
                    penalty = sp.get('blowout_under_penalty', 5.0) if current_lean == "UNDER" else sp.get('blowout_over_boost', 3.5)
                    sharp_total += penalty
                    self._log(f"Sharp 5: Blowout Adjustment (NBA) -> {penalty:+.1f}")
                    notes.append(f"Sharp Adjustment: Blowout Volatility Correction (+{penalty:.1f} pts)")

            # Sharp 6: Injury Impact (Before Foul Bonus)
            star_impact = 0
            if injury_notes:
                for note in injury_notes:
                    st = note.get('status', '').lower()
                    if "out" in st or "doubtful" in st:
                        star_impact += c.get('star_leverage', {}).get('star_out', -2.5)
                impact_cap = sp.get('injury_impact_cap')
                if impact_cap and abs(star_impact) > impact_cap:
                    star_impact = -impact_cap
                sharp_total += star_impact
                self._log(f"Sharp 6: Context Impact (Injuries) -> {star_impact:+.1f}")
                if star_impact != 0:
                    notes.append(f"Context Impact: {star_impact:+.1f} pts (Injury Related)")

            # Sharp 7: CLOSE GAME FOUL BONUS (LAST) -> POST-REGRESSION/POST-INJURY
            if projected_spread < sp.get('close_game_threshold', 4.5):
                bonus = sp.get('close_game_foul_bonus', 2.5)
                sharp_total += bonus
                self._log(f"Sharp 7: Close Game Foul Bonus (LAST) -> +{bonus:.1f}")
                notes.append(f"Sharp Adjustment: Close Game Foul Bonus (LAST) (+{bonus:.1f} pts)")

        # --- PHASE 3: FINALIZATION & CLAMPING ---
        legacy_total = stats_total # SAFE Result (Baseline only)
        
        threshold = c.get('volatility_threshold', 15.0)
        def clamp_total(val, mkt):
            edge = val - mkt
            if abs(edge) > threshold:
                excess = abs(edge) - threshold
                clamped_excess = excess * c.get('volatility_dampener', 0.7)
                multiplier = 1 if edge > 0 else -1
                return mkt + (multiplier * (threshold + clamped_excess))
            return val

        clamped_legacy = clamp_total(legacy_total, market)
        clamped_sharp = clamp_total(sharp_total, market)

        final_total = clamped_sharp if self.mode == "full" else clamped_legacy

        # v3.0 Market Anchoring (NBA FULL mode only): 75% model, 25% market
        if self.mode == "full" and c['name'] == "NBA":
            anchor_weight = 0.25
            anchored_total = (final_total * (1 - anchor_weight)) + (market * anchor_weight)
            self._log(f"v3.0 Market Anchoring: {final_total:.2f} -> {anchored_total:.2f} (75% model, 25% market)")
            notes.append(f"Market Anchoring: Blended with market ({anchor_weight*100:.0f}%)")
            final_total = anchored_total
        # Absolute Edge Principle
        raw_edge = final_total - market
        abs_edge = abs(raw_edge)
        side = "OVER" if raw_edge > 0 else "UNDER"
        
        # Decision Logic (Pass/Lean/Play)
        if c['name'] == "NBA":
            # v3.0 Professional Thresholds
            if abs_edge < 5.0:
                decision = "PASS"
            elif abs_edge < 7.0:
                decision = "LEAN"
            else:
                decision = "PLAY"
        else:
            # v2.2 Standard Thresholds
            if abs_edge < 4.0:
                decision = "PASS"
            elif abs_edge < 6.0:
                decision = "LEAN"
            else:
                decision = "PLAY"
            
        # Professional Confidence Tiers
        if abs_edge >= 9.0: confidence = "HIGH"
        elif abs_edge >= 7.0: confidence = "MEDIUM"
        elif abs_edge >= 5.0: confidence = "LOW"
        else: confidence = "NO PLAY"
        
        # NCAA Auto-Pass Override (Force PASS for very small edges)
        if self.mode == "full" and c['name'] == "NCAA":
            cutoff = c['thresholds'].get('small_edge_cutoff', 4.0)
            if abs_edge < cutoff:
                decision = "PASS"
                confidence = "NO PLAY"
                notes.append(f"Auto-Pass: Edge ({abs_edge:.1f}) below threshold ({cutoff})")

        # v2.5 Light Selection Filter: Downgrade confidence by one tier for low-total markets
        if self.mode == "full" and c['name'] == "NCAA" and market < 138.0:
            tier_map = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NO PLAY", "NO PLAY": "NO PLAY"}
            old_conf = confidence
            confidence = tier_map.get(confidence, confidence)
            if old_conf != confidence:
                self._log(f"v2.5 Light Selection Filter: Market total ({market}) < 138 -> Confidence downgraded {old_conf} -> {confidence}")
                notes.append(f"Light Selection Filter: Confidence downgraded ({old_conf} -> {confidence})")

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

