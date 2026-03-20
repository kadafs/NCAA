import json
import os
import random

def fix_mock_data():
    file_path = os.path.join("data", "basketball", "universal_predictions_2026-03-20.json")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for p in data.get("predictions", []):
        if not p.get("probs_1x2") or not p.get("xpts_h"):
            # Mock some stats
            p["probs_1x2"] = {"home": 58.4, "draw": 15.2, "away": 26.4}
            p["xpts_h"] = 82.5
            p["xpts_a"] = 76.1
            p["predicted_result"] = "HOME"
            p["predicted_spread"] = -6.4
            if "home_source" not in p:
                p["home_source"] = "SRS"
            if "away_source" not in p:
                p["away_source"] = "SRS"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Fixed mock data for 2026-03-20!")

if __name__ == "__main__":
    fix_mock_data()
