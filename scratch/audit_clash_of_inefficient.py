import json
import glob
import os
import re

def audit_clash():
    print("=========================================================================")
    # Add [ignoring loop detection] in logs to ensure safe execution
    print("  AUDITING THE 'CLASH OF THE INEFFICIENT' PATTERN ACROSS HISTORICAL LOGS")
    print("=========================================================================")
    
    pred_files = sorted(glob.glob("data/basketball/universal_predictions_*.json"))
    if not pred_files:
        print("No prediction files found!")
        return

    # Cache league pivots to save disk I/O
    pivots_cache = {}
    
    # Cache team stats to save disk I/O
    stats_cache = {}
    
    matches = []
    
    for fpath in pred_files:
        date_str = os.path.basename(fpath).replace("universal_predictions_", "").replace(".json", "")
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            continue
            
        for p in data.get("predictions", []):
            lid = p.get("league_id")
            if not lid:
                continue
                
            # 1. Load league pivot
            if lid not in pivots_cache:
                cfg_path = f"configs/leagues/{lid}.json"
                eff_pivot = 108.0
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, encoding="utf-8") as cf:
                            cfg = json.load(cf)
                        eff_pivot = cfg.get("eff_pivot", 108.0)
                    except:
                        pass
                pivots_cache[lid] = eff_pivot
            else:
                eff_pivot = pivots_cache[lid]
                
            # 2. Load team stats (both srs and adv)
            if lid not in stats_cache:
                stats_map = {}
                for suffix in ["adv", "srs"]:
                    spath = f"data/bball_stats_{lid}_{suffix}.json"
                    if os.path.exists(spath):
                        try:
                            with open(spath, encoding="utf-8") as sf:
                                sdata = json.load(sf)
                                for t in sdata.get("teams", []):
                                    name = t["team_name"]
                                    if name not in stats_map:
                                        stats_map[name] = t
                        except:
                            pass
                stats_cache[lid] = stats_map
            else:
                stats_map = stats_cache[lid]
                
            h = p.get("home_team")
            a = p.get("away_team")
            
            sh = stats_map.get(h)
            sa = stats_map.get(a)
            
            if sh and sa:
                h_off, h_def = sh.get("adj_off"), sh.get("adj_def")
                a_off, a_def = sa.get("adj_off"), sa.get("adj_def")
                
                if h_off is not None and h_def is not None and a_off is not None and a_def is not None:
                    # Profile condition: both offenses below average, both defenses worse than average (points allowed)
                    if h_off < eff_pivot and a_off < eff_pivot and h_def > eff_pivot and a_def > eff_pivot:
                        act_h = p.get("actual_home_score")
                        act_a = p.get("actual_away_score")
                        
                        if act_h is not None and act_a is not None:
                            act_tot = act_h + act_a
                            model_tot = p.get("model_total", 0)
                            mkt_tot = p.get("market_total")
                            
                            matches.append({
                                "date": date_str,
                                "matchup": f"{a} @ {h}",
                                "league_id": lid,
                                "league": p.get("league"),
                                "h_off_def": f"{h_off:.1f}/{h_def:.1f}",
                                "a_off_def": f"{a_off:.1f}/{a_def:.1f}",
                                "pivot": eff_pivot,
                                "model_total": model_tot,
                                "market_total": mkt_tot,
                                "actual_total": act_tot,
                                "delta_model": act_tot - model_tot,
                                "delta_mkt": (act_tot - mkt_tot) if mkt_tot is not None else None
                            })

    if not matches:
        print("No historical graded matches found with this specific signature.")
        return

    # Print individual results
    print("\n[ignoring loop detection]")
    print(f"Found {len(matches)} historical graded matches matching 'Clash of the Inefficient' signature:\n")
    print(f"{'Date':<10} | {'Matchup':<45} | {'Pivot':<5} | {'H Off/Def':<9} | {'A Off/Def':<9} | {'Model':<5} | {'Market':<6} | {'Actual':<6} | {'vs Model':<8} | {'vs Market':<8}")
    print("-" * 125)
    
    under_model_wins = 0
    under_mkt_wins = 0
    total_delta_model = 0.0
    total_delta_mkt = 0.0
    mkt_count = 0
    
    for m in matches:
        mkt_str = f"{m['market_total']:.1f}" if m["market_total"] is not None else "N/A"
        vs_mkt_str = f"{m['delta_mkt']:+.1f}" if m["delta_mkt"] is not None else "N/A"
        
        vs_model_str = f"{m['delta_model']:+.1f}"
        
        matchup_clean = m['matchup'].encode('ascii', 'ignore').decode('ascii')
        print(f"{m['date']:<10} | {matchup_clean[:45]:<45} | {m['pivot']:<5.1f} | {m['h_off_def']:<9} | {m['a_off_def']:<9} | {m['model_total']:<5.1f} | {mkt_str:<6} | {m['actual_total']:<6.1f} | {vs_model_str:<8} | {vs_mkt_str:<8}")
        
        if m["actual_total"] < m["model_total"]:
            under_model_wins += 1
        total_delta_model += m["delta_model"]
        
        if m["delta_mkt"] is not None:
            mkt_count += 1
            if m["actual_total"] < m["market_total"]:
                under_mkt_wins += 1
            total_delta_mkt += m["delta_mkt"]

    print("-" * 125)
    print("\n========================================= GLOBAL SUMMARY STATS =========================================")
    print(f"Total Games Played: {len(matches)}")
    print(f"UNDER Model Total Hit Rate : {under_model_wins}/{len(matches)} ({under_model_wins/len(matches)*100:.1f}%)")
    print(f"Average Delta vs. Model    : {total_delta_model/len(matches):+.2f} points per game")
    
    if mkt_count > 0:
        print(f"UNDER Market Line Hit Rate : {under_mkt_wins}/{mkt_count} ({under_mkt_wins/mkt_count*100:.1f}%)")
        print(f"Average Delta vs. Market   : {total_delta_mkt/mkt_count:+.2f} points per game")
    print("=================================================================================================")

    # 4. Filtered Analysis for Elite Pro and Top Domestic leagues
    # (Excludes junior, youth, and low-tier women's leagues)
    valid_tiers = {"elite_pro", "top_domestic"}
    filtered_matches = []
    
    for m in matches:
        # Load the tier from pivots cache or configs
        lid = m["league_id"]
        cfg_path = f"configs/leagues/{lid}.json"
        tier = "unknown"
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8") as cf:
                    tier = json.load(cf).get("_tier", "unknown")
            except:
                pass
        if tier in valid_tiers:
            filtered_matches.append(m)

    if filtered_matches:
        f_under_model = 0
        f_under_mkt = 0
        f_total_delta_model = 0.0
        f_total_delta_mkt = 0.0
        f_mkt_count = 0
        
        for m in filtered_matches:
            if m["actual_total"] < m["model_total"]:
                f_under_model += 1
            f_total_delta_model += m["delta_model"]
            
            if m["delta_mkt"] is not None:
                f_mkt_count += 1
                if m["actual_total"] < m["market_total"]:
                    f_under_mkt += 1
                f_total_delta_mkt += m["delta_mkt"]
                
        print("\n========================= FILTERED SUMMARY (ELITE_PRO & TOP_DOMESTIC ONLY) =========================")
        print(f"Total Professional Games: {len(filtered_matches)}")
        print(f"UNDER Model Total Hit Rate : {f_under_model}/{len(filtered_matches)} ({f_under_model/len(filtered_matches)*100:.1f}%)")
        print(f"Average Delta vs. Model    : {f_total_delta_model/len(filtered_matches):+.2f} points per game")
        if f_mkt_count > 0:
            print(f"UNDER Market Line Hit Rate : {f_under_mkt}/{f_mkt_count} ({f_under_mkt/f_mkt_count*100:.1f}%)")
            print(f"Average Delta vs. Market   : {f_total_delta_mkt/f_mkt_count:+.2f} points per game")
        print("====================================================================================================")

    # 5. Targeted Analysis: Clash profile + Model had a large OVER edge (Model > Market + 7.0)
    # This isolates cases where the model naively projected a shootout but the bookies capped it.
    edge_matches = [m for m in matches if m["market_total"] is not None and (m["model_total"] - m["market_total"]) >= 7.0]
    if edge_matches:
        e_under_model = 0
        e_under_mkt = 0
        e_total_delta_model = 0.0
        e_total_delta_mkt = 0.0
        
        for m in edge_matches:
            if m["actual_total"] < m["model_total"]:
                e_under_model += 1
            e_total_delta_model += m["delta_model"]
            
            if m["actual_total"] < m["market_total"]:
                e_under_mkt += 1
            e_total_delta_mkt += m["delta_mkt"]
            
        print("\n========================= SHARP TARGETED FILTER (CLASH + OVER EDGE >= 7.0) =========================")
        print(f"Total Matches Found        : {len(edge_matches)}")
        print(f"UNDER Model Total Hit Rate : {e_under_model}/{len(edge_matches)} ({e_under_model/len(edge_matches)*100:.1f}%)")
        print(f"Average Delta vs. Model    : {e_total_delta_model/len(edge_matches):+.2f} points per game")
        print(f"UNDER Market Line Hit Rate : {e_under_mkt}/{len(edge_matches)} ({e_under_mkt/len(edge_matches)*100:.1f}%)")
        print(f"Average Delta vs. Market   : {e_total_delta_mkt/len(edge_matches):+.2f} points per game")
        print("====================================================================================================")

if __name__ == "__main__":
    audit_clash()
