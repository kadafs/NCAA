import os
import json
import time
import datetime
from multiprocessing import Pool, cpu_count
from mlb_time import get_mlb_now
from run_daily_f5 import get_today_games, get_pitcher_fip, get_team_wrc_proxy, get_team_bullpen_fip, get_pitcher_projected_ip, get_team_f5_form_factor, get_team_wrc_splits, get_pitcher_siera, get_pitcher_xfip
from grade_f5 import grade_matchup_v6
from fetch_lineups import get_lineup_for_game, get_pitcher_hand
from monte_carlo_f5 import run_monte_carlo_f5
from full_game_model import run_full_game_mc
from park_factors import get_park_factor
from weather_f5 import get_weather_modifier, get_thermal_adjusted_ip
from umpire_engine import get_umpire_for_game, load_umpire_profile
from bullpen_rest import get_adjusted_bullpen_fip
from pitcher_advanced_stats import get_pitcher_advanced_metrics
from gatekeeper_v5 import generate_v6_premium_45_gatekeeper
import pandas as pd

def _retry_call(fn, *args, retries=3, delay=2.0, **kwargs):
    """Call fn(*args, **kwargs), retrying up to `retries` times on network errors."""
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt < retries - 1:
                print(f"  [Retry {attempt+1}/{retries}] {fn.__name__} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise

def _purge_old_caches(date_str: str):
    """Automatically deletes yesterday's transient daily caches to prevent disk bloat."""
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    if not os.path.exists(data_dir): return
    
    prefixes = ('batter_stats_', 'batter_hand_', 'speed_tier_', 'bullpen_rest_', 'league_fip_')
    try:
        for fname in os.listdir(data_dir):
            if fname.startswith(prefixes) and fname.endswith('.json'):
                if date_str not in fname:
                    try:
                        os.remove(os.path.join(data_dir, fname))
                    except Exception:
                        pass
    except Exception:
        pass


def process_single_game(args):
    game, sport_id, force_generic = args
    
    away = game['away_team']
    home = game['home_team']
    ap = game['away_pitcher']
    hp = game['home_pitcher']
    gid = game['game_id']
    away_id = game.get('away_id')
    home_id = game.get('home_id')
    ap_id = game.get('away_pitcher_id')
    hp_id = game.get('home_pitcher_id')
    away_abbr = game.get('away_abbr', away[:3].upper())
    home_abbr = game.get('home_abbr', home[:3].upper())
    venue = game.get('venue_name', 'Unknown Venue')
    pf = get_park_factor(venue)
    
    print(f"Processing: {away} @ {home} ({venue} - PF: {pf})")
    
    result = {
        'game_blocks': [],
        'priority_flags': [],
        'raw_json_data': None,
        'gatekeeper_data': None
    }
    
    try:
        # Weather modifier (MLB only — MiLB parks not covered by RotoWire)
        weather         = None
        weather_mult    = 1.0
        effective_pf    = pf
        if sport_id == 1:
            weather      = get_weather_modifier(venue, away_abbr=away_abbr, home_abbr=home_abbr)
            weather_mult = weather.get('weather_multiplier', 1.0)
            effective_pf = round(pf * weather_mult, 4)

        # 1. Top-Down Model
        ap_siera = _retry_call(get_pitcher_siera, ap, sport_id=sport_id, player_id=ap_id)
        hp_siera = _retry_call(get_pitcher_siera, hp, sport_id=sport_id, player_id=hp_id)
        
        ap_xfip = _retry_call(get_pitcher_xfip, ap, sport_id=sport_id, player_id=ap_id)
        hp_xfip = _retry_call(get_pitcher_xfip, hp, sport_id=sport_id, player_id=hp_id)
        
        # Keep FIP for reporting or fallback
        ap_fip = _retry_call(get_pitcher_fip, ap, sport_id=sport_id, player_id=ap_id)
        hp_fip = _retry_call(get_pitcher_fip, hp, sport_id=sport_id, player_id=hp_id)

        ap_ip = _retry_call(get_pitcher_projected_ip, ap, sport_id=sport_id, player_id=ap_id)
        hp_ip = _retry_call(get_pitcher_projected_ip, hp, sport_id=sport_id, player_id=hp_id)

        # ── Thermal IP Decay ─────────────────────────────────────────────────
        # Shorten projected innings under extreme heat before routing downstream.
        # Applies to both Top-Down and Monte Carlo models.
        if sport_id == 1 and weather:
            temp_f = weather.get('temp', 72)
            ap_ip = get_thermal_adjusted_ip(ap_ip, temp_f)
            hp_ip = get_thermal_adjusted_ip(hp_ip, temp_f)

        try:
            away_bp = _retry_call(get_adjusted_bullpen_fip, away)
        except Exception:
            away_bp = _retry_call(get_team_bullpen_fip, away, sport_id=sport_id)

        try:
            home_bp = _retry_call(get_adjusted_bullpen_fip, home)
        except Exception:
            home_bp = _retry_call(get_team_bullpen_fip, home, sport_id=sport_id)

        away_wrc = _retry_call(get_team_wrc_proxy, away, sport_id)
        home_wrc = _retry_call(get_team_wrc_proxy, home, sport_id)
        away_splits = _retry_call(get_team_wrc_splits, away, sport_id)
        home_splits = _retry_call(get_team_wrc_splits, home, sport_id)

        # Pitcher handedness for platoon logic (MLB only)
        if sport_id == 1:
            ap_hand = _retry_call(get_pitcher_hand, ap, sport_id=sport_id)
            hp_hand = _retry_call(get_pitcher_hand, hp, sport_id=sport_id)
        else:
            ap_hand, hp_hand = 'R', 'R'

        # ── F5 Recent Team Form Factors (MLB only) ───────────────────────────
        _neutral = {'factor': 1.0, 'raw_avg': 2.3, 'games_used': 0, 'games_raw': []}
        # Use pre-fetched data if the main process already embedded it (optimization);
        # otherwise fall back to fetching inline (e.g. single-game test runs).
        away_form_info = game.get('away_form_info', _neutral)
        home_form_info = game.get('home_form_info', _neutral)
        if sport_id == 1 and away_id and home_id and away_form_info == _neutral:
            try:
                away_form_info = get_team_f5_form_factor(int(away_id))
                home_form_info = get_team_f5_form_factor(int(home_id))
            except Exception as e:
                print(f"  [F5 Form] Inline fetch skipped: {e}")
        print(f"  [F5 Form] {away}: {away_form_info['factor']}x "
              f"(avg {away_form_info['raw_avg']} F5 runs, {away_form_info['games_used']} games)")
        print(f"  [F5 Form] {home}: {home_form_info['factor']}x "
              f"(avg {home_form_info['raw_avg']} F5 runs, {home_form_info['games_used']} games)")

        top_down = grade_matchup_v6(
            away, ap_siera, away_bp, ap_ip, away_splits['vsR'], away_splits['vsL'],
            home, hp_siera, home_bp, hp_ip, home_splits['vsR'], home_splits['vsL'],
            park_factor=pf,
            weather_multiplier=weather_mult,
            away_pitcher_hand=ap_hand,
            home_pitcher_hand=hp_hand,
        )
        td_total = top_down['projected_f5_total']
        
        # 2. Monte Carlo Model
        if force_generic:
            lineups = {'away': [], 'home': []}
        else:
            lineups = _retry_call(get_lineup_for_game, gid)

        lineups_status = "Confirmed" if lineups['away'] else "Projected (Generic)"
        
        # Fetch Umpire (MLB Only)
        umpire_name = None
        ump_profile = None
        if sport_id == 1:
            try:
                umpire_name = get_umpire_for_game(gid)
                if umpire_name:
                    ump_profile = load_umpire_profile(umpire_name)
            except Exception as e:
                print(f"  [Warning] Umpire fetch failed: {e}")

        mc = run_full_game_mc(
            lineups['away'], lineups['home'],
            ap, hp, ap_xfip, hp_xfip,
            away_team_name=away, home_team_name=home,
            away_projected_ip=ap_ip, home_projected_ip=hp_ip,
            iterations=10000, park_factor=pf, weather_context=weather, sport_id=sport_id,
            away_pitcher_hand=ap_hand, home_pitcher_hand=hp_hand,
            umpire_profile=ump_profile,
            away_wrc=away_wrc, home_wrc=home_wrc,
            venue_name=venue,
        )


        ap_adv = get_pitcher_advanced_metrics(ap, sport_id, player_id=ap_id)
        hp_adv = get_pitcher_advanced_metrics(hp, sport_id, player_id=hp_id)
        
        from park_factors import get_park_factor_details
        pf_details = get_park_factor_details(venue)
        static_pf = pf_details.get('static', 1.0)
        realized_pf = pf_details.get('realized', 1.0)

        # ── Top-Down Anchor Clamp ─────────────────────────────────────────────
        # Detects catastrophic simulation runs where the MC F5 total diverges
        # more than 40% above or 35% below the analytically-derived Top-Down
        # total. Tightened from 60%/45% to catch more MC OVER-inflation.
        # Blend weights: 40% MC + 60% neutral (TD anchor)
        #
        # Thresholds: MC > TD×1.40  OR  MC < TD×0.65
        _mc_f5 = mc.get('mc_total_runs') or td_total
        _td_clamp_applied = False
        if td_total > 0:
            _ratio = _mc_f5 / td_total
            if _ratio > 1.40 or _ratio < 0.65:
                _td_clamp_applied = True
                print(f"  [TD-Clamp] {away} @ {home}: MC {_mc_f5} vs TD {td_total} "
                      f"(ratio {_ratio:.2f}) — blending 40/60")
                mc = dict(mc)  # make mutable copy
                # Blend total
                mc['mc_total_runs'] = round((_mc_f5 * 0.40) + (td_total * 0.60), 2)
                # Blend all probabilities 40% MC + 60% neutral (0.50)
                # This is consistent with the 40/60 total blend:
                # extreme MC probs are pulled toward 0.50 (no edge) by 60%.
                _PROB_KEYS = [
                    'under_3_5_prob', 'under_4_5_prob', 'under_5_5_prob',
                    'full_over_7_5_prob', 'full_over_8_5_prob', 'full_over_9_5_prob',
                ]
                for _pk in _PROB_KEYS:
                    if mc.get(_pk) is not None:
                        mc[_pk] = round((mc[_pk] * 0.40) + (0.50 * 0.60), 4)

        # ── Consensus F5 Total (Removed) ────────────────────────────────────────


        # ── Pre-form advice (for flip detection) ──────────────────────────
        # We detect signal flips by comparing 4.5 advice direction only.
        # A flip is defined as: one side was OVER/UNDER, the other is SKIP or opposite.
        _away_form_neutral = away_form_info.get('factor', 1.0) == 1.0
        _home_form_neutral = home_form_info.get('factor', 1.0) == 1.0
        # Form adjustment note is shown when any team factor is significantly off-neutral
        _show_form_note = (
            away_form_info.get('games_used', 0) > 0 and
            (away_form_info['factor'] < 0.88 or away_form_info['factor'] > 1.12 or
             home_form_info['factor'] < 0.88 or home_form_info['factor'] > 1.12)
        )

        # 3. Betting Matrix Logic
        def get_advice(line, under_prob):
            td_gap     = line - td_total
            td_signal  = 'UNDER' if td_gap > 0 else 'OVER'

            if under_prob >= 0.52:
                mc_signal = 'UNDER'
            elif under_prob <= 0.48:
                mc_signal = 'OVER'
            else:
                mc_signal = 'NEUTRAL'

            if td_signal == mc_signal:
                mc_strong = under_prob >= 0.58 or under_prob <= 0.42
                td_strong = abs(td_gap) >= 0.30
                confidence = 'HIGH' if (mc_strong and td_strong) else 'MODERATE'
                _advice = f'Bet **{mc_signal}** ({confidence})'
            else:
                _advice = 'Skip'

            # -- Rule 1: Extreme Weather + Cold Team Override ------------------
            # Effective park factor +8% above neutral AND at least one cold team
            # (<0.88x) -> downgrade any OVER to Skip (Under Lean).
            # Evidence: EW+cold OVER went 0-for-6 across Jun 20-24. The 70% TD
            # anchor pulls consensus above the line regardless of cold form.
            # Displayed as 'Skip (Under Lean - R1)' — directional signal, not active bet.
            if 'OVER' in _advice and (effective_pf - 1.0) >= 0.08:
                _a_form = away_form_info.get('factor', 1.0)
                _h_form = home_form_info.get('factor', 1.0)
                if _a_form < 0.88 or _h_form < 0.88:
                    print(f"  [Rule 1: EW+Cold] eff_pf={effective_pf:.3f} "
                          f"{away}:{_a_form:.3f} {home}:{_h_form:.3f} "
                          f"-> OVER@{line} => Skip (Under Lean - R1)")
                    return 'Skip (Under Lean - R1)'

            # ── Rule 2: Both Teams Cold + OVER ────────────────────────────────
            # Both teams < 0.88x AND model calls OVER -> downgrade to Skip.
            # Evidence: both-cold OVER went 1W/5L (17%) across Jun 20-24.
            # The TD anchor keeps consensus above the line even when both offences
            # are ice-cold, making the OVER call structurally misleading.
            if 'OVER' in _advice:
                _a_form = away_form_info.get('factor', 1.0)
                _h_form = home_form_info.get('factor', 1.0)
                if _a_form < 0.88 and _h_form < 0.88:
                    print(f"  [Rule 2: Both-Cold] {away}:{_a_form:.3f} "
                          f"{home}:{_h_form:.3f} "
                          f"-> OVER@{line} downgraded to Skip (Under Lean - R2)")
                    return 'Skip (Under Lean - R2)'

            return _advice

        adv_3_5 = get_advice(3.5, mc['under_3_5_prob'])
        adv_4_5 = get_advice(4.5, mc['under_4_5_prob'])
        adv_5_5 = get_advice(5.5, mc['under_5_5_prob'])

        # ── Execution Filter: Team Bias Filter Veto ─────────────────────────
        from park_factors import get_park_factor_details
        pf_details = get_park_factor_details(venue)
        static_pf = pf_details.get('static', 1.0)
        realized_pf = pf_details.get('realized', 1.0)
        
        pf_diff = realized_pf - static_pf
        if abs(pf_diff) > 0.15:
            is_hitter_bias = pf_diff > 0
            is_pitcher_bias = pf_diff < 0
            
            for i, adv in enumerate([adv_3_5, adv_4_5, adv_5_5]):
                new_adv = None
                if "OVER" in adv and is_hitter_bias and "Skip" not in adv:
                    new_adv = "Skip (Team Bias Veto - Realized Hitter Edge)"
                elif "UNDER" in adv and is_pitcher_bias and "Skip" not in adv:
                    new_adv = "Skip (Team Bias Veto - Realized Pitcher Edge)"
                
                if new_adv:
                    if i == 0: adv_3_5 = new_adv
                    elif i == 1: adv_4_5 = new_adv
                    elif i == 2: adv_5_5 = new_adv
                    
        # ── Execution Filter: Retractable Roof Protocol ──────────────────────
        is_roof_closed = weather and weather.get('weather_label', '').lower() in ['dome', 'roof closed']
        is_roof_park = any(p in venue.lower() for p in ['daikin', 'chase', 'globe life', 'minute maid'])
        if is_roof_closed and is_roof_park:
            if "OVER" in adv_3_5 and "Skip" not in adv_3_5: adv_3_5 = "Skip (Roof Closed Protocol)"
            if "OVER" in adv_4_5 and "Skip" not in adv_4_5: adv_4_5 = "Skip (Roof Closed Protocol)"
            if "OVER" in adv_5_5 and "Skip" not in adv_5_5: adv_5_5 = "Skip (Roof Closed Protocol)"

        # Detect Rule 1 and Rule 2 Under Lean signals for report flagging
        _under_lean_r1 = any('Under Lean - R1' in adv for adv in [adv_3_5, adv_4_5, adv_5_5])
        _under_lean_r2 = any('Under Lean - R2' in adv for adv in [adv_3_5, adv_4_5, adv_5_5])
        
        # (Execution Filter: Asymmetric Total Rule removed)

        result['raw_json_data'] = {
            "away_team": away,
            "home_team": home,
            "pitchers": {
                "away": {"name": ap, "hand": ap_hand, "fip": ap_fip},
                "home": {"name": hp, "hand": hp_hand, "fip": hp_fip}
            },
            "environment": {
                "venue": venue,
                "park_factor": pf,
                "weather": weather,
                "effective_pf": effective_pf,
                "umpire": {
                    "name": umpire_name,
                    "profile": ump_profile
                } if umpire_name else None
            },
            "lineups_status": lineups_status,
            "predictions": {
                "top_down_f5": td_total,
                "mc_f5": mc.get('mc_total_runs'),
                # consensus_f5 removed per user request
                "mc_f5_away": mc.get('away_f5_runs') or mc.get('away_mc_runs'),
                "mc_f5_home": mc.get('home_f5_runs') or mc.get('home_mc_runs'),
                "mc_late": mc.get('late_total'),
                "mc_full_game": mc.get('full_game_total'),
                "td_clamp_applied": _td_clamp_applied,
                "away_f5_form": away_form_info,
                "home_f5_form": home_form_info,
                "form_factor": "Not implemented"
            },
            "probabilities": {
                "under_3_5": mc.get('under_3_5_prob'),
                "under_4_5": mc.get('under_4_5_prob'),
                "under_5_5": mc.get('under_5_5_prob'),
                "full_over_7_5": mc.get('full_over_7_5_prob'),
                "full_over_8_5": mc.get('full_over_8_5_prob'),
                "full_over_9_5": mc.get('full_over_9_5_prob')
            },
            "action_matrix": {
                "adv_3_5": adv_3_5,
                "adv_4_5": adv_4_5,
                "adv_5_5": adv_5_5
            },
            "version": "v4"
        }
        
        # Dynamic Games calculation
        now = get_mlb_now()
        opening_day = datetime.datetime(now.year, 3, 28, tzinfo=now.tzinfo)
        days_elapsed = (now - opening_day).days
        estimated_games = max(0, min(162, int(days_elapsed * 0.9)))
        
        # Build gatekeeper input
        result['gatekeeper_data'] = {
            'Game': f"{away} @ {home}",
            'TD': td_total,
            'MC': mc.get('mc_total_runs', td_total),
            'MCaw': mc.get('away_f5_runs') or mc.get('away_mc_runs', td_total/2),
            'MChm': mc.get('home_f5_runs') or mc.get('home_mc_runs', td_total/2),
            'AwSP': ap_fip,
            'HmSP': hp_fip,
            'Realized_PF': realized_pf,
            'Static_PF': static_pf,
            'Blended_PF': effective_pf,
            'Aw_HR_FB': ap_adv.get('HR_FB', 0),
            'Hm_HR_FB': hp_adv.get('HR_FB', 0),
            'Aw_K_Rate': ap_adv.get('K_Rate', 0),
            'Hm_K_Rate': hp_adv.get('K_Rate', 0),
            'Aw_BB_Rate': ap_adv.get('BB_Rate', 0),
            'Hm_BB_Rate': hp_adv.get('BB_Rate', 0),
            'Market_Line': 4.5,
            'Market_Odds': 1.85,
            'Games': estimated_games,
        }
        
        # 4. Format Output
        block_lines = []
        is_priority = False
        flag_reasons = []

        if weather:
            eff_pct_val = (effective_pf - 1.0) * 100
            if abs(eff_pct_val) >= 5.0:
                is_priority = True
                flag_reasons.append(f"Extreme Weather ({'+' if eff_pct_val>0 else ''}{round(eff_pct_val,1)}%)")

        for adv in [adv_3_5, adv_4_5, adv_5_5]:
            if "Bet" in adv and "Skip" not in adv:
                if mc['under_4_5_prob'] >= 0.58 or mc['under_4_5_prob'] <= 0.42:
                    is_priority = True
                    flag_reasons.append("High Confidence Edge")
                    break

        if _under_lean_r1:
            is_priority = True
            flag_reasons.append("Under Lean R1 (EW+Cold Form — skip OVER)")
        if _under_lean_r2:
            is_priority = True
            flag_reasons.append("Under Lean R2 (Both Teams Cold — skip OVER)")

        title = f"### {'🚨 ' if is_priority else ''}{away} ({ap}) @ {home} ({hp})"
        block_lines.append(title)
        
        if is_priority:
            block_lines.append(f"**🔥 FLAGGED:** {', '.join(set(flag_reasons))}")
            result['priority_flags'].append(f"- **{away} @ {home}:** {', '.join(set(flag_reasons))}")

        block_lines.append(f"🏙️ **{venue}** (Park Factor: {pf}x)")
        if weather:
            eff_pct = round((effective_pf - 1.0) * 100, 1)
            sign = '+' if eff_pct >= 0 else ''
            block_lines.append(f"🌤️ **Weather:** {weather['weather_label']} | Effective PF: {effective_pf}x ({sign}{eff_pct}%)")
        
        if umpire_name and ump_profile:
            games_cnt = ump_profile.get('games_called', 0)
            if games_cnt > 0:
                weight = games_cnt / (games_cnt + 40)
                k_mod = (ump_profile.get('raw_k_mod', 1.0) * weight) + (1.0 * (1.0 - weight))
                bb_mod = (ump_profile.get('raw_bb_mod', 1.0) * weight) + (1.0 * (1.0 - weight))
                k_pct = round((k_mod - 1.0) * 100, 1)
                bb_pct = round((bb_mod - 1.0) * 100, 1)
                k_sign = '+' if k_pct > 0 else ''
                bb_sign = '+' if bb_pct > 0 else ''
                block_lines.append(f"⚖️ **Umpire:** {umpire_name} (K: {k_sign}{k_pct}%, BB: {bb_sign}{bb_pct}%)")
            else:
                block_lines.append(f"⚖️ **Umpire:** {umpire_name} (Neutral - Insufficient Data)")

        block_lines.append(f"- **Pitcher Matchup:** {ap} ({ap_hand}HP, FIP: {ap_fip}) vs {hp} ({hp_hand}HP, FIP: {hp_fip})")
        block_lines.append(f"- **Top-Down Projected F5 Total:** {td_total} Runs")
        block_lines.append(f"- **Monte Carlo Simulated F5 Total:** {mc['mc_total_runs']} Runs (Lineups: {lineups_status})")
        # consensus_f5 removed from report per user request
        if _td_clamp_applied:
            block_lines.append(
                f"- ⚠️ **TD-Anchor Clamp Applied** — MC diverged significantly from Top-Down model. "
                f"Treat as **lower-conviction play**. Reduce bet size or require stronger line edge."
            )
        if _show_form_note:
            form_lines = []
            af = away_form_info
            hf = home_form_info
            if af['factor'] < 0.88 or af['factor'] > 1.12:
                direction = '📉 Cold' if af['factor'] < 0.95 else '📈 Hot'
                form_lines.append(f"  {direction} {away} offense: {af['factor']}x "
                                   f"(recent avg {af['raw_avg']} F5 runs, {af['games_used']} games)")
            if hf['factor'] < 0.88 or hf['factor'] > 1.12:
                direction = '📉 Cold' if hf['factor'] < 0.95 else '📈 Hot'
                form_lines.append(f"  {direction} {home} offense: {hf['factor']}x "
                                   f"(recent avg {hf['raw_avg']} F5 runs, {hf['games_used']} games)")
            if form_lines:
                block_lines.append("- 📊 **F5 Offense Form Adjustment:**")
                for fl in form_lines:
                    block_lines.append(fl)
        if 'late_total' in mc:
            block_lines.append(f"- **Monte Carlo Late Innings (6-9):** {mc['late_total']} Runs (Away BP FIP: {mc['away_bp_fip']} | Home BP FIP: {mc['home_bp_fip']})")
            block_lines.append(f"- **Monte Carlo FULL GAME Total:** {mc['full_game_total']} Runs")
            
            # (Execution Filter: Asymmetric Total Rule removed)
                
        if 'full_over_7_5_prob' in mc:
            block_lines.append(f"- **Full Game Probs:** Over 7.5: {int(mc['full_over_7_5_prob']*100)}% | Over 8.5: {int(mc['full_over_8_5_prob']*100)}% | Over 9.5: {int(mc['full_over_9_5_prob']*100)}%")
        block_lines.append("")
        
        result['game_blocks'].extend(block_lines)
        
    except Exception as e:
        print(f"  ⚠️  SKIPPED {away} @ {home}: {type(e).__name__}: {e}")
        result['game_blocks'].append(f"### {away} @ {home} — ⚠️ Data Error (skipped)")
        result['game_blocks'].append(f"Error: {type(e).__name__}: {e}")
        result['game_blocks'].append("")
    
    return result

def generate_consensus_report(sport_id=1, date_str=None, force_generic=False, team_filter=None):
    """
    date_str: optional date in MM/DD/YYYY format. Defaults to today.
    force_generic: if True, skips fetching confirmed lineups and uses the generic league-average weights.
    team_filter: string to filter games by away or home team name (case insensitive).
    """
    games = get_today_games(sport_id, date_str=date_str)
    if not games:
        print(f"No games found for sportId={sport_id} on {date_str or 'today'}.")
        return
        
    if team_filter:
        t_lower = team_filter.lower()
        games = [g for g in games if t_lower in g['away_team'].lower() or t_lower in g['home_team'].lower()]
        if not games:
            print(f"No games found matching team filter: '{team_filter}'")
            return

    report_date = date_str or get_mlb_now().strftime('%Y-%m-%d')
    _purge_old_caches(report_date)
    
    print(f"Generating Consensus Report for {len(games)} games on {report_date}...")

    # ── Pre-fetch F5 Form Factors (main process, serial) ───────────────────────
    # Fetch all unique team IDs once in the main process so that workers receive
    # pre-computed form dicts and do NOT need to hit the statsapi independently.
    # This cuts ~15-20 min of redundant API calls out of multiprocessing runs.
    if sport_id == 1:
        _neutral_form = {'factor': 1.0, 'raw_avg': 2.3, 'games_used': 0, 'games_raw': []}
        unique_ids = {}
        for g in games:
            for id_key in ('away_id', 'home_id'):
                tid = g.get(id_key)
                if tid and tid not in unique_ids:
                    unique_ids[tid] = None
        print(f"  Pre-fetching F5 form factors for {len(unique_ids)} teams...")
        for tid in unique_ids:
            try:
                unique_ids[tid] = get_team_f5_form_factor(int(tid))
            except Exception as e:
                print(f"  [F5 Form Pre-fetch] team {tid}: {e}")
                unique_ids[tid] = _neutral_form
        # Embed pre-fetched data into each game dict
        for g in games:
            g['away_form_info'] = unique_ids.get(g.get('away_id'), _neutral_form)
            g['home_form_info'] = unique_ids.get(g.get('home_id'), _neutral_form)
        print(f"  Form factor pre-fetch complete.")
    # ────────────────────────────────────────────────────────────────

    
    league_name = "MLB"
    if sport_id == 11: league_name = "AAA"
    elif sport_id == 12: league_name = "AA"
    elif sport_id == 13: league_name = "High-A"
    elif sport_id == 14: league_name = "Single-A"
    date_label = date_str if date_str else get_mlb_now().strftime('%m/%d/%Y')
    
    report_lines = []
    report_lines.append(f"# ⚾ V3 Tuned F5 Prediction Report (Sport ID: {sport_id})")
    report_lines.append(f"**Date:** {date_label}")
    report_lines.append(f"**Generated:** {get_mlb_now().strftime('%H:%M:%S')}")
    report_lines.append(f"**Model Mode:** {'Generic Lineups (FORCED)' if force_generic else 'Standard (Confirmed if available)'}")
    report_lines.append("")
    
    priority_flags = []
    game_blocks = []
    raw_json_data = []
    gatekeeper_rows = []

    # MULTIPROCESSING POOL
    # Windows requires the main module idiom, which is safely guarded by the if __name__ block
    pool_args = [(g, sport_id, force_generic) for g in games]
    
    num_processes = min(8, cpu_count() or 4)
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_single_game, pool_args)
        
    for r in results:
        game_blocks.extend(r['game_blocks'])
        priority_flags.extend(r['priority_flags'])
        if r['raw_json_data']:
            raw_json_data.append(r['raw_json_data'])
        if r.get('gatekeeper_data'):
            gatekeeper_rows.append(r['gatekeeper_data'])

    # 5. Assemble final report
    if priority_flags:
        report_lines.append("## 🚨 TOP PRIORITY GAMES 🚨")
        report_lines.extend(priority_flags)
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
    if gatekeeper_rows:
        df = pd.DataFrame(gatekeeper_rows)
        gatekeeper_report, structured_data = generate_v6_premium_45_gatekeeper(df)
        
        # Inject structured data back into the raw_json_data per game
        for g in raw_json_data:
            game_key = f"{g['away_team']} @ {g['home_team']}"
            if game_key in structured_data:
                g['gatekeeper_logic'] = structured_data[game_key]
            else:
                g['gatekeeper_logic'] = {"category": "No Edge", "reason": "Did not meet divergence thresholds."}

        report_lines.append(gatekeeper_report)
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    report_lines.extend(game_blocks)
        
    # Use dated filename so reports never overwrite each other
    if team_filter:
        safe_team = team_filter.replace(' ', '_').lower()
        filename = f"{safe_team}_consensus_f5_v3_report_{report_date}.md"
    else:
        filename = f"consensus_f5_v3_report_{league_name}_{report_date}.md" if sport_id != 1 else f"consensus_f5_v3_report_{report_date}.md"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    # Save structured JSON payload for the frontend data bridge
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'baseball')
    os.makedirs(data_dir, exist_ok=True)
    
    # Always append date. Use report_date defined earlier in the function.
    mode_suffix = "generic" if force_generic else "confirmed"
    json_filename = f"universal_predictions_{report_date}-{mode_suffix}.json"
    json_output_path = os.path.join(data_dir, json_filename)
    
    # Frontend wrapper format expects {"predictions": [...]}
    frontend_payload = {
        "date": report_date,
        "mode": mode_suffix,
        "total_predictions": len(raw_json_data),
        "predictions": raw_json_data
    }
    
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(frontend_payload, f, indent=4)
        
    print(f"\nDone! Report written to {output_path}")
    print(f"JSON data bridged to {json_output_path}")
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate MLB or MiLB Consensus F5 Report")
    parser.add_argument('--sportId', type=int, default=1, help='1=MLB, 11=AAA, 12=AA, 13=High-A, 14=Single-A')
    parser.add_argument('--date', type=str, default=None, help='Date in MM/DD/YYYY format (default: today)')
    parser.add_argument('--generic', action='store_true', help='Force the model to use Generic lineups even if confirmed lineups are available')
    parser.add_argument('--team', nargs='+', type=str, default=None, help='Filter the report to only include games matching this team name')
    args = parser.parse_args()
    
    team_str = " ".join(args.team) if args.team else None
    generate_consensus_report(args.sportId, date_str=args.date, force_generic=args.generic, team_filter=team_str)
