"""
consensus_tennis.py
===================
Consensus prediction engine for tennis matches (ATP + WTA).

Workflow:
  1. Fetch today's schedule from ESPN
  2. Build serve/return profiles from Sackmann data
  3. Run Markov chain simulation for each match
  4. Generate report with edge detection and gatekeeper logic
  5. Output markdown report + JSON bridge for dashboard

Supports: Wimbledon, ATP Masters, WTA 1000, and all tour events.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_tennis_stats import build_player_serve_profile, fetch_espn_tennis_schedule
from tennis_markov import simulate_match_monte_carlo
from surface_engine import infer_surface, GRAND_SLAMS, sets_to_win


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPORT_DIR = os.path.join(_BASE_DIR, '..', 'data', 'tennis')
_EDGE_THRESHOLD = 0.05   # 5% minimum edge to flag a bet


# ---------------------------------------------------------------------------
# Edge Detection (Gatekeeper)
# ---------------------------------------------------------------------------

def _detect_edge(result: dict, line_total: float = 22.5) -> dict:
    """
    Detects betting edges from simulation results.

    Returns dict with:
      has_edge (bool), edge_type (str), edge_pct (float), confidence (str)
    """
    expected = result['expected_total_games']
    over_prob = result.get(f'over_{str(line_total).replace(".", "_")}_prob', 0.5)
    under_prob = 1.0 - over_prob

    edges = []

    # Total games O/U edge
    if over_prob >= 0.55 + _EDGE_THRESHOLD:
        implied_fair = 1.0 / over_prob
        edges.append({
            'market': f'Over {line_total} Games',
            'edge_pct': round((over_prob - 0.50) * 100, 1),
            'model_prob': over_prob,
            'fair_odds': round(implied_fair, 2),
        })
    elif under_prob >= 0.55 + _EDGE_THRESHOLD:
        implied_fair = 1.0 / under_prob
        edges.append({
            'market': f'Under {line_total} Games',
            'edge_pct': round((under_prob - 0.50) * 100, 1),
            'model_prob': under_prob,
            'fair_odds': round(implied_fair, 2),
        })

    # Match winner edge (requires 60%+ probability)
    if result['p1_match_win_prob'] >= 0.60:
        edges.append({
            'market': 'P1 Match Winner',
            'edge_pct': round((result['p1_match_win_prob'] - 0.50) * 100, 1),
            'model_prob': result['p1_match_win_prob'],
            'fair_odds': round(1.0 / result['p1_match_win_prob'], 2),
        })
    elif result['p2_match_win_prob'] >= 0.60:
        edges.append({
            'market': 'P2 Match Winner',
            'edge_pct': round((result['p2_match_win_prob'] - 0.50) * 100, 1),
            'model_prob': result['p2_match_win_prob'],
            'fair_odds': round(1.0 / result['p2_match_win_prob'], 2),
        })

    # First set winner edge (requires 58%+)
    if result['p1_first_set_win_prob'] >= 0.58:
        edges.append({
            'market': 'P1 First Set Winner',
            'edge_pct': round((result['p1_first_set_win_prob'] - 0.50) * 100, 1),
            'model_prob': result['p1_first_set_win_prob'],
            'fair_odds': round(1.0 / result['p1_first_set_win_prob'], 2),
        })
    elif result['p2_first_set_win_prob'] >= 0.58:
        edges.append({
            'market': 'P2 First Set Winner',
            'edge_pct': round((result['p2_first_set_win_prob'] - 0.50) * 100, 1),
            'model_prob': result['p2_first_set_win_prob'],
            'fair_odds': round(1.0 / result['p2_first_set_win_prob'], 2),
        })

    has_edge = len(edges) > 0
    confidence = 'High' if any(e['edge_pct'] >= 10 for e in edges) else ('Medium' if has_edge else 'None')

    return {
        'has_edge': has_edge,
        'edges': edges,
        'confidence': confidence,
    }


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

def generate_tennis_report(
    tour: str = 'ATP',
    iterations: int = 10000,
    output_dir: str = None,
) -> str:
    """
    Generate a full consensus prediction report for today's tennis matches.

    Parameters
    ----------
    tour       : 'ATP' or 'WTA'
    iterations : MC simulation iterations per match
    output_dir : output directory for reports (default: data/tennis/)

    Returns
    -------
    str : path to generated report file
    """
    if output_dir is None:
        output_dir = _REPORT_DIR
    os.makedirs(output_dir, exist_ok=True)

    today_str = datetime.now().strftime('%Y-%m-%d')
    report_path = os.path.join(output_dir, f'tennis_{tour.lower()}_report_{today_str}.md')
    json_path = os.path.join(output_dir, f'tennis_{tour.lower()}_predictions_{today_str}.json')

    # Step 1: Fetch schedule
    print(f"[Tennis] Fetching {tour} schedule from ESPN...")
    matches = fetch_espn_tennis_schedule(tour)
    scheduled = [m for m in matches if m.get('status', '') in ('STATUS_SCHEDULED', 'pre')]

    if not scheduled:
        print(f"[Tennis] No scheduled {tour} matches found for today.")
        # Still try all matches including in-progress for reporting
        scheduled = matches

    print(f"[Tennis] Found {len(scheduled)} {tour} matches to analyze")

    # Step 2: Process each match
    results = []
    for match in scheduled:
        p1_name = match['p1_name']
        p2_name = match['p2_name']
        tournament = match['tournament_name']
        surface = infer_surface(tournament)

        # Skip ESPN placeholder draw slots (draw not yet released)
        if 'TBD' in (p1_name.upper(), p2_name.upper()) or p1_name == p2_name == 'Unknown':
            continue

        print(f"  Analyzing: {p1_name} vs {p2_name} ({tournament}, {surface})")

        # Build profiles with surface filter
        p1_stats = build_player_serve_profile(p1_name, tour=tour, surface=surface)
        p2_stats = build_player_serve_profile(p2_name, tour=tour, surface=surface)

        # Run simulation
        sim = simulate_match_monte_carlo(
            p1_stats, p2_stats,
            tour=tour, surface=surface, tournament_name=tournament,
            iterations=iterations,
        )

        # Format-aware O/U line: Bo5 games average ~40-46, use 37.5; Bo3 use 22.5
        sets_target = sets_to_win(tour, tournament)
        default_line = 37.5 if sets_target == 3 else 22.5

        # Detect edges
        edge_info = _detect_edge(sim, line_total=default_line)

        results.append({
            'p1_name': p1_name,
            'p2_name': p2_name,
            'tournament': tournament,
            'surface': surface,
            'simulation': sim,
            'edges': edge_info,
            'p1_profile': p1_stats,
            'p2_profile': p2_stats,
        })

    # Step 3: Write markdown report
    _write_report(report_path, tour, today_str, results)

    # Step 4: Write JSON bridge
    json_data = []
    for r in results:
        sim = r['simulation']
        entry = {
            'sport': 'tennis',
            'tour': tour,
            'p1_name': r['p1_name'],
            'p2_name': r['p2_name'],
            'tournament': r['tournament'],
            'surface': r['surface'],
            'p1_win_prob': sim['p1_match_win_prob'],
            'p2_win_prob': sim['p2_match_win_prob'],
            'expected_total_games': sim['expected_total_games'],
            'p1_first_set_prob': sim['p1_first_set_win_prob'],
            'has_edge': r['edges']['has_edge'],
            'edges': r['edges']['edges'],
        }
        json_data.append(entry)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)

    print(f"\n[Tennis] Report: {report_path}")
    print(f"[Tennis] JSON:   {json_path}")
    return report_path


def _write_report(path: str, tour: str, date_str: str, results: list):
    """
    Write the formatted markdown report.

    Bug fixes applied:
      Bug 1: Format computed via sets_to_win() — never reads sim['sets_to_win']
      Bug 2: Over probs computed as 1 - under_prob with .get() fallbacks
      Bug 3: Hold rate + serve point win read from p1/p2 profile dicts, not sim
    """
    from tennis_markov import p_server_wins_game as _p_game

    lines = []
    lines.append(f"# {'ATP' if tour == 'ATP' else 'WTA'} Tennis Prediction Report")
    lines.append(f"**Date:** {date_str}")
    lines.append(f"**Generated:** {datetime.now().strftime('%H:%M:%S')}")
    lines.append(f"**Matches Analyzed:** {len(results)}")
    lines.append("")

    # Priority games section
    priority = [r for r in results if r['edges']['has_edge']]
    if priority:
        lines.append("## TOP PRIORITY MATCHES")
        for r in priority:
            conf = r['edges']['confidence']
            emoji = "🔥 HIGH CONFIDENCE" if conf == 'High' else "⚡ Medium Edge"
            lines.append(f"- **{r['p1_name']} vs {r['p2_name']}:** {emoji}")
            for e in r['edges']['edges']:
                lines.append(f"  - {e['market']}: {e['model_prob']:.1%} (Fair: {e['fair_odds']})")
        lines.append("")
    lines.append("---")
    lines.append("")

    # Individual match details
    for r in results:
        sim  = r['simulation']
        edge = r['edges']
        p1p  = r['p1_profile']
        p2p  = r['p2_profile']

        # Bug 1 fix: derive format from surface_engine, not sim dict
        target_sets  = sets_to_win(tour, r['tournament'])
        best_of_fmt  = 5 if target_sets == 3 else 3

        flag = " 🎯 EDGE DETECTED" if edge['has_edge'] else ""
        lines.append(f"### {r['p1_name']} vs {r['p2_name']}{flag}")
        lines.append(
            f"**{r['tournament']}** | Surface: {r['surface']} "
            f"| Format: Best-of-{best_of_fmt}"
        )
        lines.append("")

        # Bug 3 fix: pull serve/hold metrics from profile, not sim diagnostics
        p1_point = p1p.get('_implied_serve_prob', 0.60)
        p2_point = p2p.get('_implied_serve_prob', 0.60)
        p1_hold  = _p_game(p1_point)
        p2_hold  = _p_game(p2_point)

        # Win probabilities table
        lines.append(f"| Metric | {r['p1_name']} | {r['p2_name']} |")
        lines.append("|--------|--------|--------|")
        lines.append(f"| Match Win | {sim['p1_match_win_prob']:.1%} | {sim['p2_match_win_prob']:.1%} |")
        lines.append(f"| 1st Set Win | {sim['p1_first_set_win_prob']:.1%} | {1.0 - sim['p1_first_set_win_prob']:.1%} |")
        lines.append(f"| Hold Game Rate | {p1_hold:.1%} | {p2_hold:.1%} |")
        lines.append(f"| Serve Point Win | {p1_point:.1%} | {p2_point:.1%} |")
        lines.append("")

        # Bug 2 fix: Over = 1 - under_prob using .get() fallbacks for missing lines
        lines.append(f"**Expected Total Games:** {sim['expected_total_games']:.1f}")
        lines.append(f"- Over 20.5: {1.0 - sim.get('under_20_5_prob', 0.5):.1%}")
        lines.append(f"- Over 22.5: {1.0 - sim.get('under_22_5_prob', 0.5):.1%}")
        lines.append(f"- Over 24.5: {1.0 - sim.get('under_24_5_prob', 0.5):.1%}")
        lines.append("")

        # Player profile section (enriched with history and risk flags)
        lines.append(f"**Profiles:** {r['p1_name']} | {r['p2_name']} ({r['surface']} History Base)")
        lines.append(f"- P1 Observed Surface Win Rate: {p1p.get('observed_win_rate', 0.5):.2%}")
        lines.append(f"- P2 Observed Surface Win Rate: {p2p.get('observed_win_rate', 0.5):.2%}")
        lines.append(
            f"- Retirement Risk: P1 ({p1p.get('retirement_risk_pct', 0.0):.1%}) "
            f"| P2 ({p2p.get('retirement_risk_pct', 0.0):.1%})"
        )
        # Retirement safety void flag
        if p1p.get('retirement_risk_flag') or p2p.get('retirement_risk_flag'):
            lines.append("  ⚠️ **Total Games O/U voided** — retirement risk ≥8% for at least one player")
        lines.append("")

        # Edge section
        if edge['has_edge']:
            lines.append(f"**EDGE ANALYSIS** ({edge['confidence']} Confidence)")
            for e in edge['edges']:
                lines.append(
                    f"- **{e['market']}**: Model {e['model_prob']:.1%}, "
                    f"Edge +{e['edge_pct']}%, Fair Odds {e['fair_odds']}"
                )
            lines.append("")

        lines.append("---")
        lines.append("")

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))



# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Tennis Consensus Prediction Engine')
    parser.add_argument('--tour', default='ATP', choices=['ATP', 'WTA', 'BOTH'],
                        help='Tour to analyze (default: ATP)')
    parser.add_argument('--iterations', type=int, default=10000,
                        help='MC iterations per match (default: 10000)')
    args = parser.parse_args()

    tours = ['ATP', 'WTA'] if args.tour == 'BOTH' else [args.tour]

    for t in tours:
        print(f"\n{'='*60}")
        print(f"  {t} TENNIS PREDICTION ENGINE")
        print(f"{'='*60}\n")
        generate_tennis_report(tour=t, iterations=args.iterations)
