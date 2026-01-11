import requests

# This is a conceptual example of how to use the local NCAA API for predictions.
# You can run this with Bun or Node.js (requires 'requests' or 'node-fetch').

API_BASE = "http://localhost:3000"

def get_team_efficiency(sport, division, team_name):
    """
    Fetches team rankings to get a sense of efficiency.
    Stat ID 28 is Scoring Defense, Stat ID 29 is Scoring Offense for Football.
    Note: These IDs change per sport.
    """
    # Fetch Scoring Offense
    offense_res = requests.get(f"{API_BASE}/stats/{sport}/{division}/current/team/29").json()
    # Fetch Scoring Defense
    defense_res = requests.get(f"{API_BASE}/stats/{sport}/{division}/current/team/28").json()
    
    offense = next((t for t in offense_res['data'] if t['Team'].lower() == team_name.lower()), None)
    defense = next((t for t in defense_res['data'] if t['Team'].lower() == team_name.lower()), None)
    
    return {
        "ppg": float(offense['Avg']) if offense else 0,
        "opp_ppg": float(defense['Avg']) if defense else 0
    }

def predict_matchup(sport, division, team_a, team_b):
    print(f"Predicting Matchup: {team_a} vs {team_b}...")
    
    stats_a = get_team_efficiency(sport, division, team_a)
    stats_b = get_team_efficiency(sport, division, team_b)
    
    # Simple prediction formula: 
    # Projected Score A = (Team A Offense + Team B Defense Allowed) / 2
    proj_a = (stats_a['ppg'] + stats_b['opp_ppg']) / 2
    proj_b = (stats_b['ppg'] + stats_a['opp_ppg']) / 2
    
    print(f"\nResults:")
    print(f"{team_a} Projected Score: {proj_a:.1f}")
    print(f"{team_b} Projected Score: {proj_b:.1f}")
    
    if proj_a > proj_b:
        print(f"Winner: {team_a} by {proj_a - proj_b:.1f} points")
    else:
        print(f"Winner: {team_b} by {proj_b - proj_a:.1f} points")

if __name__ == "__main__":
    # Example for FBS Football
    # predict_matchup("football", "fbs", "Michigan", "Washington")
    print("Script ready. Start the API server with 'bun run dev' first.")
