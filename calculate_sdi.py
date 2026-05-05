"""
calculate_sdi.py
================
Star Dependency Index (SDI) Calculator

Reads all Proballers historical box score files and calculates per-team
scoring concentration metrics. A high SDI means the team relies heavily
on 1-2 players for most of its scoring — making them vulnerable to
injury, foul trouble, or off nights.

SDI Formula:
    SDI = avg((Top 2 scorers' pts) / Team total pts) × 100

Risk Tiers:
    GREEN  (< 40%) — Balanced roster, resilient
    AMBER  (40-54%) — Moderate dependency, monitor key players
    RED    (>= 55%) — High dependency, injury = collapse

Usage:
    python calculate_sdi.py
    python calculate_sdi.py --verbose
    python calculate_sdi.py --min_games 5
"""

import json
import os
import glob
import argparse
from collections import defaultdict
from datetime import datetime

DATA_DIR       = os.path.join(os.path.dirname(__file__), "data")
HISTORICAL_DIR = os.path.join(DATA_DIR, "historical")
OUTPUT_FILE    = os.path.join(DATA_DIR, "basketball", "team_sdi.json")
MIN_GAMES_DEFAULT = 3


def load_all_historical():
    """Load proballers and nbl1_official files and return list of games with player data."""
    p_files = glob.glob(os.path.join(HISTORICAL_DIR, "proballers_*.json"))
    n_files = glob.glob(os.path.join(HISTORICAL_DIR, "nbl1_official_*.json"))
    files = p_files + n_files
    all_games = []
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
            for game in data:
                home_p = game.get("stats", {}).get("home", {}).get("players", [])
                away_p = game.get("stats", {}).get("away", {}).get("players", [])
                if home_p or away_p:
                    all_games.append(game)
        except Exception:
            continue
    return all_games


def compute_sdi_for_side(players, team_total):
    """
    Given a list of player dicts {name, pts} and the team total,
    return (sdi_pct, top_scorer_pct, top_2_names).
    """
    if not players or not team_total or team_total == 0:
        return None, None, []

    sorted_players = sorted(players, key=lambda x: x.get("pts", 0), reverse=True)
    top2 = sorted_players[:2]
    top2_pts = sum(p.get("pts", 0) for p in top2)
    top1_pts = top2[0].get("pts", 0) if top2 else 0

    sdi_pct     = (top2_pts / team_total) * 100
    top1_pct    = (top1_pts / team_total) * 100
    top2_names  = [p.get("name", "?") for p in top2]

    return round(sdi_pct, 1), round(top1_pct, 1), top2_names


