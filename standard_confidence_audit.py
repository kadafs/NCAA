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

def run_audit(dates, buffer=10, halftime=False, no_playoffs=False, league_filter=None, exclude_filter=None, league_id_filter=None):
    print(f"\n{'='*110}")
    print(f"  BASKETBALL CONFIDENCE AUDIT REPORT (Source: JSON Predictions)")
    
    header_mode = "HALF-TIME" if halftime else "FULL-TIME"
    filters = []
    if no_playoffs: filters.append("No Playoffs")
    if league_filter: filters.append(f"League: {league_filter}")
    if league_id_filter: filters.append(f"League ID: {league_id_filter}")
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
    # tier -> total_range -> { games, hits, errors }
    tier_range_stats = {}
    # tier -> spread_range -> { games, hits, errors }
    tier_spread_stats = {}

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
                                "avg_bias": row.get("avg_bias"),
                                "spread": row.get("spread")
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
                        lid = str(p.get("league_id") if p.get("league_id") is not None else "").strip()
                        lname = str(p.get("league") if p.get("league") is not None else "").lower()
                        lf = str(league_filter).strip().lower()
                        if lf != lid and lf not in lname:
                            continue
                            
                    # 2.1 League ID Filter
                    if league_id_filter:
                        lid = str(p.get("league_id") if p.get("league_id") is not None else "").strip()
                        lf_id = str(league_id_filter).strip()
                        if lf_id != lid:
                            continue
                            
                    # 2.5 Exclude Filter
                    if exclude_filter:
                        lname = str(p.get("league", "")).lower()
                        if str(exclude_filter).lower() in lname:
                            continue
                            
                    # 3. Playoff Filter
                    stage = str(p.get("stage") or "").lower()
                    lname = str(p.get("league") or "").lower()
                    
                    is_playoff = "playoff" in stage or "play-off" in stage or "postseason" in stage
                    
                    # Heuristic: If stage is empty but league is known to be in playoffs (Taiwan ID 403)
                    if not stage and p.get("league_id") == 403:
                        is_playoff = True
                        
                    if no_playoffs and is_playoff:
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
                    
                    # Prefer dated CSV spread
                    spread_str = csv_data.get("spread")
                    if spread_str:
                        spread_val = abs(float(spread_str))
                    else:
                        x_h = p.get("xpts_h")
                        x_a = p.get("xpts_a")
                        if x_h is not None and x_a is not None:
                            spread_val = abs(float(x_h) - float(x_a))
                        else:
                            spread_val = 0.0
                    
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
                        tier_range_stats[band] = {r: {"games": 0, "hits": 0, "errors": []} for r in ["< 130", "130-139.5", "140-149.5", "150-159.5", "160-169.5", "170-179.5", ">= 180"]}
                        tier_spread_stats[band] = {s: {"games": 0, "hits": 0, "errors": []} for s in ["0-5", "5-10", "10-15", "15-20", "20+"]}
                    
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
                        
                    # Model Total Range Tracking
                    total_grp = "Unknown"
                    if model_total < 130: total_grp = "< 130"
                    elif model_total < 140: total_grp = "130-139.5"
                    elif model_total < 150: total_grp = "140-149.5"
                    elif model_total < 160: total_grp = "150-159.5"
                    elif model_total < 170: total_grp = "160-169.5"
                    elif model_total < 180: total_grp = "170-179.5"
                    else: total_grp = ">= 180"
                    
                    
                    tier_range_stats[band][total_grp]["games"] += 1
                    tier_range_stats[band][total_grp]["errors"].append(error)
                    if actual_score >= (target_score - buffer):
                        tier_range_stats[band][total_grp]["hits"] += 1
                        
                    # Spread Range Tracking
                    spread_grp = "20+"
                    if spread_val < 5: spread_grp = "0-5"
                    elif spread_val < 10: spread_grp = "5-10"
                    elif spread_val < 15: spread_grp = "10-15"
                    elif spread_val < 20: spread_grp = "15-20"
                    
                    tier_spread_stats[band][spread_grp]["games"] += 1
                    tier_spread_stats[band][spread_grp]["errors"].append(error)
                    if actual_score >= (target_score - buffer):
                        tier_spread_stats[band][spread_grp]["hits"] += 1
                        
                        
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

    # Print Summary 3: Model Total Ranges by Tier
    print(f"\n[SECTION 3: HISTORICAL PERFORMANCE BY TIER AND TOTAL RANGE]")
    print(f"{'Tier / Total Range':<20} | {'Games':>5} | {'Avg Bias Error':>15} | {'Hit Rate':>18}")
    print("-" * 70)
    range_order = ["< 130", "130-139.5", "140-149.5", "150-159.5", "160-169.5", "170-179.5", ">= 180"]
    for t in tier_order:
        matched_key = next((k for k in tier_range_stats.keys() if t in k), None)
        if not matched_key: continue
        
        # Check if tier has any games in any range
        if sum(tier_range_stats[matched_key][r]["games"] for r in range_order) == 0: continue
        
        print(f"{matched_key}")
        for r in range_order:
            s = tier_range_stats[matched_key][r]
            if s["games"] == 0: continue
            avg_err = sum(s["errors"]) / s["games"]
            rate = (s["hits"] / s["games"]) * 100
            print(f"  {r:<18} | {s['games']:>5} | {avg_err:>+15.2f} | {s['hits']:>6}/{s['games']:<3} ({rate:>5.1f}%)")
            
    # Print Summary 4: Spread Ranges by Tier
    print(f"\n[SECTION 4: HISTORICAL PERFORMANCE BY TIER AND XPTS SPREAD]")
    print(f"{'Tier / Spread Range':<20} | {'Games':>5} | {'Avg Bias Error':>15} | {'Hit Rate':>18}")
    print("-" * 70)
    spread_order = ["0-5", "5-10", "10-15", "15-20", "20+"]
    for t in tier_order:
        matched_key = next((k for k in tier_spread_stats.keys() if t in k), None)
        if not matched_key: continue
        
        if sum(tier_spread_stats[matched_key][s]["games"] for s in spread_order) == 0: continue
        
        print(f"{matched_key}")
        for spr in spread_order:
            s = tier_spread_stats[matched_key][spr]
            if s["games"] == 0: continue
            avg_err = sum(s["errors"]) / s["games"]
            rate = (s["hits"] / s["games"]) * 100
            print(f"  {spr:<18} | {s['games']:>5} | {avg_err:>+15.2f} | {s['hits']:>6}/{s['games']:<3} ({rate:>5.1f}%)")

    print(f"\n{'='*110}")
    print(f"  TOTAL GRADED GAMES: {total_graded}")
    print(f"  Note: Bias Error = [Actual - Target]")
    print(f"{'='*110}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3, help="Number of recent days to audit")
    parser.add_argument("--buffer", type=int, default=0, help="Point buffer to evaluate (default: 0)")
    parser.add_argument("--halftime", action="store_true", help="Audit halftime performance instead of full time")
    parser.add_argument("--no_playoffs", action="store_true", help="Exclude playoff games from the audit")
    parser.add_argument("--league", type=str, default=None, help="Filter by league ID or league name substring")
    parser.add_argument("--league-id", "--league_id", "-l", type=str, default=None, help="Filter by exact league ID")
    parser.add_argument("--exclude", type=str, default=None, help="Exclude leagues matching this name substring")
    args = parser.parse_args()
    
    import datetime
    # Start from 0 (today) to include today's already-finished/graded games
    dates = [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, args.days)]
    run_audit(dates, args.buffer, args.halftime, args.no_playoffs, args.league, args.exclude, args.league_id)
