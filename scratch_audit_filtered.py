import json
import glob
import os
import re

DATES = ["2026-04-17", "2026-04-18"]

# 1. Load leaderboard and build valid leagues set
valid_leagues = set()
try:
    with open("data/basketball/league_leaderboard.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        lb = data.get("leaderboard", [])
        for entry in lb:
            adv_data = entry.get("adv")
            srs_data = entry.get("srs")
            adv_games = adv_data.get("graded_totals", 0) if adv_data else 0
            srs_games = srs_data.get("graded_totals", 0) if srs_data else 0
            total_games = max(adv_games, srs_games)
            
            if total_games >= 10:
                lid = entry.get("league_id")
                if lid:
                    valid_leagues.add(str(lid))
except Exception as e:
    print(f"Error loading leaderboard: {e}")

print(f"Loaded {len(valid_leagues)} leagues with >= 10 matches played.")

def is_womens(league_name):
    if not league_name: return False
    l = league_name.lower()
    return "women" in l or "woman" in l or "ladies" in l or bool(re.search(r" w$", l))

def get_tier_both(h_vol, a_vol):
    if h_vol is None or a_vol is None:
        return "Unknown"
    if h_vol < 14.8 and a_vol < 14.8:
        return "Tier 1: BOTH Green (< 14.8)"
    if h_vol <= 16.6 and a_vol <= 16.6:
        return "Tier 2: BOTH Colored (Green/Blue or Blue/Blue)"
    return "Tier 3: At least one Unstable (> 16.6)"

def init_results():
    return {
        "Tier 1: BOTH Green (< 14.8)": {"count": 0, "pass_5": 0, "pass_10": 0, "win_delta_sum": 0, "loss_delta_sum": 0},
        "Tier 2: BOTH Colored (Green/Blue or Blue/Blue)": {"count": 0, "pass_5": 0, "pass_10": 0, "win_delta_sum": 0, "loss_delta_sum": 0},
        "Tier 3: At least one Unstable (> 16.6)": {"count": 0, "pass_5": 0, "pass_10": 0, "win_delta_sum": 0, "loss_delta_sum": 0},
    }

results = {
    "MEN": init_results(),
    "WOMEN": init_results()
}

filtered_out = 0

for d in DATES:
    file_path = f"data/basketball/universal_predictions_{d}.json"
    if not os.path.exists(file_path):
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for p in data.get("predictions", []):
        league_id = str(p.get("league_id"))
        if league_id not in valid_leagues:
            filtered_out += 1
            continue
            
        act_h = p.get("actual_home_score")
        act_a = p.get("actual_away_score")
        
        if act_h is None or act_a is None:
            continue
            
        actual_total = act_h + act_a
        model_total = p.get("model_total")
        
        if model_total is None or model_total == 0:
            continue
            
        h_vol = p.get("home_team_volatility")
        a_vol = p.get("away_team_volatility")
        
        tier = get_tier_both(h_vol, a_vol)
        if tier == "Unknown":
            continue
            
        league_name = p.get("league", "")
        gender = "WOMEN" if is_womens(league_name) else "MEN"
        
        results[gender][tier]["count"] += 1
        
        delta = actual_total - model_total
        
        if actual_total >= (model_total - 5):
            results[gender][tier]["pass_5"] += 1
            
        if actual_total >= (model_total - 10):
            results[gender][tier]["pass_10"] += 1
            results[gender][tier]["win_delta_sum"] += delta
        else:
            results[gender][tier]["loss_delta_sum"] += delta

def print_report(title, res):
    print(f"\n{title}")
    print(f"{'Stability Tier':<48} | {'Games':<6} | {'Actual >= Model - 10':<22} | {'Avg Delta (Wins)':<18} | {'Avg Delta (Losses)':<18}")
    print("-" * 125)

    for tier in ["Tier 1: BOTH Green (< 14.8)", "Tier 2: BOTH Colored (Green/Blue or Blue/Blue)", "Tier 3: At least one Unstable (> 16.6)"]:
        r = res[tier]
        count = r["count"]
        if count == 0:
            continue
            
        p10 = r["pass_10"]
        losses = count - p10
        p10_pct = (p10 / count) * 100
        p10_str = f"{p10}/{count} ({p10_pct:.1f}%)"
        
        avg_win = r["win_delta_sum"] / p10 if p10 > 0 else 0
        avg_loss = r["loss_delta_sum"] / losses if losses > 0 else 0
        
        print(f"{tier:<48} | {count:<6} | {p10_str:<22} | {avg_win:>+16.1f} | {avg_loss:>+16.1f}")

    total_c = sum(r["count"] for r in res.values())
    total_p10 = sum(r["pass_10"] for r in res.values())
    total_losses = total_c - total_p10
    total_win_delta = sum(r["win_delta_sum"] for r in res.values())
    total_loss_delta = sum(r["loss_delta_sum"] for r in res.values())

    if total_c > 0:
        print("-" * 125)
        p10_str = f"{total_p10}/{total_c} ({(total_p10/total_c)*100:.1f}%)"
        avg_win = total_win_delta / total_p10 if total_p10 > 0 else 0
        avg_loss = total_loss_delta / total_losses if total_losses > 0 else 0
        print(f"{'TOTAL':<48} | {total_c:<6} | {p10_str:<22} | {avg_win:>+16.1f} | {avg_loss:>+16.1f}")

print(f"\nFiltered out {filtered_out} predictions from leagues with < 10 graded games.")
print(f"Audit: Margins of Victory/Defeat vs Model (Filtered >= 10 games) (April 17 & 18)")
print_report("=== MEN'S BASKETBALL ===", results["MEN"])
print_report("=== WOMEN'S BASKETBALL ===", results["WOMEN"])
