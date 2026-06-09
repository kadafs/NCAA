"""
kbo/consensus_f5_kbo.py
=======================
KBO First 5 Innings Consensus Report Generator.

Architecture mirrors mlb/consensus_f5.py but uses:
  - kbo/fetch_schedule.py   for schedule + probable starters
  - kbo/fetch_metrics.py    for pitcher FIP proxy, bullpen FIP, team wRC+
  - kbo/park_factors.py     for static stadium park factors
  - mlb/grade_f5.py         for Top-Down run calculation (sport-agnostic)
  - mlb/v1/monte_carlo_v1.py for Monte Carlo simulation (stable V1 engine)

Usage:
  python kbo/consensus_f5_kbo.py
  python kbo/consensus_f5_kbo.py --date 06/10/2026
"""

import os
import sys
import time
import datetime
import argparse

# Add the project root to path so we can import mlb modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'mlb'))

from mlb.grade_f5 import grade_matchup
from mlb.v1.monte_carlo_v1 import run_monte_carlo_f5
from kbo.fetch_schedule import get_today_games
from kbo.fetch_metrics import (
    get_pitcher_fip,
    get_pitcher_projected_ip,
    get_team_bullpen_fip,
    get_team_wrc_proxy,
    KBO_LEAGUE_AVG_FIP,
)
from kbo.park_factors import get_kbo_park_factor


