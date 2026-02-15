#!/usr/bin/env python3
"""
Backtest Conference-Only Models
Validates conference-only models against historical results.
"""

import sys
import os
import json
from datetime import datetime
import statistics

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

def load_json(filepath):
    """Load JSON file."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)

def calculate_mae(predictions, actuals):
    """Calculate Mean Absolute Error."""
    if not predictions or not actuals:
        return None
    
    errors = [abs(p - a) for p, a in zip(predictions, actuals)]
    return statistics.mean(errors)

def calculate_hit_rate(predictions, actuals, markets):
    """Calculate OVER/UNDER hit rate."""
    if not predictions or not actuals or not markets:
        return None
    
    correct = 0
    total = 0
    
    for pred, actual, market in zip(predictions, actuals, markets):
        # Determine predicted side
        pred_side = "OVER" if pred > market else "UNDER"
        # Determine actual side
        actual_side = "OVER" if actual > market else "UNDER"
        
        if pred_side == actual_side:
            correct += 1
        total += 1
    
    return (correct / total * 100) if total > 0 else 0

def analyze_tier_performance(predictions, tier_key="confidence"):
    """Analyze performance by confidence tier."""
    tiers = {}
    
    for pred in predictions:
        tier = pred.get(tier_key, "N/A")
        if tier not in tiers:
            tiers[tier] = {
                "count": 0,
                "total_edge": 0,
                "predictions": []
            }
        
        tiers[tier]["count"] += 1
        tiers[tier]["total_edge"] += abs(pred.get("edge", 0))
        tiers[tier]["predictions"].append(pred)
    
    # Calculate averages
    for tier, data in tiers.items():
        if data["count"] > 0:
            data["avg_edge"] = data["total_edge"] / data["count"]
    
    return tiers

def backtest_model(model_predictions, historical_results):
    """
    Backtest a model against historical results.
    
    Args:
        model_predictions: List of predictions from model
        historical_results: List of actual game results
    
    Returns:
        Dictionary of performance metrics
    """
    
    # Create matchup lookup for historical results
    results_lookup = {}
    for result in historical_results:
        matchup = result.get('matchup')
        if matchup:
            results_lookup[matchup] = result
    
    # Collect metrics
    pred_totals = []
    actual_totals = []
    market_totals = []
    edges = []
    
    matched_count = 0
    
    for pred in model_predictions:
        matchup = pred.get('matchup')
        result = results_lookup.get(matchup)
        
        if not result:
            continue
        
        matched_count += 1
        
        pred_total = pred.get('model_total', 0)
        actual_total = result.get('actual_total')
        market_total = pred.get('market_total', 0)
        
        if actual_total and market_total:
            pred_totals.append(pred_total)
            actual_totals.append(actual_total)
            market_totals.append(market_total)
            edges.append(pred.get('edge', 0))
    
    # Calculate metrics
    metrics = {
        "total_predictions": len(model_predictions),
        "matched_games": matched_count,
        "mae": calculate_mae(pred_totals, actual_totals),
        "hit_rate": calculate_hit_rate(pred_totals, actual_totals, market_totals),
        "avg_edge": statistics.mean([abs(e) for e in edges]) if edges else 0,
        "tier_performance": analyze_tier_performance(model_predictions)
    }
    
    return metrics

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backtest Conference-Only Models")
    parser.add_argument("--division", choices=["d1", "d2", "both"], default="both", help="Division to backtest")
    parser.add_argument("--days", type=int, default=7, help="Number of days to backtest")
    args = parser.parse_args()
    
    print(f"\n{'█'*80}")
    print(f" CONFERENCE-ONLY MODEL BACKTEST")
    print(f" Division: {args.division.upper()}")
    print(f" Lookback: {args.days} days")
    print(f"{'█'*80}\n")
    
    # Load historical results
    results_log = load_json("data/v1_2_results_log.json")
    
    if not results_log:
        print("ERROR: No historical results found in data/v1_2_results_log.json")
        print("Please run your models for several days to build historical data.")
        return 1
    
    print(f"✓ Loaded {len(results_log)} historical predictions")
    
    # Load conference-only predictions
    d1_conf_preds = load_json("data/d1_conf_predictions.json")
    d2_conf_preds = load_json("data/d2_conf_predictions.json")
    
    # Backtest D1
    if args.division in ["d1", "both"] and d1_conf_preds:
        print(f"\n{'='*80}")
        print("D1 CONFERENCE-ONLY MODEL BACKTEST")
        print(f"{'='*80}\n")
        
        d1_metrics = backtest_model(d1_conf_preds, results_log)
        
        print(f"Total Predictions: {d1_metrics['total_predictions']}")
        print(f"Matched Games: {d1_metrics['matched_games']}")
        print(f"Mean Absolute Error: {d1_metrics['mae']:.2f}" if d1_metrics['mae'] else "MAE: N/A")
        print(f"Hit Rate: {d1_metrics['hit_rate']:.1f}%" if d1_metrics['hit_rate'] else "Hit Rate: N/A")
        print(f"Average Edge: {d1_metrics['avg_edge']:.2f}")
        
        print(f"\nTier Performance:")
        for tier, data in d1_metrics['tier_performance'].items():
            print(f"  {tier}: {data['count']} predictions, Avg Edge: {data.get('avg_edge', 0):.2f}")
    
    # Backtest D2
    if args.division in ["d2", "both"] and d2_conf_preds:
        print(f"\n{'='*80}")
        print("D2 CONFERENCE-ONLY MODEL BACKTEST")
        print(f"{'='*80}\n")
        
        d2_metrics = backtest_model(d2_conf_preds, results_log)
        
        print(f"Total Predictions: {d2_metrics['total_predictions']}")
        print(f"Matched Games: {d2_metrics['matched_games']}")
        print(f"Mean Absolute Error: {d2_metrics['mae']:.2f}" if d2_metrics['mae'] else "MAE: N/A")
        print(f"Hit Rate: {d2_metrics['hit_rate']:.1f}%" if d2_metrics['hit_rate'] else "Hit Rate: N/A")
        print(f"Average Edge: {d2_metrics['avg_edge']:.2f}")
        
        print(f"\nTier Performance:")
        for tier, data in d2_metrics['tier_performance'].items():
            print(f"  {tier}: {data['count']} predictions, Avg Edge: {data.get('avg_edge', 0):.2f}")
    
    # Save backtest results
    backtest_output = {
        "timestamp": datetime.now().isoformat(),
        "lookback_days": args.days,
        "d1_metrics": d1_metrics if args.division in ["d1", "both"] and d1_conf_preds else None,
        "d2_metrics": d2_metrics if args.division in ["d2", "both"] and d2_conf_preds else None
    }
    
    output_file = os.path.join(ROOT_DIR, "data", "conf_model_backtest.json")
    with open(output_file, "w") as f:
        json.dump(backtest_output, f, indent=2)
    
    print(f"\n{'█'*80}")
    print(f" BACKTEST COMPLETE")
    print(f" Results saved to: {output_file}")
    print(f"{'█'*80}\n")
    
    print("\n📊 NEXT STEPS:")
    print("1. Run conference-only models daily for 2-3 weeks")
    print("2. Compare MAE and hit rate vs full-season models")
    print("3. Analyze tier performance to validate edge calibration")
    print("4. Make decision on which model to use going forward\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
