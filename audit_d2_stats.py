import json

# Check D2 stats availability
with open("data/consolidated_stats_d2.json", "r") as f:
    d2_stats = json.load(f)

sample_team = list(d2_stats.keys())[0]
sample_stats = d2_stats[sample_team]

print("=" * 80)
print("D2 STATS AVAILABILITY AUDIT")
print("=" * 80)
print(f"\nSample Team: {sample_team}")
print(f"Total D2 Teams: {len(d2_stats)}")
print(f"\nAvailable Stats ({len(sample_stats)} fields):")
print("-" * 80)

# Required stats for D2 Hybrid Model
required_stats = {
    "PPG": "Scoring Offense (Points Per Game)",
    "OPP PPG": "Scoring Defense (Opponent Points Per Game)",
    "FGA": "Field Goal Attempts",
    "FTA": "Free Throw Attempts",
    "TO": "Turnovers",
    "REB": "Total Rebounds (for OR estimation)",
    "OPP REB": "Opponent Rebounds (for OR estimation)"
}

print("\nREQUIRED STATS FOR D2 HYBRID MODEL:")
print("-" * 80)
for stat, description in required_stats.items():
    available = "[YES]" if stat in sample_stats else "[NO]"
    value = sample_stats.get(stat, "N/A")
    print(f"{stat:15} | {available:10} | {description:40} | Value: {value}")

print("\n" + "=" * 80)
print("ADDITIONAL STATS AVAILABLE:")
print("=" * 80)
for key, value in sample_stats.items():
    if key not in required_stats:
        print(f"{key:15} | {value}")

print("\n" + "=" * 80)
print("POSSESSION CALCULATION CHECK:")
print("=" * 80)
print("Formula: Possessions = FGA - OR + TO + (0.44 × FTA)")
print(f"  FGA: {sample_stats.get('FGA', 'N/A')}")
print(f"  TO: {sample_stats.get('TO', 'N/A')}")
print(f"  FTA: {sample_stats.get('FTA', 'N/A')}")
print(f"  OR: Need to calculate from REB and OPP REB")
print(f"  Note: OR (Offensive Rebounds) not directly available")
print(f"  Workaround: Use league average OR or skip pace adjustment")
