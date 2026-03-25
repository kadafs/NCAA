import json
import glob
import os

configs = glob.glob("configs/leagues/*.json")
reverted = 0

for fp in configs:
    with open(fp, encoding="utf-8") as f:
        c = json.load(f)
        
    if c.get("_source") == "tier-template":
        if c.get("_avg_total") is not None:
            c["_avg_total"] = None
            c["eff_pivot"] = 108.0
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(c, f, indent=2)
            reverted += 1

print(f"Reverted _avg_total to None for {reverted} tier-template configs.")
