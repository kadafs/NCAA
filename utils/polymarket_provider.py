import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from utils.mapping import BASKETBALL_ALIASES, NBA_TRICODES, clean_team_name

class PolymarketProvider:
    """
    Fetches and normalizes prediction market data from Polymarket's Gamma API.
    """
    GAMMA_API = "https://gamma-api.polymarket.com/events"
    
    def __init__(self):
        self.session = requests.Session()
        
        # Robust Retry Strategy (v1.6.5)
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json"
        })
    
    def get_markets(self, league="nba"):
        """
        Fetches active markets for the given league (nba/cbb).
        Returns a dictionary keyed by standardized Matchup ID.
        """
        slug = "cbb" if league.lower() == "ncaa" else "nba"
        
        params = {
            "closed": "false",
            "tag_slug": slug,
            "limit": 100, # Fetch enough to cover daily slate
            "order": "volume24hr",
            "ascending": "false"
        }
        
        try:
            res = self.session.get(self.GAMMA_API, params=params, timeout=5)
            res.raise_for_status()
            data = res.json()
            events = data if isinstance(data, list) else data.get('data', [])
            
            market_map = {}
            
            for event in events:
                title = event.get('title', '')
                
                # Normalize " vs. " to " vs "
                title_clean = title.replace(" vs. ", " vs ")
                
                # Filter for Game Matchups (Must contain 'vs')
                if " vs " not in title_clean:
                    continue
                    
                # Parse Teams from Title "Team A vs Team B"
                try:
                    parts = title_clean.split(" vs ")
                    teamA_raw = parts[0].strip()
                    # Remove potential extra text from Team B (e.g., "Team B - Feb 6")
                    teamB_raw = parts[1].split(" - ")[0].strip() 
                    
                    # Normalize
                    teamA = self._normalize_team(teamA_raw, league)
                    teamB = self._normalize_team(teamB_raw, league)
                    
                    if not teamA or not teamB:
                        continue
                        
                    # Find relevant markets (Winner/Moneyline)
                    for m in event.get('markets', []):
                        q = m.get('question', '')
                        outcomes = json.loads(m.get('outcomes', '[]'))
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        
                        if len(outcomes) != 2 or len(prices) != 2:
                            continue
                            
                        # Identify Market Type - Focus on Game Totals (O/U)
                        # Strict Filter: Exclude Quarter/Half markets and player props
                        is_period = any(x in q for x in ["1H", "2H", "Q1", "Q2", "Q3", "Q4", "First Half", "Second Half", "Quarter"])
                        is_player_prop = any(x in q for x in ["Points O/U", "Rebounds O/U", "Assists O/U", "Steals O/U", "Blocks O/U"])
                        
                        # Market is a Game Total if:
                        # 1. Contains "O/U" in the question
                        # 2. Has exactly 2 outcomes: ["Over", "Under"]
                        # 3. NOT a period market (1H, Q1, etc.)
                        # 4. NOT a player prop
                        is_game_total = (
                            "O/U" in q and 
                            outcomes == ["Over", "Under"] and 
                            not is_period and 
                            not is_player_prop
                        )
                        
                        if is_game_total:
                            # Extract the total from the question (e.g., "Warriors vs. Lakers: O/U 221.5" -> 221.5)
                            try:
                                total_str = q.split("O/U")[-1].strip()
                                total_value = float(total_str)
                            except:
                                continue  # Skip if we can't parse the total
                            # Outcomes are usually ["Team A", "Team B"] or ["Yes", "No"] (rare for games)
                            # Polymarket usually does ["Team A", "Team B"] for sports? 
                            # Checking inspection: Outcomes: ["Yes", "No"] for "Will X win?"
                            
                            # Simply map the event ID
                            matchup_id = f"{teamA}-{teamB}"
                            matchup_id_rev = f"{teamB}-{teamA}"
                            
                            market_data = {
                                "id": m.get('id'),
                                "title": m.get('question'),
                                "total": total_value,  # The O/U line (e.g., 221.5)
                                "outcomes": outcomes,  # ["Over", "Under"]
                                "prices": prices,  # [over_prob, under_prob]
                                "volume": m.get('volume24hr', 0),
                                "url": f"https://polymarket.com/event/{event.get('slug')}"
                            }
                            
                            market_map[matchup_id] = market_data
                            market_map[matchup_id_rev] = market_data
                            
                except Exception as e:
                    continue
                    
            return market_map

        except Exception as e:
            print(f"Polymarket Fetch Error: {e}")
            return {}

    def _normalize_team(self, name, league):
        """Uses existing mapping utilities."""
        # Clean common Polymarket prefixes/suffixes
        clean = name.replace("The ", "").strip().lower()
        
        # Try direct alias match
        if clean in BASKETBALL_ALIASES:
            return BASKETBALL_ALIASES[clean]
            
        # Try specific league tricodes
        if league == "nba":
            for tri, full in NBA_TRICODES.items():
                if full == clean or tri == clean:
                    return full
                    
        return clean_team_name(clean)
