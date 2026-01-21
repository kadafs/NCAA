import os
import json
import requests
from datetime import datetime

class SportradarProvider:
    """
    Sportradar Odds Comparison API Provider.
    Supports NBA, NCAA, EuroLeague, EuroCup, and ACB.
    """
    
    # Tournament/Competition IDs discovered in research
    TOURNAMENT_IDS = {
        "nba": "sr:tournament:132",
        "basketball_nba": "sr:tournament:132",
        "ncaa": "sr:tournament:338",
        "basketball_ncaa": "sr:tournament:338",
        "euroleague": "sr:tournament:137",
        "eurocup": "sr:tournament:231",
        "acb": "sr:tournament:264"
    }

    # API Base URLs
    BASE_URL_US = "https://api.sportradar.com/oddscomparison-usp1/en/us"
    BASE_URL_INTL = "https://api.sportradar.com/oddscomparison-rowt1/en/eu"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("SPORTRADAR_API_KEY")
        self.is_mock = not self.api_key or self.api_key == "YOUR_API_KEY_HERE"

    def _get_base_url(self, league_key):
        """Routes to US or International endpoints based on league."""
        if league_key in ["nba", "ncaa", "basketball_nba", "basketball_ncaa"]:
            return self.BASE_URL_US
        return self.BASE_URL_INTL

    def get_totals(self, league_key, date_obj=None):
        """
        Fetches or simulates totals for a given league and date.
        """
        if self.is_mock:
            return self._generate_mock_totals(league_key, date_obj)
        
        if date_obj is None:
            date_obj = datetime.now()
            
        date_str = date_obj.strftime("%Y-%m-%d")
        sport_id = "sr:sport:2" # Basketball
        base = self._get_base_url(league_key)
        
        # Endpoint: /sports/{sport_id}/{date}/schedule.json
        url = f"{base}/sports/{sport_id}/{date_str}/schedule.json"
        
        try:
            params = {"api_key": self.api_key}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Sportradar API Error: {response.status_code}")
                return self._generate_mock_totals(league_key, date_obj)
        except Exception as e:
            print(f"Sportradar Request Failed: {e}")
            return self._generate_mock_totals(league_key, date_obj)

    def _generate_mock_totals(self, league_key, date_obj):
        """
        Generates realistic mock data following Sportradar's JSON structure.
        """
        import random
        
        # Typical totals for leagues
        base_total = 230.5 if "nba" in league_key else (165.5 if "euro" in league_key else 145.5)
        
        mock_response = {
            "generated_at": datetime.now().isoformat(),
            "sport_events": []
        }
        
        # Add a few dummy events
        for i in range(1, 4):
            total = base_total + random.uniform(-10, 10)
            mock_response["sport_events"].append({
                "id": f"sr:sport_event:mock_{i}",
                "scheduled": (date_obj or datetime.now()).isoformat(),
                "competitors": [
                    {"id": f"sr:competitor:A{i}", "name": f"Team Away {i}", "qualifier": "away"},
                    {"id": f"sr:competitor:H{i}", "name": f"Team Home {i}", "qualifier": "home"}
                ],
                "markets": [
                    {
                        "id": "sr:market:1",
                        "name": "total",
                        "books": [
                            {
                                "id": "sr:book:18186", # FanDuel Mock
                                "name": "FanDuel (MOCK)",
                                "outcomes": [
                                    {"type": "over", "total": round(total, 1), "odds": "1.91"},
                                    {"type": "under", "total": round(total, 1), "odds": "1.91"}
                                ]
                            }
                        ]
                    }
                ]
            })
            
        return mock_response

    def extract_total(self, sport_event, book_name_priority=["FanDuel", "DraftKings"]):
        """
        Helper to extract a specific total from a sport_event object.
        """
        for market in sport_event.get("markets", []):
            if market.get("name") in ["total", "totals"]:
                # Try to find preferred bookmakers
                books = market.get("books", [])
                
                # Sort books by our priority
                selected_book = None
                for priority in book_name_priority:
                    for b in books:
                        if priority.lower() in b.get("name", "").lower():
                            selected_book = b
                            break
                    if selected_book: break
                
                if not selected_book and books:
                    selected_book = books[0]
                
                if selected_book:
                    outcomes = selected_book.get("outcomes", [])
                    for o in outcomes:
                        if "total" in o:
                            return float(o["total"])
        return None
