"""
audit_league_projections.py
============================
Compares each league's model projections against its _avg_total
to identify systematic bias (leagues where the model consistently
over- or under-shoots the league average).

Usage:
    python audit_league_projections.py
    python audit_league_projections.py --threshold 10    # Only show >10pt gaps
    python audit_league_projections.py --date 2026-03-25 # Specific date
"""

import json, os, sys, argparse
from collections import defaultdict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Audit league projection bias")
    parser.add_argument("--date", help="Date to audit (default: latest)")
    parser.add_argument("--threshold", type=float, default=5.0,
                        help="Min absolute gap to flag (default: 5.0)")
    args = parser.parse_args()

    # Find prediction file
    pred_dir = "data/basketball"
    if args.date:
        pred_file = os.path.join(pred_dir, f"universal_predictions_{args.date}.json")
    else:
        files = sorted([f for f in os.listdir(pred_dir) if f.startswith("universal_predictions_")])
        if not files:
            print("No prediction files found.")
            return
        pred_file = os.path.join(pred_dir, files[-1])

    with open(pred_file, encoding="utf-8") as f:
        data = json.load(f)

    preds = data.get("predictions", [])
    print(f"\n{'='*80}")
    print(f"  LEAGUE PROJECTION AUDIT | {data.get('date', '?')} | {len(preds)} predictions")
    print(f"{'='*80}\n")

    # Load configs for _avg_total
    config_cache = {}
    for fn in os.listdir("configs/leagues"):
        if not fn.endswith(".json"):
            continue
        lid = fn.replace(".json", "")
        with open(f"configs/leagues/{fn}", encoding="utf-8") as f:
            config_cache[lid] = json.load(f)

    # Group predictions by league
    league_data = defaultdict(list)
    for p in preds:
        lid = str(p.get("league_id", "?"))
        model = p.get("model_total", 0)
        league_name = p.get("league", "?")
        away = p.get("away", "?")
        home = p.get("home", "?")
        if model:
            league_data[lid].append({
                "model": float(model),
                "name": league_name,
                "matchup": f"{away} @ {home}",
            })

    # Compute gaps
    results = []
    for lid, games in league_data.items():
        cfg = config_cache.get(lid, {})
        avg_total = cfg.get("_avg_total")
        if not avg_total:
            continue

        model_avg = sum(g["model"] for g in games) / len(games)
        gap = model_avg - avg_total
        pct_gap = (gap / avg_total) * 100

        results.append({
            "lid": lid,
            "name": games[0]["name"],
            "n_games": len(games),
            "league_avg": avg_total,
            "model_avg": model_avg,
            "gap": gap,
            "pct_gap": pct_gap,
            "games": games,
        })

    # Sort by absolute gap
    results.sort(key=lambda x: abs(x["gap"]), reverse=True)

    # Print summary
    flagged = [r for r in results if abs(r["gap"]) >= args.threshold]
    clean = [r for r in results if abs(r["gap"]) < args.threshold]

    if flagged:
        print(f"  FLAGGED ({len(flagged)} leagues with |gap| >= {args.threshold}pt):\n")
        print(f"  {'League':<35} {'Games':>5} {'Lg Avg':>7} {'Model':>7} {'Gap':>7} {'%':>6}")
        print(f"  {'-'*68}")
        for r in flagged:
            marker = "HIGH" if r["gap"] > 0 else " LOW"
            print(f"  {r['name']:<35} {r['n_games']:>5} {r['league_avg']:>7.1f} {r['model_avg']:>7.1f} {r['gap']:>+7.1f} {r['pct_gap']:>+5.1f}% {marker}")

            # Show individual games for flagged leagues
            for g in r["games"]:
                game_gap = g["model"] - r["league_avg"]
                print(f"      {g['matchup']:<45} model={g['model']:.1f}  gap={game_gap:+.1f}")
        print()

    print(f"  CLEAN ({len(clean)} leagues within +/-{args.threshold}pt of league average)")
    print()

    # Overall health metric
    all_gaps = [abs(r["gap"]) for r in results]
    if all_gaps:
        mean_gap = sum(all_gaps) / len(all_gaps)
        max_gap = max(all_gaps)
        print(f"  HEALTH: Mean |gap|={mean_gap:.1f}pt  Max |gap|={max_gap:.1f}pt  Leagues={len(results)}")
        if mean_gap < 5:
            print(f"  STATUS: HEALTHY")
        elif mean_gap < 10:
            print(f"  STATUS: ACCEPTABLE (some leagues may need recalibration)")
        else:
            print(f"  STATUS: WARNING (significant systematic bias detected)")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