def _retry_call(fn, *args, retries=3, delay=2.0, **kwargs):
    """Retry wrapper for network calls."""
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt < retries - 1:
                print(f"  [Retry {attempt+1}/{retries}] {fn.__name__} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise


def get_advice(line: float, td_total: float, under_prob: float) -> str:
    """Returns betting advice string for a given line."""
    td_gap    = line - td_total       # positive = TD says Under
    td_signal = 'UNDER' if td_gap > 0 else 'OVER'

    if under_prob >= 0.52:
        mc_signal = 'UNDER'
    elif under_prob <= 0.48:
        mc_signal = 'OVER'
    else:
        mc_signal = 'SKIP'

    # Both must agree; need meaningful TD gap
    if mc_signal == 'SKIP':
        return f"Skip | MC Under Probability: {round(under_prob*100)}%"

    if td_signal != mc_signal:
        return f"Skip | MC Under Probability: {round(under_prob*100)}%"

    gap_abs = abs(td_gap)
    if gap_abs >= 0.75:
        conf = "HIGH"
    elif gap_abs >= 0.3:
        conf = "MODERATE"
    else:
        return f"Skip | MC Under Probability: {round(under_prob*100)}%"

    return f"Bet **{mc_signal}** ({conf}) | MC Under Probability: {round(under_prob*100)}%"


def generate_kbo_report(date_str: str | None = None) -> str:
    """
    Main report generator. Fetches today's KBO slate, runs Top-Down + MC,
    and writes a markdown report.
    Returns the output file path.
    """
    games = get_today_games(date_str)

    if not games:
        print("No KBO games found for the specified date.")
        return ""

    display_date = date_str or datetime.datetime.now().strftime('%m/%d/%Y')
    report_lines = []
    report_lines.append(f"# ⚾ KBO F5 Prediction Report")
    report_lines.append(f"**Date:** {display_date}")
    report_lines.append(f"**Generated:** {datetime.datetime.now().strftime('%H:%M:%S')}")
    report_lines.append(f"**Model:** V2 Hybrid (Current Top-Down + V1 Monte Carlo)")
    report_lines.append("")

    priority_games = []
    game_blocks    = []

    print(f"\nGenerating KBO F5 Report for {len(games)} games...")

    for game in games:
        away = game['away_team']
        home = game['home_team']
        venue = game['venue']
        away_starter = game.get('away_starter') or 'TBD'
        home_starter = game.get('home_starter') or 'TBD'

        pf, is_roofed = get_kbo_park_factor(home)
        # No weather adjustment for roofed stadiums
        weather_mult = 1.0

        print(f"\nProcessing: {away} @ {home} (PF: {pf:.2f}, Roofed: {is_roofed})")

        try:
            # --- Fetch Metrics ---
            ap_fip = _retry_call(get_pitcher_fip, away_starter) if away_starter != 'TBD' else KBO_LEAGUE_AVG_FIP
            hp_fip = _retry_call(get_pitcher_fip, home_starter) if home_starter != 'TBD' else KBO_LEAGUE_AVG_FIP
            ap_ip  = _retry_call(get_pitcher_projected_ip, away_starter) if away_starter != 'TBD' else 5.0
            hp_ip  = _retry_call(get_pitcher_projected_ip, home_starter) if home_starter != 'TBD' else 5.0
            away_bp  = _retry_call(get_team_bullpen_fip, away)
            home_bp  = _retry_call(get_team_bullpen_fip, home)
            away_wrc = _retry_call(get_team_wrc_proxy, away)
            home_wrc = _retry_call(get_team_wrc_proxy, home)

            # KBO pitchers are predominantly RHP (no hand data available)
            ap_hand = 'R'
            hp_hand = 'R'

            # --- Top-Down Model ---
            top_down = grade_matchup(
                away, ap_fip, away_bp, ap_ip, away_wrc,
                home, hp_fip, home_bp, hp_ip, home_wrc,
                park_factor=pf,
                weather_multiplier=weather_mult,
                away_pitcher_hand=ap_hand,
                home_pitcher_hand=hp_hand,
            )
            td_total = top_down['projected_f5_total']

            # --- Monte Carlo (V1 — no lineup data available, use generic) ---
            mc = run_monte_carlo_f5(
                [], [],  # empty = generic lineups
                away_starter, home_starter,
                ap_fip, hp_fip,
                iterations=10000,
                park_factor=pf,
            )
            mc_total      = mc.get('f5_total', td_total)
            under_prob_45 = mc.get('under_4_5_prob', 0.5)
            under_prob_35 = mc.get('under_3_5_prob', round(under_prob_45 + 0.12, 3))
            under_prob_55 = mc.get('under_5_5_prob', round(under_prob_45 - 0.11, 3))

            # V1 MC doesn't return f5_total directly — derive from under probs
            # (use td_total as the display total since V1 doesn't expose f5_total)
            if mc_total == td_total and 'f5_total' not in mc:
                # Estimate MC total from median: if 50% under 4.5, MC total ~= 4.5
                # Interpolate between 3.5/4.5/5.5 based on under probabilities
                if under_prob_45 > 0.55:
                    mc_total = 4.5 - (under_prob_45 - 0.5) * 2.0
                elif under_prob_45 < 0.45:
                    mc_total = 4.5 + (0.5 - under_prob_45) * 2.0
                else:
                    mc_total = 4.5

            # --- Betting Advice ---
            advice_35 = get_advice(3.5, td_total, under_prob_35)
            advice_45 = get_advice(4.5, td_total, under_prob_45)
            advice_55 = get_advice(5.5, td_total, under_prob_55)

            # --- Flag High Confidence ---
            td_gap_45 = abs(4.5 - td_total)
            is_high_conf = td_gap_45 >= 0.75 and (
                (under_prob_45 >= 0.60) or (under_prob_45 <= 0.40)
            )
            flag = "🚨 " if is_high_conf else ""
            if is_high_conf:
                priority_games.append(f"- **{away} @ {home}:** High Confidence Edge")

            # --- Build Game Block ---
            block = []
            block.append(f"### {flag}{away} ({away_starter}) @ {home} ({home_starter})")
            if is_high_conf:
                block.append(f"**🔥 FLAGGED:** High Confidence Edge")
            block.append(f"🏙️ **{venue}** (Park Factor: {pf}x){' 🏠 Roofed' if is_roofed else ''}")
            block.append(f"- **Pitcher Matchup:** {away_starter} (FIP proxy: {ap_fip:.2f}) "
                         f"vs {home_starter} (FIP proxy: {hp_fip:.2f})")
            block.append(f"- **Top-Down Projected F5 Total:** {td_total:.2f} Runs")
            block.append(f"- **Monte Carlo Simulated F5 Total:** {mc_total:.2f} Runs (Generic Lineups)")
            block.append(f"- 🎯 **ACTION MATRIX (Based on your Sportsbook's Line):**")
            block.append(f"  - If Line is **3.5** -> {advice_35}")
            block.append(f"  - If Line is **4.5** -> {advice_45}")
            block.append(f"  - If Line is **5.5** -> {advice_55}")
            game_blocks.append("\n".join(block))

        except Exception as e:
            print(f"  ⚠️  SKIPPED {away} @ {home}: {e}")
            game_blocks.append(f"### {away} @ {home}\n⚠️ Skipped: {e}")

    # --- Assemble Report ---
    if priority_games:
        report_lines.append("## 🚨 TOP PRIORITY GAMES 🚨")
        report_lines.extend(priority_games)
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    report_lines.extend("\n\n".join(game_blocks).split("\n"))

    # --- Write to file ---
    output_dir = os.path.dirname(os.path.abspath(__file__))
    if date_str:
        safe_date = date_str.replace('/', '-')
        filename  = f"kbo_f5_report_{safe_date}.md"
    else:
        filename = "kbo_f5_report.md"

    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    print(f"\nDone! KBO report written to {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate KBO F5 Prediction Report')
    parser.add_argument('--date', type=str, default=None,
                        help='Date in MM/DD/YYYY format (default: today KST)')
    args = parser.parse_args()
    generate_kbo_report(args.date)
