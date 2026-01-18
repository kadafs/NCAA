# NCAA PPG+PED Hybrid Totals v1.2 CLI Runner
import argparse
import json
import os
from datetime import datetime
import zoneinfo

from .populate import get_daily_input_sheet, load_json, INJURY_FILE
from .engine import TotalsEngine

def main():
    parser = argparse.ArgumentParser(description="NCAA PPG+PED Hybrid Totals v1.2")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--trace", action="store_true", help="Show full logic audit trace")
    args = parser.parse_args()

    # 1. Initialize
    engine = TotalsEngine(mode=args.mode)
    daily_sheet = get_daily_input_sheet()
    injuries = load_json(INJURY_FILE) if args.mode == "full" else {}

    # 2. Results Collection
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print("\n" + "="*80)
    print(f"NCAA PPG+PED HYBRID TOTALS v1.2 | {args.mode.upper()} MODE | {now.strftime('%Y-%m-%d')}")
    print("="*80)

    results = []
    
    if not daily_sheet:
        print("No matchups found for today or data sources missing.")
        return

    for game in daily_sheet:
        # For Full Mode, we need injury notes for BOTH teams
        game_injuries = []
        if args.mode == "full":
            game_injuries.extend(injuries.get(game['team'], []))
            game_injuries.extend(injuries.get(game['opponent'], []))
        
        prediction = engine.calculate_total(game, game_injuries)
        
        # Display Row
        m = f"{game['team']} vs {game['opponent']}"
        p = prediction
        status = f"[{p['mode']}] {p['decision']}"
        lean_str = f"{p['lean']} {p['final_model_total']}"
        
        print(f"{m:40} | Market: {p['market_total']:5.1f} | Model: {p['final_model_total']:5.1f} | Edge: {p['edge']:+5.2f} | {status:12} | {lean_str}")
        
        if args.trace:
            for line in p['trace']:
                print(f"   > {line}")
            print("-" * 80)
            
        results.append({
            "timestamp": now.isoformat(),
            "matchup": m,
            **prediction
        })

    # 3. Persistence (Unified Daily Log)
    log_file = "data/v1_2_results_log.json"
    historical = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f: historical = json.load(f)
        except: pass
        
    historical.extend(results)
    with open(log_file, "w") as f:
        json.dump(historical, f, indent=2)

    print(f"\nSaved {len(results)} results to {log_file}")

if __name__ == "__main__":
    main()
