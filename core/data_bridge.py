# Universal DataBridge v1.4
import os
import json
import sys

# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES, NBA_TRICODES

class UniversalDataBridge:
    """
    Bridges raw data files into standardized engine inputs.
    """
    
    def __init__(self, league_name):
        self.league = league_name.upper()
        self.data_dir = "data"

    def _load_json(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path): return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_standardized_sheet(self):
        """Dispatches to league-specific population logic."""
        if self.league == "NBA":
            return self._pop_nba()
        elif self.league == "NCAA":
            return self._pop_ncaa()
        elif self.league == "EURO":
            return self._pop_euro()
        else:
            return []

    def _pop_nba(self):
        """NBA-specific population logic moved to core."""
        matchups = self._load_json("nba_matchups.json")
        all_stats = self._load_json("nba_stats.json")
        
        daily_sheet = []
        for m in matchups:
            teamA_name = find_team_in_dict(m['away'], all_stats, BASKETBALL_ALIASES)
            teamH_name = find_team_in_dict(m['home'], all_stats, BASKETBALL_ALIASES)
            
            if not teamA_name or not teamH_name: continue
            
            sA = all_stats[teamA_name]
            sH = all_stats[teamH_name]
            
            daily_sheet.append({
                "team": teamA_name,
                "opponent": teamH_name,
                "pace_adjustment": (sA['adj_t'] + sH['adj_t']) / 2,
                "efficiency_adjustment": (sA['adj_off'] + sH['adj_def'] + sH['adj_off'] + sA['adj_def']) / 4,
                "market_total": m.get('total', 230.5),
                "is_elite_offense": sA['adj_off'] > 120 or sH['adj_off'] > 120,
                "is_strong_defense": sA['adj_def'] < 110 or sH['adj_def'] < 110,
                "three_pa_total": sA.get('fg3a', 35) + sH.get('fg3a', 35),
                "statsA": {
                    "adj_off": sA['adj_off'],
                    "adj_def": sA['adj_def'],
                    "adj_t": sA['adj_t'],
                    "four_factors": sA.get('four_factors', {})
                },
                "statsH": {
                    "adj_off": sH['adj_off'],
                    "adj_def": sH['adj_def'],
                    "adj_t": sH['adj_t'],
                    "four_factors": sH.get('four_factors', {})
                }
            })
        return daily_sheet

    def _pop_ncaa(self):
        """NCAA-specific population logic moved to core."""
        bt_data = self._load_json("barttorvik_stats.json")
        score_data = self._load_json("consolidated_stats.json")
        
        # We need a way to fetch matchups (reusing the API call or a saved file)
        # For simplicity in the bridge, we'll look for a matchups file first
        matchups = self._load_json("ncaa_matchups.json")
        if not matchups:
            # Fallback to fetching today (simplified)
            from ncaa.v1_2.populate import fetch_matchups
            matchups = fetch_matchups()
            
        daily_sheet = []
        for m in matchups:
            teamA = find_team_in_dict(m['away'], bt_data, BASKETBALL_ALIASES)
            teamH = find_team_in_dict(m['home'], bt_data, BASKETBALL_ALIASES)
            
            if not teamA or not teamH: continue
            
            sA = bt_data[teamA]
            sH = bt_data[teamH]
            
            # Find PPG helper
            def get_ppg(name, stats):
                for entry in score_data.get('scoring_offense', []):
                    if entry['Team'] == name: return float(entry['PPG'])
                return (stats['adj_off'] * (stats['adj_t'] / 100))
                
            daily_sheet.append({
                "team": teamA,
                "opponent": teamH,
                "team_ppg": get_ppg(teamA, sA),
                "opp_ppg": get_ppg(teamH, sH),
                "pace_adjustment": (sA['adj_t'] + sH['adj_t']) / 2,
                "efficiency_adjustment": (sA['adj_off'] + sH['adj_def'] + sH['adj_off'] + sA['adj_def']) / 4,
                "market_total": m.get('total', 145.5),
                "is_elite_offense": sA['adj_off'] > 115 or sH['adj_off'] > 115,
                "is_strong_defense": sA['adj_def'] < 100 or sH['adj_def'] < 100,
                "conf": sA['conf'],
                "statsA": {
                    "adj_off": sA['adj_off'],
                    "adj_def": sA['adj_def'],
                    "adj_t": sA['adj_t'],
                    "four_factors": {
                        "efg": sA.get('efg', 0),
                        "tov": sA.get('to', 0),
                        "orb": sA.get('or', 0),
                        "ftr": sA.get('ftr', 0)
                    }
                },
                "statsH": {
                    "adj_off": sH['adj_off'],
                    "adj_def": sH['adj_def'],
                    "adj_t": sH['adj_t'],
                    "four_factors": {
                        "efg": sH.get('efg', 0),
                        "tov": sH.get('to', 0),
                        "orb": sH.get('or', 0),
                        "ftr": sH.get('ftr', 0)
                    }
                }
            })
        return daily_sheet

    def _pop_euro(self):
        """EuroLeague-specific population logic v1.9."""
        matchups = self._load_json("euro_matchups.json")
        all_stats = self._load_json("euro_stats.json")
        
        daily_sheet = []
        for m in matchups:
            teamA_name = find_team_in_dict(m['away'], all_stats)
            teamH_name = find_team_in_dict(m['home'], all_stats)
            
            if not teamA_name or not teamH_name: continue
            
            sA = all_stats[teamA_name]
            sH = all_stats[teamH_name]
            
            daily_sheet.append({
                "team": teamA_name,
                "opponent": teamH_name,
                "pace_adjustment": (sA.get('adj_t', 72.0) + sH.get('adj_t', 72.0)) / 2,
                "efficiency_adjustment": (
                    sA.get('adj_off', 110.0) + sH.get('adj_def', 110.0) +
                    sH.get('adj_off', 110.0) + sA.get('adj_def', 110.0)
                ) / 4,
                "market_total": m.get('total', 160.0),
                "is_elite_offense": sA.get('adj_off', 110.0) > 120 or sH.get('adj_off', 110.0) > 120,
                "is_strong_defense": sA.get('adj_def', 110.0) < 105 or sH.get('adj_def', 110.0) < 105,
                "three_pa_total": sA.get('fg3a', 25.0) + sH.get('fg3a', 25.0),
                "statsA": {
                    "adj_off": sA.get('adj_off', 110.0),
                    "adj_def": sA.get('adj_def', 110.0),
                    "adj_t": sA.get('adj_t', 72.0)
                },
                "statsH": {
                    "adj_off": sH.get('adj_off', 110.0),
                    "adj_def": sH.get('adj_def', 110.0),
                    "adj_t": sH.get('adj_t', 72.0)
                }
            })
        return daily_sheet
