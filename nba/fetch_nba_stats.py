import json
import os
import time
from nba_api.stats.endpoints import leaguedashteamstats

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "nba_stats.json")

def fetch_nba_complete_stats():
    print("Fetching NBA Complete Stats (Team, Advanced, Opponent) from official API...")
    
    try:
        # 1. Fetch Base Stats (PerGame)
        base_stats = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Base',
            per_mode_detailed='PerGame',
            season='2025-26',
            season_type_all_star='Regular Season'
        ).get_dict()

        # 2. Fetch Advanced Stats
        advanced_stats = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Advanced',
            season='2025-26',
            season_type_all_star='Regular Season'
        ).get_dict()

        # 3. Fetch Opponent Stats (What they allow)
        opponent_stats = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Opponent',
            per_mode_detailed='PerGame',
            season='2025-26',
            season_type_all_star='Regular Season'
        ).get_dict()

        # Extract headers and rows
        h_base = base_stats['resultSets'][0]['headers']
        r_base = base_stats['resultSets'][0]['rowSet']

        h_adv = advanced_stats['resultSets'][0]['headers']
        r_adv = advanced_stats['resultSets'][0]['rowSet']
        
        h_opp = opponent_stats['resultSets'][0]['headers']
        r_opp = opponent_stats['resultSets'][0]['rowSet']

        processed_data = {}

        # Merge by Team Name
        for i, row in enumerate(r_adv):
            row_dict_adv = dict(zip(h_adv, row))
            team_name = row_dict_adv['TEAM_NAME']
            
            # Find base row
            row_dict_base = {}
            for rb in r_base:
                if rb[h_base.index('TEAM_NAME')] == team_name:
                    row_dict_base = dict(zip(h_base, rb))
                    break

            # Find opponent row
            row_dict_opp = {}
            for ro in r_opp:
                if ro[h_opp.index('TEAM_NAME')] == team_name:
                    row_dict_opp = dict(zip(h_opp, ro))
                    break

            # Four Factors calculation
            fga = row_dict_base.get('FGA', 1)
            fta = row_dict_base.get('FTA', 0)
            ftr = fta / fga if fga > 0 else 0

            processed_data[team_name] = {
                "pts": row_dict_base.get('PTS', 115.0),
                "fg3a": row_dict_base.get('FG3A', 35.0),
                "adj_off": row_dict_adv['OFF_RATING'],
                "adj_def": row_dict_adv['DEF_RATING'],
                "adj_t": row_dict_adv['PACE'],
                "four_factors": {
                    "efg": row_dict_adv.get('EFG_PCT', 0) * 100,
                    "tov": row_dict_adv.get('TM_TOV_PCT', 0) * 100,
                    "orb": row_dict_adv.get('OREB_PCT', 0) * 100,
                    "ftr": ftr * 100
                },
                "allowed": {
                    "pts": row_dict_opp.get('OPP_PTS', 115.0),
                    "ast": row_dict_opp.get('OPP_AST', 25.0),
                    "reb": row_dict_opp.get('OPP_REB', 44.0),
                    "fg3a": row_dict_opp.get('OPP_FG3A', 35.0)
                },
                "conf": "NBA"
            }

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)
            
        print(f"Successfully saved complete stats for {len(processed_data)} NBA teams to {OUTPUT_FILE}")

    except Exception as e:
        print(f"Error fetching NBA stats: {e}")

if __name__ == "__main__":
    fetch_nba_complete_stats()
