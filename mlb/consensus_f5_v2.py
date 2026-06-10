import os
import time
import datetime
from run_daily_f5 import get_today_games, get_pitcher_fip, get_team_wrc_proxy, get_team_bullpen_fip, get_pitcher_projected_ip
from grade_f5 import grade_matchup
from fetch_lineups import get_lineup_for_game, get_pitcher_hand
from v1.monte_carlo_v1 import run_monte_carlo_f5
from park_factors import get_park_factor
from weather_f5 import get_weather_modifier


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

def generate_consensus_report(sport_id=1, date_str=None, force_generic=False):
    """
    date_str: optional date in MM/DD/YYYY format. Defaults to today.
    force_generic: if True, skips fetching confirmed lineups and uses the generic league-average weights.
    """
    games = get_today_games(sport_id, date_str=date_str)
    if not games:
        print(f"No games found for sportId={sport_id} on {date_str or 'today'}.")
        return
        
    report_date = date_str or datetime.datetime.now().strftime('%Y-%m-%d')
    print(f"Generating Consensus Report for {len(games)} games on {report_date}...")
    
    league_name = "MLB"
    if sport_id == 11: league_name = "AAA"
    elif sport_id == 12: league_name = "AA"
    elif sport_id == 13: league_name = "High-A"
    elif sport_id == 14: league_name = "Single-A"
    date_label = date_str if date_str else datetime.datetime.now().strftime('%m/%d/%Y')
    
    report_lines = []
    report_lines.append(f"# ⚾ V2 Hybrid F5 Prediction Report (Sport ID: {sport_id})")
    report_lines.append(f"**Date:** {date_label}")
    report_lines.append(f"**Generated:** {datetime.datetime.now().strftime('%H:%M:%S')}")
    report_lines.append(f"**Model Mode:** {'Generic Lineups (FORCED)' if force_generic else 'Standard (Confirmed if available)'}")
    report_lines.append("")
    
    priority_flags = []
    game_blocks = []

    for game in games:
        away = game['away_team']
        home = game['home_team']
        ap = game['away_pitcher']
        hp = game['home_pitcher']
        gid = game['game_id']
        venue = game.get('venue_name', 'Unknown Venue')
        pf = get_park_factor(venue)
        
        print(f"Processing: {away} @ {home} ({venue} - PF: {pf})")
        
        try:
            # Weather modifier (MLB only — MiLB parks not covered by RotoWire)
            weather         = None
            weather_mult    = 1.0
            effective_pf    = pf
            if sport_id == 1:
                weather      = get_weather_modifier(venue, away_abbr=away, home_abbr=home)
                weather_mult = weather.get('weather_multiplier', 1.0)
                # Issue 1 fix: MULTIPLICATIVE composition, not additive.
                # Old: pf + (wx - 1)  e.g. 1.15 + 0.15 = 1.30  (wrong — ignores compounding)
                # New: pf × wx        e.g. 1.15 × 1.15 = 1.32  (correct physical stacking)
                effective_pf = round(pf * weather_mult, 4)

            # 1. Top-Down Model
            ap_fip = _retry_call(get_pitcher_fip, ap, sport_id=sport_id)
            hp_fip = _retry_call(get_pitcher_fip, hp, sport_id=sport_id)

            ap_ip = _retry_call(get_pitcher_projected_ip, ap, sport_id=sport_id)
            hp_ip = _retry_call(get_pitcher_projected_ip, hp, sport_id=sport_id)

            away_bp = _retry_call(get_team_bullpen_fip, away, sport_id=sport_id)
            home_bp = _retry_call(get_team_bullpen_fip, home, sport_id=sport_id)

            away_wrc = _retry_call(get_team_wrc_proxy, away, sport_id)
            home_wrc = _retry_call(get_team_wrc_proxy, home, sport_id)

            # Pitcher handedness for platoon logic (MLB only)
            if sport_id == 1:
                ap_hand = _retry_call(get_pitcher_hand, ap, sport_id=sport_id)
                hp_hand = _retry_call(get_pitcher_hand, hp, sport_id=sport_id)
            else:
                ap_hand, hp_hand = 'R', 'R'

            # Issue 1 + 3 fix: pass park_factor and weather_multiplier separately
            # (not blended), and pass pitcher hands so platoon adjustment fires.
            top_down = grade_matchup(
                away, ap_fip, away_bp, ap_ip, away_wrc,
                home, hp_fip, home_bp, hp_ip, home_wrc,
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

            # Check if lineups exist, otherwise MC uses league average generic lineups.
            lineups_status = "Confirmed" if lineups['away'] else "Projected (Generic)"
            mc = run_monte_carlo_f5(
                lineups['away'], lineups['home'],
                ap, hp, ap_fip, hp_fip,
                iterations=10000, park_factor=pf
            )
            
            # 3. Betting Matrix Logic (Issue 2 fix)
            # TD signal now carries a *strength* dimension:
            # - Distance from line captures how emphatic the top-down call is.
            # - A TD projection of 3.1 vs a 4.5 line (gap=1.4) is far stronger
            #   than a TD projection of 4.3 vs a 4.5 line (gap=0.2).
            # Both models must agree on direction to produce a 'Bet' signal.
            # Confidence tier requires MC >58%/>42% AND TD gap >=0.3 runs.
            def get_advice(line, under_prob):
                td_gap     = line - td_total           # positive = TD says Under
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
                    return f'Bet **{mc_signal}** ({confidence})'
                return 'Skip'

            adv_3_5 = get_advice(3.5, mc['under_3_5_prob'])
            adv_4_5 = get_advice(4.5, mc['under_4_5_prob'])
            adv_5_5 = get_advice(5.5, mc['under_5_5_prob'])
            
            # 4. Format Output
            block_lines = []
            is_priority = False
            flag_reasons = []

            # Check for extreme weather
            if weather:
                eff_pct_val = (effective_pf - 1.0) * 100
                if abs(eff_pct_val) >= 5.0:
                    is_priority = True
                    flag_reasons.append(f"Extreme Weather ({'+' if eff_pct_val>0 else ''}{round(eff_pct_val,1)}%)")

            # Check for high confidence edges
            for adv in [adv_3_5, adv_4_5, adv_5_5]:
                if "Bet" in adv and "Skip" not in adv:
                    if mc['under_4_5_prob'] >= 0.58 or mc['under_4_5_prob'] <= 0.42:
                        is_priority = True
                        flag_reasons.append("High Confidence Edge")
                        break

            title = f"### {'🚨 ' if is_priority else ''}{away} ({ap}) @ {home} ({hp})"
            block_lines.append(title)
            
            if is_priority:
                block_lines.append(f"**🔥 FLAGGED:** {', '.join(set(flag_reasons))}")
                priority_flags.append(f"- **{away} @ {home}:** {', '.join(set(flag_reasons))}")

            block_lines.append(f"🏙️ **{venue}** (Park Factor: {pf}x)")
            if weather:
                eff_pct = round((effective_pf - 1.0) * 100, 1)
                sign = '+' if eff_pct >= 0 else ''
                block_lines.append(f"🌤️ **Weather:** {weather['weather_label']} | Effective PF: {effective_pf}x ({sign}{eff_pct}%)")
            block_lines.append(f"- **Pitcher Matchup:** {ap} ({ap_hand}HP, FIP: {ap_fip}) vs {hp} ({hp_hand}HP, FIP: {hp_fip})")
            block_lines.append(f"- **Top-Down Projected F5 Total:** {td_total} Runs")
            block_lines.append(f"- **Monte Carlo Simulated F5 Total:** {mc['mc_total_runs']} Runs (Lineups: {lineups_status})")
            block_lines.append(f"- 🎯 **ACTION MATRIX (Based on your Sportsbook's Line):**")
            block_lines.append(f"  - If Line is **3.5** -> {adv_3_5} | MC Under Probability: {int(mc['under_3_5_prob']*100)}%")
            block_lines.append(f"  - If Line is **4.5** -> {adv_4_5} | MC Under Probability: {int(mc['under_4_5_prob']*100)}%")
            block_lines.append(f"  - If Line is **5.5** -> {adv_5_5} | MC Under Probability: {int(mc['under_5_5_prob']*100)}%")
            block_lines.append("")
            
            game_blocks.extend(block_lines)
            
        except Exception as e:
            print(f"  ⚠️  SKIPPED {away} @ {home}: {type(e).__name__}: {e}")
            game_blocks.append(f"### {away} @ {home} — ⚠️ Data Error (skipped)")
            game_blocks.append(f"Error: {type(e).__name__}: {e}")
            game_blocks.append("")
        
        # Brief pause between games to avoid rate-limiting the MLB Stats API
        time.sleep(0.5)

    # 5. Assemble final report
    if priority_flags:
        report_lines.append("## 🚨 TOP PRIORITY GAMES 🚨")
        report_lines.extend(priority_flags)
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    report_lines.extend(game_blocks)
        
    # Use dated filename for historical runs so they don't overwrite today's report
    league_name_val = league_name
    if date_str:
        safe_date = date_str.replace('/', '-')
        filename = f"consensus_f5_v2_report_{league_name_val}_{safe_date}.md"
    else:
        filename = f"consensus_f5_v2_report_{league_name_val}.md" if sport_id != 1 else "consensus_f5_v2_report.md"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    print(f"\nDone! Report written to {output_path}")
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate MLB or MiLB Consensus F5 Report")
    parser.add_argument('--sportId', type=int, default=1, help='1=MLB, 11=AAA, 12=AA, 13=High-A, 14=Single-A')
    parser.add_argument('--date', type=str, default=None, help='Date in MM/DD/YYYY format (default: today)')
    parser.add_argument('--generic', action='store_true', help='Force the model to use Generic lineups even if confirmed lineups are available')
    args = parser.parse_args()
    
    generate_consensus_report(args.sportId, date_str=args.date, force_generic=args.generic)
