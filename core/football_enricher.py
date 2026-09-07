"""
core/football_enricher.py
─────────────────────────
Fetches enrichment data from api-football endpoints for a given fixture:
  - /odds            → real bookmaker BTTS implied probability
  - /predictions     → API consensus winner prediction
  - /injuries        → per-league injury/suspension flags
  - /fixtures/statistics → corners, shots, cards, fouls per team
  - /fixtures/events → per-event card data for booking model
  - /fixtures/players → per-player match ratings

All functions are designed to be safe (never raise, return {} on failure).
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

# Booking points system
YELLOW_CARD_PTS = 10
RED_CARD_PTS    = 25   # straight red
# Note: 2nd yellow = yellow (10) + red (25) = 35 total


def _get(endpoint: str, params: dict, retries: int = 2) -> dict:
    """Safe GET wrapper. Returns {} on any failure."""
    if not API_KEY:
        return {}
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code == 429:
                time.sleep(2)
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt < retries:
                time.sleep(1)
    return {}


# ─────────────────────────────────────────────────────────────
# ODDS — real bookmaker implied probabilities
# ─────────────────────────────────────────────────────────────

def fetch_live_odds(fixture_id: int) -> dict:
    """
    Returns market-implied probabilities from the first available bookmaker.
    Falls back to empty dict if no odds available (e.g. lower league).

    Returns:
        {
          "btts_market_prob": float,   # implied BTTS YES probability (0-1)
          "home_odds": float,
          "draw_odds": float,
          "away_odds": float,
          "btts_yes_odds": float,
          "btts_no_odds": float,
          "over25_odds": float,
          "under25_odds": float,
          "bookmaker": str,
        }
    """
    data = _get("/odds", {"fixture": fixture_id})
    try:
        bookmakers = data["response"][0]["bookmakers"]
    except (KeyError, IndexError, TypeError):
        return {}

    result = {}
    for bk in bookmakers:
        bets = {b["name"]: b["values"] for b in bk.get("bets", [])}

        # 1X2
        if "Match Winner" in bets and "home_odds" not in result:
            for v in bets["Match Winner"]:
                val = v.get("value", "").lower()
                try:
                    odd = float(v["odd"])
                except (ValueError, KeyError):
                    continue
                if val == "home":
                    result["home_odds"] = odd
                elif val == "draw":
                    result["draw_odds"] = odd
                elif val == "away":
                    result["away_odds"] = odd

        # BTTS
        if "Both Teams Score" in bets and "btts_yes_odds" not in result:
            for v in bets["Both Teams Score"]:
                val = v.get("value", "").lower()
                try:
                    odd = float(v["odd"])
                except (ValueError, KeyError):
                    continue
                if val == "yes":
                    result["btts_yes_odds"] = odd
                    result["btts_market_prob"] = round(1 / odd, 4)
                elif val == "no":
                    result["btts_no_odds"] = odd

        # Goals Over/Under 2.5
        if "Goals Over/Under" in bets and "over25_odds" not in result:
            for v in bets["Goals Over/Under"]:
                val = v.get("value", "").lower()
                try:
                    odd = float(v["odd"])
                except (ValueError, KeyError):
                    continue
                if val == "over 2.5":
                    result["over25_odds"] = odd
                elif val == "under 2.5":
                    result["under25_odds"] = odd

        if result.get("btts_market_prob") and result.get("home_odds"):
            result["bookmaker"] = bk.get("name", "")
            break   # got everything we need

    return result


# ─────────────────────────────────────────────────────────────
# PREDICTIONS — API consensus
# ─────────────────────────────────────────────────────────────

def fetch_api_consensus(fixture_id: int) -> dict:
    """
    Returns the API-Football consensus prediction for a fixture.

    Returns:
        {
          "consensus_winner": str | None,
          "home_pct": str,
          "draw_pct": str,
          "away_pct": str,
          "advice": str,
        }
    """
    data = _get("/predictions", {"fixture": fixture_id})
    try:
        pred = data["response"][0]["predictions"]
    except (KeyError, IndexError, TypeError):
        return {}

    winner = pred.get("winner") or {}
    pct    = pred.get("percent") or {}
    return {
        "consensus_winner": winner.get("name"),
        "home_pct":  pct.get("home", "0%"),
        "draw_pct":  pct.get("draw", "0%"),
        "away_pct":  pct.get("away", "0%"),
        "advice":    pred.get("advice", ""),
    }


# ─────────────────────────────────────────────────────────────
# INJURIES — per league
# ─────────────────────────────────────────────────────────────

def fetch_injury_flags(league_id: int, season: int) -> dict:
    """
    Returns a dict mapping team_id → list of injury strings (deduplicated per player).

    Example:
        {33: ["Joelinton (Missing Fixture)", "Harvey Barnes (Questionable)"]}
    """
    data = _get("/injuries", {"league": league_id, "season": season})
    player_injuries: dict[int, dict[str, str]] = {}
    for item in data.get("response", []):
        try:
            team_id     = item["team"]["id"]
            player_name = item["player"]["name"]
            inj_type    = item["player"]["type"]  # "Missing Fixture" or "Questionable"

            team_dict = player_injuries.setdefault(team_id, {})
            existing  = team_dict.get(player_name)
            if not existing:
                team_dict[player_name] = inj_type
            elif existing != "Missing Fixture" and inj_type == "Missing Fixture":
                team_dict[player_name] = inj_type
        except (KeyError, TypeError):
            continue

    injuries: dict[int, list[str]] = {}
    for team_id, p_map in player_injuries.items():
        injuries[team_id] = [f"{p} ({t})" for p, t in p_map.items()]
    return injuries


# ─────────────────────────────────────────────────────────────
# FIXTURE STATISTICS — corners, shots, cards, fouls
# ─────────────────────────────────────────────────────────────

def fetch_match_stats(fixture_id: int) -> dict:
    """
    Returns per-team match statistics for a completed fixture.

    Returns:
        {
          "home": {"corners": int, "yellow_cards": int, "red_cards": int,
                   "fouls": int, "shots_total": int, "shots_on_goal": int,
                   "possession": int, "booking_pts": int},
          "away": { ... }
        }
    """
    data = _get("/fixtures/statistics", {"fixture": fixture_id})
    result = {}
    response = data.get("response", [])
    sides = ["home", "away"]

    for idx, block in enumerate(response[:2]):
        side = sides[idx]
        stats_raw = {s["type"]: s["value"] for s in block.get("statistics", [])}

        def _int(key, default=0):
            v = stats_raw.get(key)
            if v is None:
                return default
            try:
                return int(str(v).replace("%", ""))
            except (ValueError, TypeError):
                return default

        yellow = _int("Yellow Cards")
        red    = _int("Red Cards")
        booking_pts = (yellow * YELLOW_CARD_PTS) + (red * RED_CARD_PTS)

        result[side] = {
            "corners":       _int("Corner Kicks"),
            "yellow_cards":  yellow,
            "red_cards":     red,
            "fouls":         _int("Fouls"),
            "shots_total":   _int("Total Shots"),
            "shots_on_goal": _int("Shots on Goal"),
            "possession":    _int("Ball Possession"),
            "booking_pts":   booking_pts,
        }

    return result


# ─────────────────────────────────────────────────────────────
# FIXTURE EVENTS — card events (for booking model detail)
# ─────────────────────────────────────────────────────────────

def fetch_match_events(fixture_id: int) -> list:
    """
    Returns a list of card events from a completed fixture.

    Each entry:
        {"minute": int, "team_id": int, "team": str, "player": str,
         "type": "Yellow Card" | "Red Card", "booking_pts": int}
    """
    data = _get("/fixtures/events", {"fixture": fixture_id})
    events = []
    for ev in data.get("response", []):
        detail = ev.get("detail", "")
        ev_type = ev.get("type", "")

        if ev_type not in ("Card",):
            continue

        if "Yellow Card" in detail:
            pts = YELLOW_CARD_PTS
            card_type = "Yellow Card"
        elif "Red Card" in detail and "Yellow" not in detail:
            pts = RED_CARD_PTS
            card_type = "Red Card"
        elif "Yellow Red Card" in detail:  # 2nd yellow = yellow + red
            pts = YELLOW_CARD_PTS + RED_CARD_PTS
            card_type = "2nd Yellow / Red"
        else:
            continue

        try:
            events.append({
                "minute":     ev["time"]["elapsed"],
                "team_id":    ev["team"]["id"],
                "team":       ev["team"]["name"],
                "player":     ev["player"]["name"],
                "type":       card_type,
                "booking_pts": pts,
            })
        except (KeyError, TypeError):
            continue

    return events


# ─────────────────────────────────────────────────────────────
# FIXTURE PLAYERS — per-player match stats
# ─────────────────────────────────────────────────────────────

def fetch_player_stats(fixture_id: int) -> dict:
    """
    Returns top-rated players for home and away teams.

    Returns:
        {
          "home": [{"name": str, "rating": float, "goals": int, "assists": int}],
          "away": [...]
        }
    """
    data = _get("/fixtures/players", {"fixture": fixture_id})
    result = {}
    for idx, block in enumerate(data.get("response", [])[:2]):
        side = "home" if idx == 0 else "away"
        players = []
        for p in block.get("players", []):
            try:
                stats   = p["statistics"][0]
                games   = stats.get("games", {})
                rating_raw = games.get("rating")
                rating  = float(rating_raw) if rating_raw else 0.0
                players.append({
                    "name":    p["player"]["name"],
                    "rating":  rating,
                    "goals":   (stats.get("goals") or {}).get("total") or 0,
                    "assists": (stats.get("goals") or {}).get("assists") or 0,
                    "yellow_cards": (stats.get("cards") or {}).get("yellow") or 0,
                    "red_cards":    (stats.get("cards") or {}).get("red") or 0,
                })
            except (KeyError, TypeError, ValueError):
                continue
        # Sort by rating descending
        players.sort(key=lambda x: x["rating"], reverse=True)
        result[side] = players[:5]  # top 5 per team
    return result


# ─────────────────────────────────────────────────────────────
# ENRICHMENT SUMMARY — combine all per-fixture enrichment
# ─────────────────────────────────────────────────────────────

def enrich_fixture(fixture_id: int, home_team_id: int, away_team_id: int,
                   injury_cache: dict) -> dict:
    """
    Combines all per-fixture enrichment into one dict.
    Call this once per fixture in run_football_daily.py.

    Args:
        fixture_id:     API fixture ID
        home_team_id:   home team's API ID
        away_team_id:   away team's API ID
        injury_cache:   pre-fetched {team_id: [injury strings]} for the league

    Returns combined enrichment dict to be merged into the prediction row.
    """
    if not fixture_id:
        return {}

    enrichment = {}

    # Odds
    odds = fetch_live_odds(fixture_id)
    if odds:
        enrichment["market_odds"] = odds
        # Expose btts_market_prob at top level for engine
        enrichment["btts_market_prob"] = odds.get("btts_market_prob")

    # Consensus
    consensus = fetch_api_consensus(fixture_id)
    if consensus:
        enrichment["api_consensus"] = consensus

    # Injuries from cache (no extra API call)
    enrichment["home_injuries"] = injury_cache.get(home_team_id, [])
    enrichment["away_injuries"] = injury_cache.get(away_team_id, [])

    return enrichment
