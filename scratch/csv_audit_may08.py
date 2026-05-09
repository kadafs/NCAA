import csv, json

CSV_FILE = "data/confidence_reports/confidence_2026-05-08_no_playoffs.csv"
JSON_FILE = "data/basketball/universal_predictions_2026-05-08.json"
BUFFER = 5

# Load JSON actual scores
preds = {}
data = json.load(open(JSON_FILE, encoding="utf-8"))
for p in data.get("predictions", []):
    key = (p.get("home_team", "").strip(), p.get("away_team", "").strip())
    preds[key] = p

tier_order = ["[ELITE]", "[HIGH]", "[SOLID]", "[MODERATE]", "[LOW]", "[AVOID]"]
tier_stats = {}
tier_bias_stats = {}
total_graded = 0

with open(CSV_FILE, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        band = row.get("band", "").strip()
        home = row.get("home_team", "").strip()
        away = row.get("away_team", "").strip()

        model_total_csv = row.get("model_total", "")
        if not model_total_csv:
            continue
        model_total = float(model_total_csv)
        avg_bias = float(row.get("avg_bias", 0) or 0)

        p = preds.get((home, away))
        if not p:
            continue

        h_s = p.get("actual_home_score")
        a_s = p.get("actual_away_score")
        if h_s is None or a_s is None:
            continue

        actual_total = h_s + a_s
        error = actual_total - model_total
        total_graded += 1

        if band not in tier_stats:
            tier_stats[band] = {"games": 0, "hits": 0, "errors": []}
            tier_bias_stats[band] = {b: {"games": 0, "hits": 0, "errors": []} for b in ["Positive", "Neutral", "Negative"]}

        tier_stats[band]["games"] += 1
        tier_stats[band]["errors"].append(error)
        if actual_total >= (model_total - BUFFER):
            tier_stats[band]["hits"] += 1

        b_grp = "Neutral"
        if avg_bias > 1.0:
            b_grp = "Positive"
        elif avg_bias < -1.0:
            b_grp = "Negative"

        tier_bias_stats[band][b_grp]["games"] += 1
        tier_bias_stats[band][b_grp]["errors"].append(error)
        if actual_total >= (model_total - BUFFER):
            tier_bias_stats[band][b_grp]["hits"] += 1

print()
print("=" * 100)
print("  CSV AUDIT — confidence_2026-05-08_no_playoffs.csv | Buffer: -5pts | No Playoffs")
print("=" * 100)
print("[SECTION 1: CONFIDENCE TIER PERFORMANCE]")
print(f"{'Tier':<18} | {'Games':>5} | {'Avg Error':>12} | {'Hit Rate':>18}")
print("-" * 62)
for t in tier_order:
    mk = next((k for k in tier_stats if t in k), None)
    if not mk:
        continue
    s = tier_stats[mk]
    avg_e = sum(s["errors"]) / s["games"]
    rate = (s["hits"] / s["games"]) * 100
    print(f"{mk:<18} | {s['games']:>5} | {avg_e:>+12.2f} | {s['hits']:>6}/{s['games']:<3} ({rate:>5.1f}%)")

print()
print("[SECTION 2: HISTORICAL BIAS PERFORMANCE BY TIER]")
print(f"{'Tier / Bias Group':<20} | {'Games':>5} | {'Avg Error':>12} | {'Hit Rate':>18}")
print("-" * 64)
for t in tier_order:
    mk = next((k for k in tier_bias_stats if t in k), None)
    if not mk:
        continue
    print(mk)
    for b in ["Positive", "Neutral", "Negative"]:
        s = tier_bias_stats[mk][b]
        if s["games"] == 0:
            continue
        avg_e = sum(s["errors"]) / s["games"]
        rate = (s["hits"] / s["games"]) * 100
        print(f"  {b:<18} | {s['games']:>5} | {avg_e:>+12.2f} | {s['hits']:>6}/{s['games']:<3} ({rate:>5.1f}%)")

print()
print(f"  TOTAL GRADED (CSV): {total_graded}")
print("=" * 100)
