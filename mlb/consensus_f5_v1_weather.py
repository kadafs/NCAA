"""
consensus_f5_v1_weather.py
==========================
The "V1.5" model.
This takes the original simple V1 math ((FIP/9)*5) and purely sequential Monte Carlo,
but injects real-time weather data (temperature + wind modifiers) into the Park Factor.

Key differences from V1 Static:
  - Multiplies the static park factor by the real-time weather modifier.

Key differences from Current Model:
  - Uses sequential python MC (no NumPy vectorization)
  - No TTO (Times Through the Order) penalties
  - No platoon L/R split adjustments
  - No runner speed tiers
  - 2,000 iterations (vs 10,000 in current)

Run with:
    python mlb/consensus_f5_v1_weather.py
    python mlb/consensus_f5_v1_weather.py --date 06/09/2026
"""

import sys
import os
import datetime
import argparse

# Insert mlb/ into path for shared infrastructure imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'v1'))

from run_daily_f5 import get_today_games, get_pitcher_fip, get_team_wrc_proxy
from fetch_lineups import get_lineup_for_game
from park_factors import get_park_factor
from weather_f5 import get_weather_modifier

# V1-specific imports
from monte_carlo_v1 import run_monte_carlo_f5
from grade_f5_v1 import grade_matchup


def generate_v1_weather_report(sport_id=1, date_str=None, force_generic=False):
    games = get_today_games(sport_id, date_str=date_str)
    if not games:
        print(f"No games found for sportId={sport_id} on {date_str or 'today'}.")
        return

    report_date = date_str or datetime.datetime.now().strftime('%Y-%m-%d')
    print(f"\n[V1+Weather] Generating consensus report for {len(games)} games on {report_date}...")
    print(f"[V1+Weather] Model: Simple FIP/wRC+ | Sequential MC | WITH WEATHER | {'GENERIC LINEUPS' if force_generic else 'CONFIRMED LINEUPS'}\n")

    report_lines = [
        f"# MLB F5 V1.5 (Weather) Consensus Picks - {report_date}",
        f"> **V1.5 Model** — FIP/wRC+ top-down + 2,000-iteration sequential Monte Carlo + Weather Park Factors.",
        f"> Lineup Mode: {'**Generic Averages (Forced)**' if force_generic else 'Confirmed (if available)'}",
        "",
    ]

    flagged = []

    for game in games:
        away    = game['away_team']
        home    = game['home_team']
        ap      = game['away_pitcher']
        hp      = game['home_pitcher']
        gid     = game['game_id']
        venue   = game.get('venue_name', 'Unknown Venue')
        
        # ── 1. Fetch Weather & Park Factor ──────────────────────────────────
        static_pf = get_park_factor(venue)
        weather = get_weather_modifier(venue, away, home)
        weather_mult = weather.get('weather_multiplier', 1.0)
        weather_label = weather.get('weather_label', 'Unknown Weather')
        
        # Create Effective PF
        effective_pf = round(static_pf * weather_mult, 4)

        print(f"  Processing: {away} @ {home}...")

        # ── 2. Top-Down Model (V1 formula) ──────────────────────────────────
        ap_fip   = get_pitcher_fip(ap)
        hp_fip   = get_pitcher_fip(hp)
        away_wrc = get_team_wrc_proxy(away, sport_id)
        home_wrc = get_team_wrc_proxy(home, sport_id)

        top_down  = grade_matchup(away, ap_fip, away_wrc, home, hp_fip, home_wrc, park_factor=effective_pf)
        td_total  = top_down['projected_f5_total']

        # ── 3. Monte Carlo (V1 sequential) ──────────────────────────────────
        if force_generic:
            lineups = {'away': [], 'home': []}
            lineups_status = "Generic (Forced)"
        else:
            lineups = get_lineup_for_game(gid)
            lineups_status = "Confirmed" if lineups['away'] else "Generic (Fallback)"

        mc = run_monte_carlo_f5(
            lineups['away'], lineups['home'],
            ap, hp,
            ap_fip, hp_fip,
            iterations=2000,
            park_factor=effective_pf
        )

        mc_total       = round(mc.get('mc_total_runs', mc.get('median_total', 0)), 2)
        under_3_5_prob = mc.get('under_3_5_prob', 0.5)
        under_4_5_prob = mc.get('under_4_5_prob', 0.5)
        under_5_5_prob = mc.get('under_5_5_prob', 0.5)

        # ── 4. Betting Matrix (same logic as V1) ────────────────────────────
        def get_advice(line, under_prob):
            td_signal = "UNDER" if td_total < line else "OVER"
            mc_signal = "NEUTRAL"
            if under_prob >= 0.52:
                mc_signal = "UNDER"
            elif under_prob <= 0.48:
                mc_signal = "OVER"

            if td_signal == mc_signal:
                confidence = "HIGH" if (under_prob >= 0.58 or under_prob <= 0.42) else "MODERATE"
                return f"Bet **{mc_signal}** ({confidence})", mc_signal, confidence
            return "Skip", "NEUTRAL", ""

        adv_3_5, sig_3_5, conf_3_5 = get_advice(3.5, under_3_5_prob)
        adv_4_5, sig_4_5, conf_4_5 = get_advice(4.5, under_4_5_prob)
        adv_5_5, sig_5_5, conf_5_5 = get_advice(5.5, under_5_5_prob)

        # Flag if any HIGH confidence pick exists
        is_flagged = any(c == "HIGH" for c in [conf_3_5, conf_4_5, conf_5_5])
        if is_flagged:
            flagged.append(f"**{away} @ {home}:** High Confidence Edge")

        # ── 5. Format report section ─────────────────────────────────────────
        header = f"### {'🚨 ' if is_flagged else ''}{away} ({ap}) @ {home} ({hp})"
        report_lines.append(header)
        if is_flagged:
            report_lines.append("**🔥 FLAGGED:** High Confidence Edge")
        report_lines.append(f"🏙️ **{venue}** (Base PF: {static_pf}x)")
        report_lines.append(f"🌤️ **Weather:** {weather_label} | Effective PF: {effective_pf}x")
        report_lines.append(f"- **V1.5 Top-Down Projected F5 Total:** {td_total} Runs")
        report_lines.append(f"- **V1.5 Monte Carlo Simulated F5 Total:** {mc_total} Runs (Lineups: {lineups_status})")
        report_lines.append(f"- 🎯 **ACTION MATRIX (Based on your Sportsbook's Line):**")
        report_lines.append(f"  - If Line is **3.5** -> {adv_3_5} | MC Under Probability: {round(under_3_5_prob*100)}%")
        report_lines.append(f"  - If Line is **4.5** -> {adv_4_5} | MC Under Probability: {round(under_4_5_prob*100)}%")
        report_lines.append(f"  - If Line is **5.5** -> {adv_5_5} | MC Under Probability: {round(under_5_5_prob*100)}%")
        report_lines.append("")

    # ── Summary Header ───────────────────────────────────────────────────────
    summary = ["## 🏆 V1.5 High Confidence Picks Summary", ""]
    if flagged:
        for f in flagged:
            summary.append(f"- {f}")
    else:
        summary.append("- No high confidence picks today.")
    summary.append("")

    final_report = report_lines[:4] + summary + report_lines[4:]

    # ── Write Report ─────────────────────────────────────────────────────────
    report_path = os.path.join(os.path.dirname(__file__), 'consensus_f5_v1_weather_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_report))

    print(f"\n[V1+Weather] Report saved -> {report_path}")
    print(f"[V1+Weather] Flagged games: {len(flagged)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="V1.5 Simple F5 Consensus Engine (Weather Adjusted)")
    parser.add_argument('--date', type=str, help='Date in MM/DD/YYYY format', default=None)
    parser.add_argument('--force_generic', action='store_true', help='Force generic lineups (ignore confirmed)')
    args = parser.parse_args()
    generate_v1_weather_report(date_str=args.date, force_generic=args.force_generic)
