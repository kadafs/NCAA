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
        if c['name'] == "NBA":
            # v3.1 Matchup-Adjusted Efficiency (Professional Upgrade)
            # Expects adj_off and adj_def in game_data stats
            league_avg_eff = c.get('eff_pivot', 115.0)
            
            sA = game_data.get('statsA', {})
            sB = game_data.get('statsH', {})
            
            a_off = sA.get('adj_off', league_avg_eff)
            a_def = sA.get('adj_def', league_avg_eff)
            b_off = sB.get('adj_off', league_avg_eff)
            b_def = sB.get('adj_def', league_avg_eff)
            
            # KenPom-style Expected Efficiency per possession
            exp_a_eff = (a_off * b_def) / league_avg_eff
            exp_b_eff = (b_off * a_def) / league_avg_eff
            
            combined_eff = (exp_a_eff + exp_b_eff) / 2
            stats_total = (combined_eff * pace_adj / 100) * 2
            
            self._log(f"Step 1: Matchup Efficiency Base (A:{exp_a_eff:.1f} + B:{exp_b_eff:.1f}) @ {pace_adj:.1f} Pace = {stats_total:.2f}")
        else:
            # Legacy/NCAA Simple Average
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
            # Dynamic regression: stepped floors (Protection from under-pulls)
            if stats_total < 215:
                reg_factor = 0.99
            elif stats_total <= 235:
                reg_factor = 0.97
            elif stats_total <= 250:
                reg_factor = 0.95
            else:
                reg_factor = 0.94
            self._log(f"Step 4: Stepped Regression (NBA v3.5, total={stats_total:.1f}) -> factor={reg_factor}")
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
            # v3.3 Cap High Pace Efficiency
            pace_cap = sp.get('high_pace_efficiency_cap')
            if pace_cap and pace_eff_bonus > pace_cap:
                pace_eff_bonus = pace_cap
        
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

            if c['name'] == "NBL1":
                    # Sharp 2: Elite Offense Boost — CONTINUOUS SCALING (Audit v2)
                    # Replaces binary threshold with a scaled factor proportional to avg offense above pivot
                    # elite_factor = avg_OFF − league_pivot  → bonus = factor × 0.12, cap 2.0
                    nbl1_league_avg = c.get('eff_pivot', 100.0)
                    sA_off_v = game_data.get('statsA', {}).get('adj_off', nbl1_league_avg)
                    sH_off_v = game_data.get('statsH', {}).get('adj_off', nbl1_league_avg)
                    avg_matchup_off = (sA_off_v + sH_off_v) / 2
                    elite_factor = avg_matchup_off - nbl1_league_avg

                    if elite_factor > 0:
                        scale_factor = sp.get('elite_offense_scale_factor', 0.12)
                        eff_cap      = sp.get('elite_offense_continuous_cap', 2.0)
                        nbl1_elite_bonus = min(elite_factor * scale_factor, eff_cap)
                        sharp_total += nbl1_elite_bonus
                        notes.append(f"Sharp Adjustment: Elite Offense Booster (+{nbl1_elite_bonus:.2f} pts)")
                        self._log(f"Sharp 2: Elite Offense Continuous (avg_OFF {avg_matchup_off:.1f}, delta {elite_factor:.1f}) -> +{nbl1_elite_bonus:.2f}")
                        # Pace Conflict Gate: cap pace-eff at 50% when elite offense active
                        if pace_eff_bonus > 0:
                            pace_eff_bonus *= 0.5
                            self._log(f"Sharp 2b: High Pace Gate (Elite Offense active) -> Pace Efficiency capped at 50%")

                    # Sharp 3: High Pace Efficiency
                    if pace_eff_bonus > 0:
                        sharp_total += pace_eff_bonus
                        self._log(f"Sharp 3: High Pace Efficiency Bonus -> +{pace_eff_bonus:.2f}")

                    # Sharp 4: Blowout Volatility (NBL1 calibrated to ~8pt spread threshold)
                    spread_threshold = sp.get('blowout_spread_threshold', 8.0)
                    if projected_spread > spread_threshold:
                        penalty = sp.get('blowout_under_penalty', 2.5) if current_lean == "UNDER" else sp.get('blowout_over_boost', 2.0)
                        sharp_total += penalty
                        self._log(f"Sharp 4: Blowout Adjustment (NBL1) -> {penalty:+.1f}")
                        notes.append(f"Sharp Adjustment: Blowout Volatility Correction ({penalty:+.1f} pts)")

                        # Sharp 4b: Large Blowout Bonus — extra +0.5 when spread > 12 (Audit v2)
                        # Extreme mismatches produce explosive garbage-time scoring
                        large_blowout_threshold = sp.get('blowout_large_threshold', 12.0)
                        if projected_spread > large_blowout_threshold:
                            large_bonus = sp.get('blowout_large_bonus', 0.5)
                            sharp_total += large_bonus
                            self._log(f"Sharp 4b: Large Blowout Extra (spread {projected_spread:.1f} > {large_blowout_threshold}) -> +{large_bonus}")
                            notes.append(f"Sharp Adjustment: Large Blowout Extra (+{large_bonus} pts)")

                    # Sharp 4.5: Form Momentum Bonus (NBL1-only)
                    # Uses the form string (e.g. "WWLWW") from standings endpoint
                    home_form_wins = game_data.get('home_form_wins', 2)
                    away_form_wins = game_data.get('away_form_wins', 2)
                    combined_form  = home_form_wins + away_form_wins
                    hot_threshold  = sp.get('form_hot_streak_threshold', 8)
                    cold_threshold = sp.get('form_cold_streak_threshold', 2)
                    if combined_form >= hot_threshold:
                        form_bonus = sp.get('form_hot_streak_bonus', 1.0)   # Audit v2: reduced 1.5 → 1.0
                        sharp_total += form_bonus
                        self._log(f"Sharp 4.5: Form Momentum Bonus (Both Hot: {home_form_wins}+{away_form_wins}) -> +{form_bonus}")
                        notes.append(f"Sharp Adjustment: Hot-Streak Momentum (+{form_bonus} pts)")
                    elif combined_form <= cold_threshold:
                        form_drag = sp.get('form_cold_streak_drag', -1.0)
                        sharp_total += form_drag
                        self._log(f"Sharp 4.5: Form Momentum Drag (Both Cold: {home_form_wins}+{away_form_wins}) -> {form_drag:.1f}")
                        notes.append(f"Sharp Adjustment: Cold-Streak Drag ({form_drag:.1f} pts)")

                    # --- SHARP ADJUSTMENT CAP (Audit v2) ---
                    # Enforces Stats > Sharps hierarchy:
                    # Phase 2 is behavioral correction, NOT stat override
                    # Cap: boost ≤ +9.0, drag ≥ -6.0  (relative to stats_baseline)
                    sharp_adj_cap  = sp.get('sharp_adjustment_cap', 9.0)
                    sharp_drag_cap = sp.get('sharp_drag_cap', -6.0)
                    total_sharp_adj = sharp_total - stats_total

                    if total_sharp_adj > sharp_adj_cap:
                        clipped_total  = stats_total + sharp_adj_cap
                        self._log(f"Sharp Cap: Boost clipped {sharp_total:.2f} -> {clipped_total:.2f} (adj {total_sharp_adj:+.2f} exceeded cap +{sharp_adj_cap})")
                        notes.append(f"Sharp Cap: Boost adjustment capped at +{sharp_adj_cap} (Stats > Sharps)")
                        sharp_total = clipped_total
                    elif total_sharp_adj < sharp_drag_cap:
                        clipped_total  = stats_total + sharp_drag_cap
                        self._log(f"Sharp Cap: Drag clipped {sharp_total:.2f} -> {clipped_total:.2f} (adj {total_sharp_adj:+.2f} exceeded cap {sharp_drag_cap})")
                        notes.append(f"Sharp Cap: Drag adjustment capped at {sharp_drag_cap} (Stats > Sharps)")
                        sharp_total = clipped_total



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

                # Sharp 4: v3.1 3PT Scaling (Volume per 100 Possessions)
                # Formula: (3PA/100 - LeagueAvg) * ScaleFactor (Capped)
                if sp.get('three_pt_scale_factor'):
                    three_pa = game_data.get('three_pa_total', 70)
                    pace = pace_adj
                    three_pa_100 = (three_pa / pace) * 100
                    league_avg_3pa_100 = 35.0 * 2 # Approx 70 total -> 35 per team -> 35 per 100
                    
                    diff = three_pa_100 - league_avg_3pa_100
                    if diff > 0:
                        bonus = diff * sp.get('three_pt_scale_factor', 0.08)
                        cap = sp.get('three_pt_cap', 2.0)
                        if bonus > cap: bonus = cap
                        sharp_total += bonus
                        self._log(f"Sharp 4: 3PT Efficiency (v3.1) -> +{bonus:.2f} ({three_pa_100:.1f} 3PA/100)")

                # Sharp 5: v3.1 Pace-Conditioned Blowout Logic
                spread_threshold = sp.get('blowout_spread_threshold', 12.0)
                if projected_spread > spread_threshold:
                    fast_pace_mark = sp.get('blowout_fast_pace', 100.0)
                    slow_pace_mark = sp.get('blowout_slow_pace', 98.0)
                    
                    # Logic: Fast teams usually score in garbage time -> OVER boost
                    # Logic: Slow teams usually grind clock -> No boost or small penalty
                    if current_lean == "UNDER":
                         # Defensive/Slow check: if pace is slow, don't penalize under too much
                         penalty = sp.get('blowout_under_penalty', 5.0)
                         if pace_adj < slow_pace_mark:
                             penalty *= 0.5 # Halve penalty for slow teams
                         sharp_total += penalty
                         self._log(f"Sharp 5: Blowout Adjustment (NBA Under) -> {penalty:+.1f}")
                         notes.append(f"Sharp Adjustment: Blowout Volatility Correction (+{penalty:.1f} pts)")
                    else:
                        # Over boost only if pace is decent
                        if pace_adj >= fast_pace_mark:
                            boost = sp.get('blowout_boost_fast', 4.0)
                            sharp_total += boost
                            self._log(f"Sharp 5: Blowout Adjustment (NBA Fast Over) -> +{boost:.1f}")
                            notes.append(f"Sharp Adjustment: Fast-Pace Blowout Boost (+{boost:.1f} pts)")
                        elif pace_adj >= slow_pace_mark:
                            boost = sp.get('blowout_boost_avg', 2.0)
                            sharp_total += boost
                            self._log(f"Sharp 5: Blowout Adjustment (NBA Avg Over) -> +{boost:.1f}")
                            notes.append(f"Sharp Adjustment: Blowout Correction (+{boost:.1f} pts)")
                        else:
                            self._log(f"Sharp 5: Blowout Adjustment SKIPPED (Slow Pace {pace_adj:.1f})")

            # Sharp 6: v3.1 Tiered Injury Impact
            star_impact = 0
            if injury_notes:
                leverage = c.get('star_leverage', {})
                for note in injury_notes:
                    txt = note.get('note', '').lower()
                    st = note.get('status', '').lower()
                    
                    if "out" in st or "doubtful" in st:
                        # Attempt to detect tier from text (requires bridge to populate this or future expansion)
                        # For now, simplistic keyword matching if available, else standard fallback
                        val = leverage.get('star_out', -2.5) # Default
                        
                        if "mvp" in txt or "superstar" in txt: val = leverage.get('mvp_out', -4.0)
                        elif "all-star" in txt: val = leverage.get('all_star_out', -2.5)
                        elif "starter" in txt: val = leverage.get('starter_out', -1.5)
                        elif "bench" in txt or "rotation" in txt: val = leverage.get('bench_out', -0.5)
                        
                        star_impact += val
                        
                impact_cap = sp.get('injury_impact_cap')
                if impact_cap and abs(star_impact) > impact_cap:
                    star_impact = -impact_cap
                
                sharp_total += star_impact
                self._log(f"Sharp 6: Context Impact (Injuries v3.1) -> {star_impact:+.1f}")
                if star_impact != 0:
                    notes.append(f"Context Impact: {star_impact:+.1f} pts (Injury Related)")

            # Sharp 6.5: v3.2 Fatigue Logic (B2B & 3-in-4)
            # Situational penalties for schedule density
            situational = c.get('situational', {})
            fatigue_adj = 0.0
            
            # 1. B2B Check
            b2b_h = game_data.get('is_b2b_home', False)
            b2b_a = game_data.get('is_b2b_away', False)
            if b2b_h and b2b_a:
                fatigue_adj += situational.get('b2b_penalty_double', -2.0)
            elif b2b_h or b2b_a:
                fatigue_adj += situational.get('b2b_penalty_single', -1.0)
                
            # 2. 3-in-4 Check
            tr4_h = game_data.get('is_3in4_home', False)
            tr4_a = game_data.get('is_3in4_away', False)
            if tr4_h and tr4_a:
                fatigue_adj += situational.get('3in4_penalty_double', -3.5)
            elif tr4_h or tr4_a:
                fatigue_adj += situational.get('3in4_penalty_single', -2.0)
                
            # 3. Cap Impact
            fatigue_cap = situational.get('fatigue_impact_cap', -4.0)
            if fatigue_adj < fatigue_cap:
                fatigue_adj = fatigue_cap
                
            if fatigue_adj != 0:
                sharp_total += fatigue_adj
                self._log(f"Sharp 6.5: Fatigue Adjustment (B2B/3in4) -> {fatigue_adj:.1f}")
                notes.append(f"Situational: Schedule Fatigue Penalty ({fatigue_adj:.1f} pts)")


            # Sharp 7: v3.3 Home/Away Pace Split
            # Condition: Both teams faster in current venue (Home/Away) -> Over Boost
            # Condition: Both teams slower in current venue (Home/Away) -> Under Drag
            split_bonus = sp.get('pace_home_advantage_bonus', 1.5)
            if split_bonus > 0:
                sH = game_data.get('statsH', {})
                sA = game_data.get('statsA', {})
                
                # Check for granular keys (defensive check)
                if 'pace_home' in sH and 'pace_away' in sA:
                   h_pace_home = sH.get('pace_home', 0)
                   h_pace_avg = sH.get('pace', 100)
                   a_pace_road = sA.get('pace_away', 0)
                   a_pace_avg = sA.get('pace', 100)
                   
                   if h_pace_home > h_pace_avg and a_pace_road > a_pace_avg:
                       sharp_total += split_bonus
                       self._log(f"Sharp 7: Pace Split Bonus (Both Fast @ Venue) -> +{split_bonus}")
                       notes.append(f"Sharp Adjustment: Venue Pace Split Boost (+{split_bonus} pts)")
                   elif h_pace_home < h_pace_avg and a_pace_road < a_pace_avg:
                       sharp_total -= split_bonus
                       self._log(f"Sharp 7: Pace Split Drag (Both Slow @ Venue) -> -{split_bonus}")
                       notes.append(f"Sharp Adjustment: Venue Pace Split Drag (-{split_bonus} pts)")

            # Sharp 8: CLOSE GAME FOUL BONUS (LAST) -> POST-REGRESSION/POST-INJURY
            if projected_spread < sp.get('close_game_threshold', 4.5):
                bonus = sp.get('close_game_foul_bonus', 2.5)
                sharp_total += bonus
                self._log(f"Sharp 8: Close Game Foul Bonus (LAST) -> +{bonus:.1f}")
                notes.append(f"Sharp Adjustment: Close Game Foul Bonus (LAST) (+{bonus:.1f} pts)")

        # --- PHASE 3: FINALIZATION & CLAMPING ---
        legacy_total = stats_total # SAFE Result (Baseline only)
        
        # v3.1 Stricter Volatility Clamp
        # Use new config params if available (NBA), else fallback (NCAA)
        clamp_thr = sp.get('volatility_clamp_threshold', c.get('volatility_threshold', 15.0))
        dampener = sp.get('volatility_dampener_factor', c.get('volatility_dampener', 0.7))

        def clamp_total(val, mkt):
            edge = val - mkt
            if abs(edge) > clamp_thr:
                excess = abs(edge) - clamp_thr
                clamped_excess = excess * dampener
                multiplier = 1 if edge > 0 else -1
                return mkt + (multiplier * (clamp_thr + clamped_excess))
            return val

        clamped_legacy = clamp_total(legacy_total, market)
        clamped_sharp = clamp_total(sharp_total, market)

        final_total = clamped_sharp if self.mode == "full" else clamped_legacy

        # v3.5 High-Total Protection Rule (NBA)
        # Cap UNDER edge at 6 points if market >= 232 and teams are elite offensive/pace
        if c['name'] == "NBA" and market >= 232.0 and self.mode == "full":
            sA = game_data.get('statsA', {})
            sH = game_data.get('statsH', {})
            rank_off_A = sA.get('rank_off', 99)
            rank_off_H = sH.get('rank_off', 99)
            rank_pace_A = sA.get('rank_pace', 99)
            rank_pace_H = sH.get('rank_pace', 99)
            
            # Condition: Both Top-10 Offense OR Both Top-10 Pace
            is_elite_context = (rank_off_A <= 10 and rank_off_H <= 10) or (rank_pace_A <= 10 and rank_pace_H <= 10)
            
            if is_elite_context:
                current_edge = final_total - market
                # If UNDER edge > 6 (i.e., current_edge < -6)
                if current_edge < -6.0:
                    capped_total = market - 6.0
                    self._log(f"v3.5 High-Total Protection: Cap UNDER edge (Market {market} >= 232, Elite Context) -> {final_total:.1f} to {capped_total:.1f}")
                    final_total = capped_total
                    notes.append("Protection Rule: Under edge capped at 6pts (High Total + Elite Off/Pace)")

        # v3.5 Market Anchoring (NBA FULL mode only): 65% model, 35% market
        if self.mode == "full" and c['name'] == "NBA":
            anchor_weight = 0.35
            anchored_total = (final_total * (1 - anchor_weight)) + (market * anchor_weight)
            self._log(f"v3.0 Market Anchoring: {final_total:.2f} -> {anchored_total:.2f} (65% model, 35% market)")
            notes.append(f"Market Anchoring: Blended with market ({anchor_weight*100:.0f}%)")
            final_total = anchored_total
        # Absolute Edge Principle
        raw_edge = final_total - market
        abs_edge = abs(raw_edge)
        side = "OVER" if raw_edge > 0 else "UNDER"
        
        # Decision Logic (Pass/Lean/Play)
        if c['name'] == "NBA":
            # v3.5 Professional Thresholds
            if abs_edge < 5.0:
                decision = "PASS"
            elif abs_edge < 8.0:
                decision = "LEAN"
            else:
                decision = "PLAY"
        else:
            # v2.5 New Recommended Structure (NCAA) -> Mapped to Legacy Keys for Frontend Compatibility
            if abs_edge < 4.0:
                decision = "PASS"
            elif (4.0 <= abs_edge < 5.0) or (7.0 <= abs_edge < 9.0):
                decision = "LEAN"
            elif 5.0 <= abs_edge < 7.0:
                decision = "PLAY" # TIER B -> PLAY
            else: # >= 9.0
                decision = "PLAY" # TIER A -> PLAY
            
        # Professional Confidence Tiers (NCAA structure) mapped to Legacy Strings
        if c['name'] == "NBA":
            if abs_edge >= 8.0: confidence = "HIGH"
            elif abs_edge >= 6.5: confidence = "MEDIUM" # Implicit mid-tier
            elif abs_edge >= 5.0: confidence = "LOW"
            else: confidence = "NO PLAY"
        else:
            # NCAA: New Thresholds -> Legacy Strings
            if abs_edge >= 9.0: confidence = "HIGH"         # Was TIER A
            elif 5.0 <= abs_edge < 7.0: confidence = "MEDIUM" # Was TIER B
            elif (4.0 <= abs_edge < 5.0) or (7.0 <= abs_edge < 9.0): confidence = "LOW" # Was LEAN
            else: confidence = "NO PLAY"                      # Was PASS
        
        # NCAA / NBL1 Auto-Pass Override (Force PASS for very small edges)
        if self.mode == "full" and c['name'] in ("NCAA", "NBL1"):
            cutoff = c['thresholds'].get('small_edge_cutoff', 4.0)
            if abs_edge < cutoff:
                decision = "PASS"
                confidence = "NO PLAY"
                notes.append(f"Auto-Pass: Edge ({abs_edge:.1f}) below threshold ({cutoff})")

        # v2.5 Light Selection Filter: Downgrade confidence for low-total markets (NCAA)
        if self.mode == "full" and c['name'] == "NCAA" and market < 138.0:
            tier_map = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NO PLAY", "NO PLAY": "NO PLAY"}
            old_conf = confidence
            confidence = tier_map.get(confidence, confidence)
            if old_conf != confidence:
                self._log(f"v2.5 Light Selection Filter: Market total ({market}) < 138 -> Confidence downgraded {old_conf} -> {confidence}")
                notes.append(f"Light Selection Filter: Confidence downgraded ({old_conf} -> {confidence})")

        # NBL1 Low-Total Filter: Downgrade confidence for markets below 150
        if self.mode == "full" and c['name'] == "NBL1" and market < 150.0:
            tier_map = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NO PLAY", "NO PLAY": "NO PLAY"}
            old_conf = confidence
            confidence = tier_map.get(confidence, confidence)
            if old_conf != confidence:
                self._log(f"NBL1 Low-Total Filter: Market total ({market}) < 150 -> Confidence downgraded {old_conf} -> {confidence}")
                notes.append(f"NBL1 Low-Total Filter: Confidence downgraded ({old_conf} -> {confidence})")

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

