#!/usr/bin/env python3
"""
Model Comparison Tool
Runs both full-season and conference-only models side-by-side for D1 and D2.
"""

import sys
import os
import json
import subprocess
from datetime import datetime
import zoneinfo

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

def run_command(cmd, description):
    """Run a command and capture output."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed")
        print(f"Error output: {e.stderr}")
        return None

def load_predictions(filepath):
    """Load predictions from JSON file."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)

def compare_predictions(full_season, conf_only, model_name):
    """Compare two sets of predictions."""
    print(f"\n{'█'*80}")
    print(f" {model_name} MODEL COMPARISON")
    print(f"{'█'*80}\n")
    
    if not full_season or not conf_only:
        print("⚠ Missing prediction data for comparison")
        return
    
    # Create matchup lookup for conference-only
    conf_lookup = {p['matchup']: p for p in conf_only}
    
    # Compare each matchup
    comparisons = []
    
    for fs_pred in full_season:
        matchup = fs_pred['matchup']
        co_pred = conf_lookup.get(matchup)
        
        if not co_pred:
            continue
        
        # Extract key metrics
        fs_total = fs_pred.get('model_total', 0)
        co_total = co_pred.get('model_total', 0)
        market = fs_pred.get('market_total', 0)
        
        fs_edge = fs_pred.get('edge', 0)
        co_edge = co_pred.get('edge', 0)
        
        fs_decision = fs_pred.get('decision', 'N/A')
        co_decision = co_pred.get('decision', 'N/A')
        
        # Calculate difference
        total_diff = co_total - fs_total
        
        # Determine which model is more confident
        fs_abs_edge = abs(fs_edge) if fs_edge else 0
        co_abs_edge = abs(co_edge) if co_edge else 0
        
        more_confident = "Conf-Only" if co_abs_edge > fs_abs_edge else "Full-Season" if fs_abs_edge > co_abs_edge else "Equal"
        
        # Display comparison
        print(f"{'─'*80}")
        print(f"Matchup: {matchup}")
        print(f"{'─'*80}")
        print(f"{'Model':<15} | {'Total':>6} | {'Edge':>6} | {'Decision':<12} | {'Confidence':>10}")
        print(f"{'─'*80}")
        print(f"{'Full Season':<15} | {fs_total:>6.1f} | {fs_edge:>+6.2f} | {fs_decision:<12} | {fs_pred.get('confidence', 'N/A'):>10}")
        print(f"{'Conf-Only':<15} | {co_total:>6.1f} | {co_edge:>+6.2f} | {co_decision:<12} | {co_pred.get('confidence', 'N/A'):>10}")
        print(f"{'Market':<15} | {market:>6.1f} |")
        print(f"{'─'*80}")
        print(f"Difference (Conf - Full): {total_diff:+.1f} points")
        print(f"More Confident Model: {more_confident}")
        print()
        
        # Store comparison
        comparisons.append({
            "matchup": matchup,
            "full_season": {
                "total": fs_total,
                "edge": fs_edge,
                "decision": fs_decision,
                "confidence": fs_pred.get('confidence', 'N/A')
            },
            "conf_only": {
                "total": co_total,
                "edge": co_edge,
                "decision": co_decision,
                "confidence": co_pred.get('confidence', 'N/A')
            },
            "market": market,
            "difference": total_diff,
            "more_confident": more_confident
        })
    
    return comparisons

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compare Full-Season vs Conference-Only Models")
    parser.add_argument("--division", choices=["d1", "d2", "both"], default="both", help="Division to compare")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S ET")
    
    print(f"\n{'█'*80}")
    print(f" MODEL COMPARISON TOOL")
    print(f" Timestamp: {timestamp}")
    print(f" Mode: {args.mode.upper()}")
    print(f"{'█'*80}")
    
    all_comparisons = {}
    
    # D1 Comparison
    if args.division in ["d1", "both"]:
        print(f"\n{'='*80}")
        print("RUNNING D1 MODELS")
        print(f"{'='*80}")
        
        # Run full-season D1 model
        d1_full_cmd = ["python", "run_universal.py", "--league", "ncaa", "--mode", args.mode]
        if args.date:
            d1_full_cmd.extend(["--date", args.date])
        
        run_command(d1_full_cmd, "D1 Full-Season Model")
        
        # Run conference-only D1 model
        d1_conf_cmd = ["python", "ncaa/predict_d1_conf.py", "--mode", args.mode]
        if args.date:
            d1_conf_cmd.extend(["--date", args.date])
        
        run_command(d1_conf_cmd, "D1 Conference-Only Model")
        
        # Load and compare predictions
        # Note: Need to determine where run_universal saves D1 predictions
        # For now, we'll use the conference-only output
        d1_conf_preds = load_predictions("data/d1_conf_predictions.json")
        
        # TODO: Load full-season D1 predictions from appropriate location
        print("\n⚠ Note: Full-season D1 prediction loading needs to be implemented")
        print("   Conference-only predictions saved to: data/d1_conf_predictions.json")
    
    # D2 Comparison
    if args.division in ["d2", "both"]:
        print(f"\n{'='*80}")
        print("RUNNING D2 MODELS")
        print(f"{'='*80}")
        
        # Run full-season D2 model
        d2_full_cmd = ["python", "ncaa/predict_d2_hybrid.py", "--division", "d2"]
        run_command(d2_full_cmd, "D2 Full-Season Model")
        
        # Run conference-only D2 model
        d2_conf_cmd = ["python", "ncaa/predict_d2_conf.py", "--division", "d2"]
        run_command(d2_conf_cmd, "D2 Conference-Only Model")
        
        # Load predictions
        d2_full_preds = []  # TODO: Load from D2 full-season output
        d2_conf_preds = load_predictions("data/d2_conf_predictions.json")
        
        print("\n⚠ Note: Full-season D2 prediction loading needs to be implemented")
        print("   Conference-only predictions saved to: data/d2_conf_predictions.json")
    
    # Save comparison results
    comparison_output = {
        "timestamp": timestamp,
        "mode": args.mode,
        "divisions": args.division,
        "comparisons": all_comparisons
    }
    
    output_file = os.path.join(ROOT_DIR, "data", "model_comparison.json")
    with open(output_file, "w") as f:
        json.dump(comparison_output, f, indent=2)
    
    print(f"\n{'█'*80}")
    print(f" COMPARISON COMPLETE")
    print(f" Results saved to: {output_file}")
    print(f"{'█'*80}\n")

if __name__ == "__main__":
    main()
