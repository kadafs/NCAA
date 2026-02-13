import json

# Analyze D2 rebound data to determine OR estimation formula
with open("data/consolidated_stats_d2.json", "r") as f:
    d2_stats = json.load(f)

print("=" * 80)
print("D2 OFFENSIVE REBOUND ESTIMATION ANALYSIS")
print("=" * 80)

# Collect rebound data
total_reb_list = []
opp_reb_list = []
or_estimates = []

for team, stats in d2_stats.items():
    if 'REB' in stats and 'OPP REB' in stats:
        total_reb = float(stats['REB'])
        opp_reb = float(stats['OPP REB'])
        
        # Team's offensive rebounds = Opponent's defensive rebounds
        # Total rebounds = Offensive rebounds + Defensive rebounds
        # Opponent's total rebounds = Their OR + Their DR
        # Our DR = Their OR
        # So: Our OR = Our Total REB - Their OR
        # But we don't have their OR directly...
        
        # Alternative: League average approach
        # OR typically ~30% of total rebounds in college basketball
        estimated_or = total_reb * 0.30
        
        total_reb_list.append(total_reb)
        opp_reb_list.append(opp_reb)
        or_estimates.append(estimated_or)

# Calculate league averages
avg_total_reb = sum(total_reb_list) / len(total_reb_list)
avg_opp_reb = sum(opp_reb_list) / len(opp_reb_list)
avg_or_estimate = sum(or_estimates) / len(or_estimates)

print(f"\nLeague Averages (D2):")
print(f"  Total Rebounds per team: {avg_total_reb:.1f}")
print(f"  Opponent Rebounds: {avg_opp_reb:.1f}")
print(f"  Estimated OR (30% method): {avg_or_estimate:.1f}")

# Alternative calculation
# Team's DR = Opponent's missed shots that team rebounded
# Team's OR = Team's missed shots that team rebounded
# Total REB = OR + DR
# If we assume roughly equal OR/DR split, OR ≈ 40% of total (since OR% is typically 25-35%)

print(f"\nAlternative estimates:")
print(f"  OR at 25% of total: {avg_total_reb * 0.25:.1f}")
print(f"  OR at 30% of total: {avg_total_reb * 0.30:.1f}")
print(f"  OR at 35% of total: {avg_total_reb * 0.35:.1f}")

# Check if we can derive OR from available stats
print(f"\n" + "=" * 80)
print("POSSESSION FORMULA COMPARISON")
print("=" * 80)

# Sample team
sample_team = list(d2_stats.keys())[0]
sample = d2_stats[sample_team]

print(f"\nSample Team: {sample_team}")
print(f"  Games: {sample.get('GM', 'N/A')}")
print(f"  FGA: {sample.get('FGA', 'N/A')}")
print(f"  FTA: {sample.get('FTA', 'N/A')}")
print(f"  TO: {sample.get('TO', 'N/A')}")
print(f"  Total REB: {sample.get('REB', 'N/A')}")

games = float(sample.get('GM', 1))
fga = float(sample.get('FGA', 0)) / games
fta = float(sample.get('FTA', 0)) / games
to = float(sample.get('TO', 0)) / games
total_reb = float(sample.get('REB', 0)) / games

# Test different OR estimates
or_25 = total_reb * 0.25
or_30 = total_reb * 0.30
or_35 = total_reb * 0.35

print(f"\nPer-game averages:")
print(f"  FGA/g: {fga:.1f}")
print(f"  FTA/g: {fta:.1f}")
print(f"  TO/g: {to:.1f}")
print(f"  Total REB/g: {total_reb:.1f}")

print(f"\nPossession estimates:")
print(f"  With OR=25%: {fga - or_25 + to + (0.44 * fta):.1f}")
print(f"  With OR=30%: {fga - or_30 + to + (0.44 * fta):.1f}")
print(f"  With OR=35%: {fga - or_35 + to + (0.44 * fta):.1f}")
print(f"  Without OR:  {fga + to + (0.44 * fta):.1f}")

print(f"\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("""
Based on college basketball norms:
- Offensive Rebound % typically ranges from 25-35%
- D2 teams average ~{:.1f} total rebounds per game
- Using 30% as middle estimate: ~{:.1f} OR per game

RECOMMENDED FORMULA:
  OR = Total_REB × 0.30

This is a reasonable middle-ground estimate for D2 basketball.
""".format(avg_total_reb / games if games > 0 else avg_total_reb, 
           (avg_total_reb / games * 0.30) if games > 0 else avg_or_estimate))
