import json
import os
import csv
import argparse
from datetime import datetime

# ==============================================================================
# STANDARD BASKETBALL CONFIDENCE AUDIT ENGINE (Hybrid: CSV Band + JSON Scores)
# ==============================================================================
# Sourcing strategy:
#   BAND/TIER  → Dated CSV file (e.g. confidence_2026-05-08_no_playoffs.csv)
#                This is what was shown on the dashboard when the bet was placed.
#                Falls back to JSON band if no CSV exists for that date.
#   ACTUAL SCORES  → JSON predictions (graded actual_home_score / actual_away_score)
#   MODEL METRICS  → JSON predictions (model_total, bias_h, bias_a)
#
# This avoids the pipeline timing issue where run_basketball_daily.py can write
# stale confidence bands before generate_advanced_metrics.py completes.
# ==============================================================================

CONFIDENCE_DIR = "data/confidence_reports"
PREDICTIONS_DIR = "data/basketball"

def run_audit(dates, buffer=10, halftime=False, no_playoffs=False, league_filter=None, exclude_filter=None):
    print(f"\n{'='*110}")
    print(f"  BASKETBALL CONFIDENCE AUDIT REPORT (Source: JSON Predictions)")
    
    header_mode = "HALF-TIME" if halftime else "FULL-TIME"
    filters = []
    if no_playoffs: filters.append("No Playoffs")
    if league_filter: filters.append(f"League: {league_filter}")
    if exclude_filter: filters.append(f"Exclude: {exclude_filter}")
    filter_str = f" | Filters: {', '.join(filters)}" if filters else ""
    
    print(f"  MODE: {header_mode} | Buffer: -{buffer} pts | Window: {', '.join(dates)}{filter_str}")
    
    if halftime:
        print(f"  Target: Halftime Total >= (Raw Model Total / 2) - {buffer}")
    else:
        print(f"  Target: Final Total >= Raw Model Total - {buffer}")
    print(f"{'='*110}")

    # tier -> { games, hits, errors }
    tier_stats = {}
    # tier -> bias_group -> { games, hits, errors }
    tier_bias_stats = {}

    total_graded = 0

    for date in dates:
        path = os.path.join(PREDICTIONS_DIR, f"universal_predictions_{date}.json")
        if not os.path.exists(path):
            continue
        
        # --- Load CSV metrics for this date (prefer no_playoffs variant) ---
        csv_metrics = {}
        for csv_name in [f"confidence_{date}_no_playoffs.csv", f"confidence_{date}.csv"]:
            csv_path = os.path.join(CONFIDENCE_DIR, csv_name)
            if os.path.exists(csv_path):
                try:
                    with open(csv_path, encoding="utf-8") as cf:
                        for row in csv.DictReader(cf):
                            key = (row.get("home_team", "").strip(), row.get("away_team", "").strip())
                            csv_metrics[key] = {
                                "band": row.get("band", "").strip(),
                                "model_total": row.get("model_total"),
                                "avg_bias": row.get("avg_bias")
                            }
                except Exception:
                    pass
                break  # Use first match only
        
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                
            for p in data.get("predictions", []):
                try:
                    # 1. Verification: Must be graded
                    h_s, a_s = p.get("actual_home_score"), p.get("actual_away_score")
                    if h_s is None or a_s is None:
                        continue
                    
                    ht_total = p.get("halftime_total")
                    if halftime and ht_total is None:
                        continue # Skip if halftime mode but no halftime data
                    
                    # 2. League Filter
                    if league_filter:
                        lid = str(p.get("league_id", ""))
                        lname = str(p.get("league", "")).lower()
                        lf = str(league_filter).lower()
                        if lf != lid and lf not in lname:
                            continue
                            
                    # 2.5 Exclude Filter
                    if exclude_filter:
                        lname = str(p.get("league", "")).lower()
                        if str(exclude_filter).lower() in lname:
                            continue
                            
                    # 3. Skip Playoffs
                    if no_playoffs:
                        stage = p.get("stage", "")
                        if stage is None: stage = ""
                        stage = stage.lower()
                        playoff_keywords = ["final", "semi", "quarter", "playoff", "3rd place", "relegation"]
                        if any(k in stage for k in playoff_keywords):
                            continue

                    # 4. Extract Metrics — Prefer CSV (authoritative), fallback to JSON
                    home = p.get("home_team", "").strip()
                    away = p.get("away_team", "").strip()
                    
                    csv_data = csv_metrics.get((home, away), {})
                    
                    # Prefer dated CSV band (matches what was shown on dashboard)
                    band = csv_data.get("band")
                    if not band:
                        band = p.get("confidence_score_band") or p.get("band", "[UNKNOWN]")
                    
                    # Prefer dated CSV model total
                    model_total_str = csv_data.get("model_total")
                    if model_total_str:
                        model_total = float(model_total_str)
                    else:
                        model_total = p.get("model_total")
                        if model_total is None: continue
                        model_total = float(model_total)
                    
                    # Prefer dated CSV average bias
                    avg_bias_str = csv_data.get("avg_bias")
                    if avg_bias_str:
                        avg_bias_raw = float(avg_bias_str)
                    else:
                        bias_h = p.get("bias_h")
                        bias_a = p.get("bias_a")
                        bias_h = float(bias_h) if bias_h is not None else 0.0
                        bias_a = float(bias_a) if bias_a is not None else 0.0
                        avg_bias_raw = (bias_h + bias_a) / 2
                    
                    actual_total = h_s + a_s
                    
                    if halftime:
                        target_score = model_total / 2
                        actual_score = ht_total
                    else:
                        target_score = model_total
                        actual_score = actual_total
                        
                    error = actual_score - target_score
                    total_graded += 1
                    
                    # --- STATS COLLECTION ---
                    
                    # Tier Tracking
                    if band not in tier_stats:
                        tier_stats[band] = {"games": 0, "hits": 0, "errors": []}
                        tier_bias_stats[band] = {b: {"games": 0, "hits": 0, "errors": []} for b in ["Positive", "Neutral", "Negative"]}
                    
                    tier_stats[band]["games"] += 1
                    tier_stats[band]["errors"].append(error)
                    if actual_score >= (target_score - buffer):
                        tier_stats[band]["hits"] += 1
                        
                    # Bias Tracking by Tier
                    b_grp = "Neutral"
                    if avg_bias_raw > 1.0: b_grp = "Positive"
                    elif avg_bias_raw < -1.0: b_grp = "Negative"
                    
                    tier_bias_stats[band][b_grp]["games"] += 1
                    tier_bias_stats[band][b_grp]["errors"].append(error)
                    if actual_score >= (target_score - buffer):
                        tier_bias_stats[band][b_grp]["hits"] += 1
                        
                except Exception as inner_e:
                    # Skip individual malformed games but continue the file
                    continue
                    
        except Exception as e:
            print(f"Error processing {date} JSON: {e}")

    # Print Summary 1: Tiers
    print(f"\n[SECTION 1: CONFIDENCE TIER PERFORMANCE]")
    print(f"{'Tier':<18} | {'Games':>5} | {'Avg Bias Error':>15} | {'Hit Rate':>18}")
    print("-" * 68)
    # Sort tiers by confidence score (Elite first)
    tier_order = ["[ELITE]", "[HIGH]", "[SOLID]", "[MODERATE]", "[LOW]", "[AVOID]"]
    for t in tier_order:
        # Match by prefix since band labels might have padding/brackets
        matched_key = next((k for k in tier_stats.keys() if t in k), None)
        if not matched_key: continue
        
        s = tier_stats[matched_key]
        avg_err = sum(s["errors"]) / s["games"]
        rate = (s["hits"] / s["games"]) * 100
        print(f"{matched_key:<18} | {s['games']:>5} | {avg_err:>+15.2f} | {s['hits']:>6}/{s['games']:<3} ({rate:>5.1f}%)")

    # Print Summary 2: Bias by Tier
    print(f"\n[SECTION 2: HISTORICAL BIAS PERFORMANCE BY TIER]")
    print(f"{'Tier / Bias Group':<20} | {'Games':>5} | {'Avg Bias Error':>15} | {'Hit Rate':>18}")
    print("-" * 70)
    for t in tier_order:
        matched_key = next((k for k in tier_bias_stats.keys() if t in k), None)
        if not matched_key: continue
        
        print(f"{matched_key}")
        for b in ["Positive", "Neutral", "Negative"]:
            s = tier_bias_stats[matched_key][b]
            if s["games"] == 0: continue
            avg_err = sum(s["errors"]) / s["games"]
            rate = (s["hits"] / s["games"]) * 100
            print(f"  {b:<18} | {s['games']:>5} | {avg_err:>+15.2f} | {s['hits']:>6}/{s['games']:<3} ({rate:>5.1f}%)")

    print(f"\n{'='*110}")
    print(f"  TOTAL GRADED GAMES: {total_graded}")
    print(f"  Note: Bias Error = [Actual - Target]")
    print(f"{'='*110}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3, help="Number of recent days to audit")
    parser.add_argument("--buffer", type=int, default=10, help="Point buffer to evaluate (default: 10)")
    parser.add_argument("--halftime", action="store_true", help="Audit halftime performance instead of full time")
    parser.add_argument("--no_playoffs", action="store_true", help="Exclude playoff games from the audit")
    parser.add_argument("--league", type=str, default=None, help="Filter by league ID or league name substring")
    parser.add_argument("--exclude", type=str, default=None, help="Exclude leagues matching this name substring")
    args = parser.parse_args()
    
    import datetime
    dates = [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, args.days + 1)]
    run_audit(dates, args.buffer, args.halftime, args.no_playoffs, args.league, args.exclude)
