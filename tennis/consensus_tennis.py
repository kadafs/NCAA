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

        # Detect edges
        edge_info = _detect_edge(sim)

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
    """Write the formatted markdown report."""
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
            emoji = "HIGH CONFIDENCE" if conf == 'High' else "Medium Edge"
            lines.append(f"- **{r['p1_name']} vs {r['p2_name']}:** {emoji}")
            for e in r['edges']['edges']:
                lines.append(f"  - {e['market']}: {e['model_prob']:.1%} (Fair: {e['fair_odds']})")
        lines.append("")
    lines.append("---")
    lines.append("")

    # Individual match details
    for r in results:
        sim = r['simulation']
        edge = r['edges']

        flag = " EDGE" if edge['has_edge'] else ""
        lines.append(f"### {r['p1_name']} vs {r['p2_name']}{flag}")
        lines.append(f"**{r['tournament']}** | Surface: {r['surface']} | "
                      f"Format: Best-of-{sim['sets_to_win'] * 2 - 1}")
        lines.append("")

        # Win probabilities
        lines.append(f"| Metric | {r['p1_name']} | {r['p2_name']} |")
        lines.append("|--------|--------|--------|")
        lines.append(f"| Match Win | {sim['p1_match_win_prob']:.1%} | {sim['p2_match_win_prob']:.1%} |")
        lines.append(f"| 1st Set Win | {sim['p1_first_set_win_prob']:.1%} | {sim['p2_first_set_win_prob']:.1%} |")
        lines.append(f"| Hold Rate | {sim['p1_hold_game_prob']:.1%} | {sim['p2_hold_game_prob']:.1%} |")
        lines.append(f"| Serve Point Win | {sim['p1_serve_point_prob']:.1%} | {sim['p2_serve_point_prob']:.1%} |")
        lines.append("")

        # Total games
        lines.append(f"**Expected Total Games:** {sim['expected_total_games']}")
        lines.append(f"- Over 21.5: {sim['over_21_5_prob']:.1%}")
        lines.append(f"- Over 22.5: {sim['over_22_5_prob']:.1%}")
        lines.append(f"- Over 23.5: {sim['over_23_5_prob']:.1%}")
        lines.append(f"- Over 24.5: {sim['over_24_5_prob']:.1%}")
        lines.append("")

        # Player profiles
        p1p = r['p1_profile']
        p2p = r['p2_profile']
        lines.append(f"**Profiles:** {r['p1_name']} ({p1p.get('matches_total', 0)} matches) | "
                      f"{r['p2_name']} ({p2p.get('matches_total', 0)} matches)")
        lines.append("")

        # Edge flags
        if edge['has_edge']:
            lines.append(f"**EDGE DETECTED** ({edge['confidence']} Confidence)")
            for e in edge['edges']:
                lines.append(f"- **{e['market']}**: Model {e['model_prob']:.1%}, "
                              f"Edge +{e['edge_pct']}%, Fair Odds {e['fair_odds']}")
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
