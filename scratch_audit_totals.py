import json
import glob
import os

DATES = ["2026-04-12", "2026-04-13", "2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17"]

def get_tier(h_vol, a_vol):
    if h_vol is None or a_vol is None:
        return "Unknown/Unstable"
    if h_vol < 14.8 and a_vol < 14.8:
        return "Tier 1: Both Elite (Green < 14.8)"
    if h_vol <= 16.6 and a_vol <= 16.6:
        return "Tier 2: Both Stable (Blue <= 16.6)"
    return "Tier 3: Unstable (> 16.6)"

results = {
    "Tier 1: Both Elite (Green < 14.8)": {"count": 0, "pass_5": 0, "pass_10": 0},
    "Tier 2: Both Stable (Blue <= 16.6)": {"count": 0, "pass_5": 0, "pass_10": 0},
    "Tier 3: Unstable (> 16.6)": {"count": 0, "pass_5": 0, "pass_10": 0},
    "Unknown/Unstable": {"count": 0, "pass_5": 0, "pass_10": 0}
}

for d in DATES:
    file_path = f"data/basketball/universal_predictions_{d}.json"
    if not os.path.exists(file_path):
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for p in data.get("predictions", []):
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
        
        tier = get_tier(h_vol, a_vol)
        
        results[tier]["count"] += 1
        
        # Condition 1: Actual >= Model Total - 5
        if actual_total >= (model_total - 5):
            results[tier]["pass_5"] += 1
            
        # Condition 2: Actual >= Model Total - 10
        if actual_total >= (model_total - 10):
            results[tier]["pass_10"] += 1

print(f"Audit: Model Total vs Actual Score ({DATES[0]} to {DATES[-1]})\n")
print(f"{'Stability Tier':<35} | {'Games':<6} | {'Actual >= Model - 5':<22} | {'Actual >= Model - 10':<22}")
print("-" * 92)

for tier in ["Tier 1: Both Elite (Green < 14.8)", "Tier 2: Both Stable (Blue <= 16.6)", "Tier 3: Unstable (> 16.6)"]:
    r = results[tier]
    count = r["count"]
    if count == 0:
        continue
        
    p5 = r["pass_5"]
    p10 = r["pass_10"]
    
    p5_pct = (p5 / count) * 100
    p10_pct = (p10 / count) * 100
    
    p5_str = f"{p5}/{count} ({p5_pct:.1f}%)"
    p10_str = f"{p10}/{count} ({p10_pct:.1f}%)"
    
    print(f"{tier:<35} | {count:<6} | {p5_str:<22} | {p10_str:<22}")

# Print Total
total_c = sum(r["count"] for r in results.values())
total_p5 = sum(r["pass_5"] for r in results.values())
total_p10 = sum(r["pass_10"] for r in results.values())

if total_c > 0:
    print("-" * 92)
    p5_str = f"{total_p5}/{total_c} ({(total_p5/total_c)*100:.1f}%)"
    p10_str = f"{total_p10}/{total_c} ({(total_p10/total_c)*100:.1f}%)"
    print(f"{'TOTAL (All Games)':<35} | {total_c:<6} | {p5_str:<22} | {p10_str:<22}")