def main():
    parser = argparse.ArgumentParser(description="Calculate Star Dependency Index (SDI) per team.")
    parser.add_argument("--min_games", type=int, default=MIN_GAMES_DEFAULT,
                        help=f"Minimum games with player data to include a team (default: {MIN_GAMES_DEFAULT})")
    parser.add_argument("--verbose", action="store_true", help="Print per-team details during processing.")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  STAR DEPENDENCY INDEX (SDI) CALCULATOR")
    print("="*70)

    games = load_all_historical()
    print(f"  Loaded {len(games)} games with player data across all leagues.\n")

    # team_data[team_name] = { sdi_samples: [], top1_samples: [], top_scorers: Counter, games: int }
    team_data = defaultdict(lambda: {
        "sdi_samples":  [],
        "top1_samples": [],
        "top_scorers":  defaultdict(int),
        "game_count":   0
    })

    for game in games:
        home_team  = game.get("home_team", "")
        away_team  = game.get("away_team", "")
        
        # Ensure NBL1 women's teams don't get merged with men's teams of the exact same name
        comp = game.get("competition", "").lower()
        if "women" in comp or "(w)" in comp:
            if not home_team.endswith(" W"): home_team += " W"
            if not away_team.endswith(" W"): away_team += " W"
            
        home_score = game.get("home_score", 0) or 0
        away_score = game.get("away_score", 0) or 0

        home_players = game.get("stats", {}).get("home", {}).get("players", [])
        away_players = game.get("stats", {}).get("away", {}).get("players", [])

        for team, players, total in [
            (home_team, home_players, home_score),
            (away_team, away_players, away_score)
        ]:
            if not team or not players or total <= 0:
                continue

            sdi, top1, top2_names = compute_sdi_for_side(players, total)
            if sdi is None:
                continue

            team_data[team]["sdi_samples"].append(sdi)
            team_data[team]["top1_samples"].append(top1)
            team_data[team]["game_count"] += 1

            for name in top2_names:
                team_data[team]["top_scorers"][name] += 1

    # Compile results
    results = []
    skipped = 0

    for team_name, d in team_data.items():
        g = d["game_count"]
        if g < args.min_games:
            skipped += 1
            continue

        avg_sdi  = round(sum(d["sdi_samples"])  / g, 1)
        avg_top1 = round(sum(d["top1_samples"]) / g, 1)
        max_sdi  = round(max(d["sdi_samples"]),  1)
        min_sdi  = round(min(d["sdi_samples"]),  1)

        # Top recurring star players
        top_players = sorted(d["top_scorers"].items(), key=lambda x: x[1], reverse=True)
        top_players_list = [{"name": n, "times_top2": t} for n, t in top_players[:5]]

        # Risk tier
        if avg_sdi >= 55:
            risk = "RED"
            risk_label = "HIGH DEPENDENCY"
        elif avg_sdi >= 40:
            risk = "AMBER"
            risk_label = "MODERATE"
        else:
            risk = "GREEN"
            risk_label = "BALANCED"

        results.append({
            "team":          team_name,
            "games_tracked": g,
            "avg_sdi":       avg_sdi,
            "avg_top1_pct":  avg_top1,
            "max_sdi":       max_sdi,
            "min_sdi":       min_sdi,
            "risk":          risk,
            "risk_label":    risk_label,
            "top_players":   top_players_list,
        })

        if args.verbose:
            stars = ", ".join(f"{p['name']} ({p['times_top2']}g)" for p in top_players_list[:2])
            print(f"  [{risk}] {team_name:<35} SDI={avg_sdi:>5}% | Top1={avg_top1:>4}% | Games={g} | Stars: {stars}")

    # Sort by SDI descending (most dependent first)
    results.sort(key=lambda x: x["avg_sdi"], reverse=True)

    # Summary stats
    red_count   = sum(1 for r in results if r["risk"] == "RED")
    amber_count = sum(1 for r in results if r["risk"] == "AMBER")
    green_count = sum(1 for r in results if r["risk"] == "GREEN")

    output = {
        "generated_at":     datetime.now().isoformat(),
        "total_teams":      len(results),
        "skipped_teams":    skipped,
        "min_games_filter": args.min_games,
        "summary": {
            "red_high_dependency": red_count,
            "amber_moderate":      amber_count,
            "green_balanced":      green_count,
        },
        "teams": results
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Results: {len(results)} teams tracked ({skipped} skipped — fewer than {args.min_games} games)")
    print(f"  Risk breakdown: RED={red_count} | AMBER={amber_count} | GREEN={green_count}")
    print(f"\n  Output saved -> {OUTPUT_FILE}")

    # Print top 15 most star-dependent teams
    print(f"\n  TOP 15 MOST STAR-DEPENDENT TEAMS:")
    print(f"  {'Team':<35} {'SDI':>6} {'Top1':>5} {'Risk':<8} {'Key Players'}")
    print("  " + "-" * 90)
    for r in results[:15]:
        stars = ", ".join(p["name"] for p in r["top_players"][:2])
        print(f"  {r['team']:<35} {r['avg_sdi']:>5}% {r['avg_top1_pct']:>4}% {r['risk_label']:<12} {stars}")

    # Print bottom 10 most balanced teams
    print(f"\n  TOP 10 MOST BALANCED TEAMS (Lowest SDI):")
    print(f"  {'Team':<35} {'SDI':>6} {'Games':>6} {'Risk'}")
    print("  " + "-" * 60)
    for r in results[-10:][::-1]:
        print(f"  {r['team']:<35} {r['avg_sdi']:>5}% {r['games_tracked']:>6}   {r['risk_label']}")

    print()


if __name__ == "__main__":
    main()
