"""
consensus_t20.py
================
Consensus prediction engine for T20 cricket matches.

Primary market: Powerplay (overs 1-6) total — structural analog to MLB F5.
Secondary market: 1st innings total, match winner.

Workflow:
  1. Fetch today's T20 schedule (CricketData.org)
  2. Build bowler/batter profiles (Cricsheet baseline + live delta)
  3. Run vectorized T20 MC simulation for each match
  4. Gatekeeper edge detection (Powerplay O/U primary)
  5. Output markdown report + JSON bridge for dashboard
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_cricket_stats import (
    get_point_in_time_bowler_profile,
    get_point_in_time_batter_profile,
    fetch_today_matches,
    fetch_today_playing_xi,
    POWERPLAY_BOWLER, DEATH_BOWLER, SPINNER,
    OPENER_BATTER, LEAGUE_BATTER_BASELINE, TAILENDER_BATTER,
)
from monte_carlo_t20 import run_t20_match_mc
from ground_factors import get_ground_factor, LEAGUE_AVG_SCORE

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPORT_DIR = os.path.join(_BASE_DIR, '..', 'data', 'cricket')
_EDGE_THRESHOLD = 0.05  # 5% minimum model edge to flag

os.makedirs(_REPORT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Lineup Builder
# ---------------------------------------------------------------------------

def _build_lineup(player_names: list, role: str = 'batting') -> list:
    """
    Build a batting or bowling lineup from player names.
    Falls back to position/role-based defaults for unknown players.
    """
    lineup = []
    for i, name in enumerate(player_names):
        if role == 'batting':
            pos = i + 1  # 1-indexed batting position
            profile = get_point_in_time_batter_profile(name, batting_position=pos)
            lineup.append(profile)
        else:
            # Assign bowler role based on position in bowling list
            profile = get_point_in_time_bowler_profile(name)
            lineup.append(profile)
    return lineup


def _generic_lineup(role: str = 'batting', n: int = 11) -> list:
    """Build a generic lineup using league average profiles."""
    if role == 'batting':
        return (
            [OPENER_BATTER.copy(), OPENER_BATTER.copy()] +
            [LEAGUE_BATTER_BASELINE.copy()] * 5 +
            [TAILENDER_BATTER.copy()] * (n - 7)
        )
    else:
        return (
            [POWERPLAY_BOWLER.copy()] * 2 +
            [SPINNER.copy()] * 2 +
            [DEATH_BOWLER.copy()]
        )


# ---------------------------------------------------------------------------
# Edge Detection (Gatekeeper)
# ---------------------------------------------------------------------------

def _detect_t20_edge(sim: dict) -> dict:
    """
    Detect betting edges from T20 simulation results.
    Primary: Powerplay (overs 1-6) combined total O/U
    Secondary: 1st innings total, match winner
    """
    edges = []

    # --- Powerplay total O/U (primary market) ---
    pp_expected = sim.get('expected_pp_combined', 90.0)

    for line in [85.0, 90.0, 95.0, 100.0]:
        over_key = f'pp_combined_over_{int(line)}_prob'
        under_key = f'pp_combined_under_{int(line)}_prob'
        over_p = sim.get(over_key, 0.50)
        under_p = sim.get(under_key, 0.50)

        if over_p >= 0.55 + _EDGE_THRESHOLD:
            edges.append({
                'market': f'Powerplay Total Over {line}',
                'edge_pct': round((over_p - 0.50) * 100, 1),
                'model_prob': over_p,
                'fair_odds': round(1.0 / over_p, 2),
                'priority': 'PRIMARY',
            })
        elif under_p >= 0.55 + _EDGE_THRESHOLD:
            edges.append({
                'market': f'Powerplay Total Under {line}',
                'edge_pct': round((under_p - 0.50) * 100, 1),
                'model_prob': under_p,
                'fair_odds': round(1.0 / under_p, 2),
                'priority': 'PRIMARY',
            })

    # --- 1st innings total (secondary) ---
    t1 = sim.get('team1_innings', {})
    for line in [155.0, 165.0, 175.0, 185.0]:
        key = f'over_{int(line)}_prob'
        if key in t1:
            op = t1[key]
            up = 1.0 - op
            if op >= 0.60:
                edges.append({
                    'market': f'1st Innings Over {line}',
                    'edge_pct': round((op - 0.50) * 100, 1),
                    'model_prob': op,
                    'fair_odds': round(1.0 / op, 2),
                    'priority': 'SECONDARY',
                })
            elif up >= 0.60:
                edges.append({
                    'market': f'1st Innings Under {line}',
                    'edge_pct': round((up - 0.50) * 100, 1),
                    'model_prob': up,
                    'fair_odds': round(1.0 / up, 2),
                    'priority': 'SECONDARY',
                })

    # --- Match winner ---
    t1_win = sim.get('team1_win_prob', 0.50)
    t2_win = sim.get('team2_win_prob', 0.50)
    if t1_win >= 0.62:
        edges.append({
            'market': 'Team 1 Match Winner',
            'edge_pct': round((t1_win - 0.50) * 100, 1),
            'model_prob': t1_win,
            'fair_odds': round(1.0 / t1_win, 2),
            'priority': 'SECONDARY',
        })
    elif t2_win >= 0.62:
        edges.append({
            'market': 'Team 2 Match Winner',
            'edge_pct': round((t2_win - 0.50) * 100, 1),
            'model_prob': t2_win,
            'fair_odds': round(1.0 / t2_win, 2),
            'priority': 'SECONDARY',
        })

    primary_edges = [e for e in edges if e['priority'] == 'PRIMARY']
    confidence = (
        'High' if any(e['edge_pct'] >= 10 for e in primary_edges)
        else ('Medium' if primary_edges else ('Low' if edges else 'None'))
    )

    return {
        'has_edge': len(edges) > 0,
        'has_primary_edge': len(primary_edges) > 0,
        'edges': edges,
        'confidence': confidence,
    }


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

def generate_t20_report(
    competition: str = 'The Hundred',
    iterations: int = 10000,
    output_dir: str = None,
) -> str:
    """
    Generate consensus T20 prediction report for today's matches.

    Parameters
    ----------
    competition : Tournament name (used for filtering schedule)
    iterations  : MC simulation iterations (default 10,000)
    output_dir  : output folder (default: data/cricket/)

    Returns
    -------
    str : path to generated report file
    """
    if output_dir is None:
        output_dir = _REPORT_DIR

    today_str = datetime.now().strftime('%Y-%m-%d')
    comp_slug = competition.lower().replace(' ', '_')
    report_path = os.path.join(output_dir, f'cricket_{comp_slug}_report_{today_str}.md')
    json_path = os.path.join(output_dir, f'cricket_{comp_slug}_predictions_{today_str}.json')

    # Step 1: Fetch schedule
    print(f"[Cricket] Fetching today's {competition} schedule...")
    matches = fetch_today_matches()
    matches = [m for m in matches if competition.lower() in m.get('series', '').lower()] or matches

    if not matches:
        print(f"[Cricket] No matches found. Generating demo report.")
        matches = [{'match_id': 'demo', 'name': 'Team A vs Team B', 'venue': 'Lord\'s', 'series': competition}]

    print(f"[Cricket] Analyzing {len(matches)} match(es)")

    results = []
    for match in matches:
        match_name = match.get('name', 'Unknown Match')
        venue = match.get('venue', 'Unknown Venue')
        match_id = match.get('match_id', match.get('id', ''))

        print(f"  Processing: {match_name} @ {venue}")

        # Fetch playing XIs
        squads = fetch_today_playing_xi(match_id) if match_id and match_id != 'demo' else {}

        team1_name = match.get('teamInfo', [{}])[0].get('name', 'Team 1') if match.get('teamInfo') else 'Team 1'
        team2_name = match.get('teamInfo', [{}])[1].get('name', 'Team 2') if match.get('teamInfo') else 'Team 2'

        t1_players = squads.get('team1', {}).get('players', [])
        t2_players = squads.get('team2', {}).get('players', [])

        # Build lineups (fall back to generics if no confirmed XI)
        if t1_players:
            t1_batting = _build_lineup([p.get('name', '') for p in t1_players[:11]], 'batting')
            t1_bowling = _build_lineup([p.get('name', '') for p in t1_players if p.get('role') in ('Bowler', 'All-Rounder')][:5], 'bowling')
        else:
            t1_batting = _generic_lineup('batting')
            t1_bowling = _generic_lineup('bowling')

        if t2_players:
            t2_batting = _build_lineup([p.get('name', '') for p in t2_players[:11]], 'batting')
            t2_bowling = _build_lineup([p.get('name', '') for p in t2_players if p.get('role') in ('Bowler', 'All-Rounder')][:5], 'bowling')
        else:
            t2_batting = _generic_lineup('batting')
            t2_bowling = _generic_lineup('bowling')

        # Pad bowling to exactly 5 bowlers
        while len(t1_bowling) < 5:
            t1_bowling.append(SPINNER.copy())
        while len(t2_bowling) < 5:
            t2_bowling.append(SPINNER.copy())

        # Run simulation
        sim = run_t20_match_mc(
            t1_batting, t2_batting,
            t1_bowling, t2_bowling,
            venue_name=venue,
            iterations=iterations,
        )

        # Edge detection
        edge = _detect_t20_edge(sim)

        results.append({
            'match_name': match_name,
            'team1': team1_name,
            'team2': team2_name,
            'venue': venue,
            'simulation': sim,
            'edges': edge,
            'confirmed_xi': bool(t1_players),
        })

    # Write report
    _write_t20_report(report_path, competition, today_str, results)

    # Write JSON
    json_out = []
    for r in results:
        sim = r['simulation']
        t1_inn = sim.get('team1_innings', {})
        json_out.append({
            'sport': 'cricket_t20',
            'competition': competition,
            'match': r['match_name'],
            'team1': r['team1'],
            'team2': r['team2'],
            'venue': r['venue'],
            'expected_pp_combined': sim.get('expected_pp_combined'),
            'expected_t1_runs': t1_inn.get('expected_total_runs'),
            'team1_win_prob': sim.get('team1_win_prob'),
            'has_primary_edge': r['edges']['has_primary_edge'],
            'edges': r['edges']['edges'],
        })

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_out, f, indent=2)

    print(f"\n[Cricket] Report: {report_path}")
    print(f"[Cricket] JSON:   {json_path}")
    return report_path


def _write_t20_report(path: str, competition: str, date_str: str, results: list):
    """Write formatted markdown report."""
    lines = []
    lines.append(f"# T20 Cricket Prediction Report — {competition}")
    lines.append(f"**Date:** {date_str}")
    lines.append(f"**Generated:** {datetime.now().strftime('%H:%M:%S')}")
    lines.append(f"**Matches Analyzed:** {len(results)}")
    lines.append("")

    priority = [r for r in results if r['edges']['has_primary_edge']]
    if priority:
        lines.append("## TOP PRIORITY — POWERPLAY EDGES")
        for r in priority:
            conf = r['edges']['confidence']
            lines.append(f"- **{r['match_name']}** ({r['venue']}) — {conf} Confidence")
            for e in [ed for ed in r['edges']['edges'] if ed['priority'] == 'PRIMARY']:
                lines.append(f"  - {e['market']}: {e['model_prob']:.1%} | Fair: {e['fair_odds']}")
        lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        sim = r['simulation']
        t1_inn = sim.get('team1_innings', {})
        t2_inn = sim.get('team2_innings', {})
        edge = r['edges']

        xi_status = "Confirmed XI" if r['confirmed_xi'] else "Generic Lineup"
        flag = " EDGE" if edge['has_edge'] else ""
        lines.append(f"### {r['match_name']}{flag}")
        lines.append(f"**Venue:** {r['venue']} (GF: {sim.get('ground_factor', 1.0):.2f}x) | {xi_status}")
        lines.append(f"**Dew Factor:** {'Yes' if sim.get('dew_present') else 'No'}")
        lines.append("")

        lines.append("| Metric | Team 1 | Team 2 |")
        lines.append("|--------|--------|--------|")
        lines.append(f"| Expected Innings Total | {t1_inn.get('expected_total_runs', 'N/A')} | {t2_inn.get('expected_total_runs', 'N/A')} |")
        lines.append(f"| Expected Powerplay | {t1_inn.get('expected_powerplay_runs', 'N/A')} | {t2_inn.get('expected_powerplay_runs', 'N/A')} |")
        lines.append(f"| Win Probability | {sim.get('team1_win_prob', 0):.1%} | {sim.get('team2_win_prob', 0):.1%} |")
        lines.append("")

        pp_comb = sim.get('expected_pp_combined', 0)
        lines.append(f"**Combined Powerplay (Overs 1-6):** {pp_comb:.1f} runs")
        for line_val in [85, 90, 95, 100]:
            op = sim.get(f'pp_combined_over_{line_val}_prob', 0)
            lines.append(f"  - Over {line_val}: {op:.1%} | Under {line_val}: {1-op:.1%}")
        lines.append("")

        if edge['has_edge']:
            lines.append(f"**EDGE DETECTED ({edge['confidence']} Confidence)**")
            for e in edge['edges']:
                pri_tag = " [PRIMARY]" if e['priority'] == 'PRIMARY' else ""
                lines.append(f"- **{e['market']}**{pri_tag}: {e['model_prob']:.1%} | +{e['edge_pct']}% | Fair: {e['fair_odds']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T20 Cricket Consensus Engine')
    parser.add_argument('--competition', default='The Hundred', help='Tournament name')
    parser.add_argument('--iterations', type=int, default=10000)
    args = parser.parse_args()
    generate_t20_report(competition=args.competition, iterations=args.iterations)
