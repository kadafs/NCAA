"""
run_football_daily.py
======================
Universal daily football (soccer) prediction runner.
Covers EVERY league on api-football.com — no exclusions.

Pipeline per league:
  1. GET /fixtures?date=YYYY-MM-DD  (single call — discovers all active leagues)
  2. For each league: load cached stats OR fetch /teams/statistics (paid tier)
  3. Dixon-Coles xG → Poisson BTTS% / Draw% → FootballEngine.calculate()
  4. Output table to console + save to data/football/universal_predictions_YYYY-MM-DD.json

Usage:
    python run_football_daily.py                       # all leagues today
    python run_football_daily.py --league_id 39        # Premier League only
    python run_football_daily.py --date 2026-03-15     # specific date (paid tier = works)
    python run_football_daily.py --min_games 2         # skip leagues with < 2 fixtures
    python run_football_daily.py --mode full           # sharp layer
    python run_football_daily.py --refresh             # force re-fetch stats
    python run_football_daily.py --trace               # show engine math logs
"""

import sys
import os
import io
import json
import math
import time
import argparse
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from glob import glob
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

API_KEY  = os.getenv("API_BASKETBALL_KEY")          # Same key covers api-sports football
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}
ET_TZ    = timezone.utc

# Stats cache max age in seconds (24 hours)
CACHE_MAX_AGE = 86400

# Minimum games a team must have played before we predict their game
MIN_GAMES_PLAYED = 4


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------


# The curated list of High-Priority "Tier 1 and Tier 2" global leagues.
# Limits the engine to pull /teams/statistics only for these leagues
# to prevent busting the 100 API Request/day Free Tier limit.
PRIORITY_LEAGUES = {
    # Top 5 Europe + 2nd Divisions
    39, 40,   # English Premier League, Championship
    140, 141, # Spain La Liga, Segunda
    135, 136, # Italy Serie A, Serie B
    78, 79,   # Germany Bundesliga, 2. Bundesliga
    61, 62,   # France Ligue 1, Ligue 2
    
    # European Tournaments
    2, 3, 848, # UCL, Europa, Conference Leagues
    
    # Americas
    253, 254, # MLS, USL
    71,       # Brazil Serie A
    262,      # Liga MX
    128,      # Argentina Liga Profesional
    
    # Top European Tier 2
    88,       # Netherlands Eredivisie
    94,       # Portugal Primeira Liga
    61,       # France Ligue 1
    119,      # Denmark Superliga
    144,      # Belgium Pro League
    203,      # Turkey Super Lig
    103,      # Norway Eliteserien
    113,      # Sweden Allsvenskan
    
    # Asia / RoW
    307,      # Saudi Pro League
    98,       # Japan J1 League
    292,      # South Korea K League 1
    
    # Domestic Cups (Late Stage usually)
    45, 48,   # FA Cup, League Cup
    143,      # Copa del Rey
    137,      # Coppa Italia
    81,       # DFB Pokal
}

def get_today_str(date_str=None):
    if date_str:
        return date_str
    return datetime.now(ET_TZ).strftime("%Y-%m-%d")


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def safe_get(url, params, retries=3, delay=0.4):
    """Requests wrapper with retry and polite delay."""
    for attempt in range(retries):
        try:
            time.sleep(delay)
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            print(f"    HTTP {r.status_code} (attempt {attempt + 1}), retrying...")
        except Exception as e:
            print(f"    Request error (attempt {attempt + 1}): {e}")
            time.sleep(2 ** attempt)
    return {}


def is_cache_fresh(path, max_age=CACHE_MAX_AGE):
    """True if a file exists and was modified less than max_age seconds ago."""
    if not os.path.exists(path):
        return False
    age = time.time() - os.path.getmtime(path)
    return age < max_age


# ------------------------------------------------------------------
# STEP 1: FETCH ALL FIXTURES FOR THE DAY
# ------------------------------------------------------------------

def fetch_all_fixtures(date_str, refresh=False):
    """
    Single /fixtures?date= call — returns all leagues active today.
    Returns { league_id: { league_info, season, [games] } }
    """
    cache_path = f"data/football/universal_fixtures_{date_str}.json"

    # For today's date, use a short 4-hour cache so completed game scores
    # get picked up when the script re-runs later in the evening.
    # For past/future dates the file is effectively permanent.
    today_str = datetime.now(ET_TZ).strftime("%Y-%m-%d")
    fixture_cache_max_age = 4 * 3600 if (date_str == today_str) else 365 * 24 * 3600

    if not refresh and is_cache_fresh(cache_path, max_age=fixture_cache_max_age):
        print(f"  Using cached fixtures: {cache_path}")
        return load_json(cache_path)

    print(f"  Fetching all football fixtures for {date_str}...")
    data = safe_get(f"{BASE_URL}/fixtures", {"date": date_str})
    fixtures = data.get("response", [])
    total = data.get("results", 0)
    print(f"  Got {total} fixtures across all leagues.")

    from collections import defaultdict
    by_league = {}

    for fix in fixtures:
        league   = fix.get("league", {})
        lid      = league.get("id")
        lname    = league.get("name", "Unknown")
        country  = league.get("country", "")
        season   = league.get("season")
        teams    = fix.get("teams", {})
        goals    = fix.get("goals", {})
        fixture  = fix.get("fixture", {})
        status   = fixture.get("status", {}).get("short", "NS")

        home_name  = teams.get("home", {}).get("name", "?")
        away_name  = teams.get("away", {}).get("name", "?")
        home_id    = teams.get("home", {}).get("id")
        away_id    = teams.get("away", {}).get("id")
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        kickoff    = fixture.get("date", "")[:16].replace("T", " ")
        is_done    = status in ("FT", "AET", "PEN")
        btts_result = (home_goals is not None and away_goals is not None
                       and home_goals > 0 and away_goals > 0) if is_done else None
        draw_result = (home_goals == away_goals) if is_done else None

        game = {
            "fixture_id":  fixture.get("id"),
            "home_id":     home_id,
            "away_id":     away_id,
            "home_team":   home_name,
            "away_team":   away_name,
            "kickoff":     kickoff,
            "status":      status,
            "is_completed": is_done,
            "home_goals":  home_goals,
            "away_goals":  away_goals,
            "btts_result": btts_result,
            "draw_result": draw_result,
        }

        if lid not in by_league:
            by_league[lid] = {
                "league_id":   lid,
                "league_name": lname,
                "country":     country,
                "season":      season,
                "games":       [],
            }
        by_league[lid]["games"].append(game)

    os.makedirs("data/football", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(by_league, f, indent=2)
    return by_league


# ------------------------------------------------------------------
# STEP 2: FETCH / CACHE TEAM STATS FOR A LEAGUE
# ------------------------------------------------------------------

def check_cache_valid_for_games(cached_data, games):
    """Ensure all teams playing in the given games are actually present in the cache."""
    if not cached_data: return False
    teams_dict = cached_data.get("teams", {})
    cached_ids = {v.get("team_id") for v in teams_dict.values() if v.get("team_id")}
    
    for g in games:
        h_id = g.get("home_id")
        a_id = g.get("away_id")
        if h_id and h_id not in cached_ids: return False
        if a_id and a_id not in cached_ids: return False
    return True


def get_or_fetch_stats(league_id, season, games, refresh=False):
    """
    Returns {team_name: stats_dict} for a league.
    """
    # Priority 1: Check existing stats
    if not refresh:
        for stats_file in glob("data/football/*_stats.json"):
            cached = load_json(stats_file)
            if cached and cached.get("league_id") == league_id and is_cache_fresh(stats_file):
                if check_cache_valid_for_games(cached, games):
                    return cached.get("teams", {}), cached.get("league_averages", {})

    # Priority 2: Universal cache
    universal_cache = f"data/football/universal_{league_id}_stats.json"
    if not refresh and is_cache_fresh(universal_cache):
        cached = load_json(universal_cache)
        if cached and check_cache_valid_for_games(cached, games):
            return cached.get("teams", {}), cached.get("league_averages", {})

    # Priority 3: Fetch from API
    return fetch_stats_from_api(league_id, season, games)


def fetch_stats_from_api(league_id, season, games):
    """
    Pulls /teams/statistics. To avoid rate-limit hangs on huge leagues (like Friendlies
    with 2000+ teams), it only fetches stats for teams actually playing today.
    """
    teams_data = safe_get(f"{BASE_URL}/teams", {"league": league_id, "season": season})
    teams = teams_data.get("response", [])

    if not teams:
        prev = season - 1 if isinstance(season, int) else int(str(season)[:4]) - 1
        teams_data = safe_get(f"{BASE_URL}/teams", {"league": league_id, "season": prev})
        teams = teams_data.get("response", [])
        if teams:
            season = prev
        else:
            return {}, {}

    # Filter `teams` to only those playing in `games` to avoid massive API loops
    playing_team_ids = set()
    for g in games:
        if g.get("home_id"): playing_team_ids.add(g.get("home_id"))
        if g.get("away_id"): playing_team_ids.add(g.get("away_id"))
        
    filtered_teams = []
    for t_entry in teams:
        tid = t_entry.get("team", {}).get("id")
        
        # Exact ID matching eliminates textual mismatches entirely
        if tid in playing_team_ids:
            filtered_teams.append(t_entry)
            
    # If the filter is too tight, fallback to fetching all (capped at 80 to prevent total hangs)
    if not filtered_teams:
        filtered_teams = teams[:80]
    else:
        # Also cap filtered just in case
        filtered_teams = filtered_teams[:80]

    raw_stats = []

    for team_entry in filtered_teams:
        team = team_entry.get("team", {})
        tid  = team.get("id")
        name = team.get("name", "Unknown")

        r = safe_get(f"{BASE_URL}/teams/statistics",
                     {"team": tid, "league": league_id, "season": season})
        stats = r.get("response", {})
        if not stats:
            continue

        games       = stats.get("fixtures", {})
        goals       = stats.get("goals", {})
        form_str    = stats.get("form", "")

        played_home = games.get("played", {}).get("home", 0)
        played_away = games.get("played", {}).get("away", 0)
        played_all  = games.get("played", {}).get("total", 0)

        wins_home   = games.get("wins",  {}).get("home", 0)
        wins_away   = games.get("wins",  {}).get("away", 0)
        draws_home  = games.get("draws", {}).get("home", 0)
        draws_away  = games.get("draws", {}).get("away", 0)

        gf_home = goals.get("for",     {}).get("total", {}).get("home", 0) or 0
        gf_away = goals.get("for",     {}).get("total", {}).get("away", 0) or 0
        gf_all  = goals.get("for",     {}).get("total", {}).get("total", 0) or 0
        ga_home = goals.get("against", {}).get("total", {}).get("home", 0) or 0
        ga_away = goals.get("against", {}).get("total", {}).get("away", 0) or 0
        ga_all  = goals.get("against", {}).get("total", {}).get("total", 0) or 0

        cs          = stats.get("clean_sheet", {}).get("total", 0) or 0
        failed      = stats.get("failed_to_score", {}).get("total", 0) or 0
        btts_count  = played_all - cs - failed

        def _(n, d): return round(n / d, 3) if d else 0

        raw_stats.append({
            "name":         name,
            "team_id":      tid,
            "league_id":    league_id,
            "season":       season,
            "played_home":  played_home,
            "played_away":  played_away,
            "played_all":   played_all,
            "goals_for_home": gf_home,
            "goals_for_away": gf_away,
            "goals_for_all":  gf_all,
            "goals_ag_home":  ga_home,
            "goals_ag_away":  ga_away,
            "goals_ag_all":   ga_all,
            "pgf_home":   _(gf_home, played_home),
            "pgf_away":   _(gf_away, played_away),
            "pgf_all":    _(gf_all,  played_all),
            "pga_home":   _(ga_home, played_home),
            "pga_away":   _(ga_away, played_away),
            "pga_all":    _(ga_all,  played_all),
            "wins_home":  wins_home,
            "wins_away":  wins_away,
            "draws_home": draws_home,
            "draws_away": draws_away,
            "win_pct":    _((wins_home + wins_away), played_all),
            "clean_sheets":  cs,
            "failed_to_score":  failed,
            "btts_count":    btts_count,
            "btts_rate":     _(btts_count, played_all),
            "form":          form_str,
            "form_wins":     form_str.upper().count("W") if form_str else 0,
            "form_draws":    form_str.upper().count("D") if form_str else 0,
            "_raw_goals": {
                "for_home":     gf_home,
                "for_away":     gf_away,
                "against_home": ga_home,
                "against_away": ga_away,
            }
        })

    if not raw_stats:
        return {}, {}

    # Compute league averages
    hgf_list, agf_list = [], []
    for s in raw_stats:
        ph = s["played_home"] or 1
        pa = s["played_away"] or 1
        g  = s["_raw_goals"]
        if g["for_home"] > 0: hgf_list.append(g["for_home"] / ph)
        if g["for_away"] > 0: agf_list.append(g["for_away"] / pa)

    avg_home = round(sum(hgf_list) / len(hgf_list), 3) if hgf_list else 1.5
    avg_away = round(sum(agf_list) / len(agf_list), 3) if agf_list else 1.2
    league_avgs = {
        "avg_home_goals_for": avg_home,
        "avg_away_goals_for": avg_away,
    }

    # Compute normalized attack/defense ratings
    teams_dict = {}
    for s in raw_stats:
        s.pop("_raw_goals", None)
        ph = s["pgf_home"]; pa = s["pgf_away"]
        dh = s["pga_home"]; da = s["pga_away"]
        s["attack_rating_home"]  = round(ph / avg_home, 4) if avg_home else 1.0
        s["attack_rating_away"]  = round(pa / avg_away, 4) if avg_away else 1.0
        s["attack_rating_all"]   = round((s["attack_rating_home"] + s["attack_rating_away"]) / 2, 4)
        s["defense_rating_home"] = round(dh / avg_home, 4) if avg_home else 1.0
        s["defense_rating_away"] = round(da / avg_away, 4) if avg_away else 1.0
        s["defense_rating_all"]  = round((s["defense_rating_home"] + s["defense_rating_away"]) / 2, 4)
        s["league_avg_home_goals"] = avg_home
        s["league_avg_away_goals"] = avg_away
        teams_dict[s["name"]] = s

    # Save cache
    os.makedirs("data/football", exist_ok=True)
    out = {
        "league_id":       league_id,
        "season":          season,
        "fetched_at":      datetime.now(ET_TZ).isoformat(),
        "team_count":      len(teams_dict),
        "league_averages": league_avgs,
        "teams":           teams_dict,
    }
    save_json(f"data/football/universal_{league_id}_stats.json", out)
    return teams_dict, league_avgs


# ------------------------------------------------------------------
# STEP 3: API WRAPPERS FOR STANDINGS & H2H
# ------------------------------------------------------------------

def fetch_standings(league_id, season, refresh=False):
    cache_file = f"data/football/standings_{league_id}_{season}.json"
    if not refresh and is_cache_fresh(cache_file):
        return load_json(cache_file)
    r = safe_get(f"{BASE_URL}/standings", {"league": league_id, "season": season})
    response = r.get("response", [])
    if not response:
        return []
    
    # Standings can be a list of lists (for different groups/stages)
    standings_lists = response[0].get("league", {}).get("standings", [])
    flat_standings = []
    for s_list in standings_lists:
        if isinstance(s_list, list):
            flat_standings.extend(s_list)
        else:
            flat_standings.append(s_list)
            
    if flat_standings:
        save_json(cache_file, flat_standings)
    return flat_standings

def fetch_team_recent_fixtures(team_id, last=5, refresh=False):
    """Fetch last N completed fixtures for a team."""
    cache_file = f"data/football/recent_{team_id}.json"
    
    if not refresh and os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < 86400:  # 24h cache for recent form
            return load_json(cache_file)

    r = safe_get(f"{BASE_URL}/fixtures", {"team": team_id, "last": last, "status": "FT"})
    data = r.get("response", [])
    if data:
        save_json(cache_file, data)
    return data

def fetch_h2h(home_id, away_id, refresh=False):
    if not home_id or not away_id:
        return []
    min_id = min(home_id, away_id)
    max_id = max(home_id, away_id)
    h2h_str = f"{min_id}-{max_id}"
    cache_file = f"data/football/h2h_{h2h_str}.json"
    
    if not refresh and os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < 86400 * 14:  # H2H changes slowly, 14 days is safe between meetings
            return load_json(cache_file)

    r = safe_get(f"{BASE_URL}/fixtures/headtohead", {"h2h": h2h_str, "last": 5})
    data = r.get("response", [])
    if data is not None:
        save_json(cache_file, data)
    return data or []


# ------------------------------------------------------------------
# STEP 4: FUZZY TEAM MATCHING & MATH LOGIC
# ------------------------------------------------------------------

def find_team(team_id, name, teams):
    if not teams: return None, None
    if team_id:
        for k, v in teams.items():
            if v.get("team_id") == team_id:
                return k, v
    if not name: return None, None
    nl = name.lower().strip()
    if name in teams: return name, teams[name]
    for k in teams:
        if k.lower() == nl: return k, teams[k]
    for k in teams:
        kl = k.lower()
        if kl in nl or nl in kl: return k, teams[k]
    nw = set(nl.split())
    best, score = None, 0
    for k in teams:
        ov = len(nw & set(k.lower().split()))
        if ov > score: best, score = k, ov
    if score >= 1: return best, teams[best]
    return None, None


# ------------------------------------------------------------------
# STEP 4: xG CALCULATION (Dixon-Coles Poisson)
# ------------------------------------------------------------------

def poisson_prob(lam, k):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return (math.e ** -lam) * (lam ** k) / math.factorial(k)

def calc_btts_prob(xg_h, xg_a):
    return round((1 - poisson_prob(xg_h, 0)) * (1 - poisson_prob(xg_a, 0)), 4)

def calc_draw_prob(xg_h, xg_a, max_g=6):
    return round(sum(poisson_prob(xg_h, k) * poisson_prob(xg_a, k) for k in range(max_g + 1)), 4)

def calc_over_prob(xg_total, threshold):
    under_p = 0.0
    for k in range(int(threshold + 0.5)):
        under_p += poisson_prob(xg_total, k)
    return round(1.0 - under_p, 4)

def calc_xg(home_s, away_s, avg_home, avg_away):
    # Dynamic Bayesian Regression: Trust scales with games played
    # 1 game = 0.11 trust, 4 games = 0.44 trust, 8+ games = capped at 0.88.
    def get_regression(played):
        return min(0.88, max(0.10, played * 0.11))
        
    reg_home = get_regression(home_s.get("played_all", 1))
    reg_away = get_regression(away_s.get("played_all", 1))

    ar_home = home_s.get("attack_rating_home", 1.0)
    dr_away = away_s.get("defense_rating_away", 1.0)
    xg_h_raw = ar_home * dr_away * avg_home

    ar_away = away_s.get("attack_rating_away", 1.0)
    dr_home = home_s.get("defense_rating_home", 1.0)
    xg_a_raw = ar_away * dr_home * avg_away

    xg_h = round(xg_h_raw * reg_home + avg_home * (1 - reg_home), 3)
    xg_a = round(xg_a_raw * reg_away + avg_away * (1 - reg_away), 3)
    return xg_h, xg_a

def calc_xg_elo(home_name, away_name):
    elo_path = os.path.join(os.path.dirname(__file__), "data", "football", "elo_ratings.json")
    try:
        with open(elo_path, 'r', encoding='utf-8') as f:
            elo_data = json.load(f).get("ratings", {})
    except Exception:
        elo_data = {}

    # Fuzzy match Elo names
    def get_elo(name):
        c_name = name.lower().replace(" u23", "").replace(" u21", "").replace(" u20", "").replace(" u19", "").replace(" u18", "").replace(" u17", "").replace(" w", "").strip()
        # Generate a small repeatable offset based on the name so unknowns aren't identically rated
        hash_offset = sum(ord(c) for c in c_name) % 100
        base = 1450 + hash_offset
        for k, v in elo_data.items():
            if k.lower() == c_name or k.lower() in c_name or c_name in k.lower():
                return v
        return base

    h_elo = get_elo(home_name)
    a_elo = get_elo(away_name)
    
    # +50 Elo for Home Advantage
    diff = (h_elo + 50) - a_elo
    
    # Conversion: 100 Elo points ~ 0.35 goals difference. Base Int Total ~ 2.45
    base = 2.45 / 2.0
    xg_diff = (diff / 100.0) * 0.35
    
    xg_h = round(base + (xg_diff / 2.0), 3)
    xg_a = round(base - (xg_diff / 2.0), 3)
    
    return max(0.25, xg_h), max(0.25, xg_a)


# ------------------------------------------------------------------
# STEP 5: RUN ENGINE PER GAME
# ------------------------------------------------------------------

def predict_game(game, home_s, away_s, avg_home, avg_away, mode, trace, country=""):
    from core.football_engine import FootballEngine

    home_name = game["home_team"]
    away_name = game["away_team"]

    # National teams often only play 1-2 games a year. Bypass the strict check.
    min_req = 1 if country.lower() == "world" else MIN_GAMES_PLAYED
    
    if country.lower() == "world":
        xg_h, xg_a = calc_xg_elo(home_name, away_name)
    else:
        if home_s.get("played_all", 0) < min_req or away_s.get("played_all", 0) < min_req:
            return None, f"Insufficient games played (need {min_req}+)"
        xg_h, xg_a = calc_xg(home_s, away_s, avg_home, avg_away)
    btts_prob   = calc_btts_prob(xg_h, xg_a)
    draw_prob   = calc_draw_prob(xg_h, xg_a)

    home_cs_rate  = home_s.get("clean_sheets", 0) / max(home_s.get("played_all", 1), 1)
    away_cs_rate  = away_s.get("clean_sheets", 0) / max(away_s.get("played_all", 1), 1)
    home_draws    = home_s.get("form_draws", 0)
    away_draws    = away_s.get("form_draws", 0)
    home_form     = home_s.get("form_wins", 0)
    away_form     = away_s.get("form_wins", 0)

    game_row = {
        "fixture_id":       game.get("fixture_id"),
        "matchup":          f"{away_name} @ {home_name}",
        "home_team":        home_name,
        "away_team":        away_name,
        "kickoff":          game.get("kickoff", ""),
        "xg_home":          xg_h,
        "xg_away":          xg_a,
        "xg_total":         round(xg_h + xg_a, 3),
        "btts_prob":        btts_prob,
        "draw_prob":        draw_prob,
        "is_both_defensive": home_cs_rate > 0.35 and away_cs_rate > 0.35,
        "is_both_attacking": (home_s.get("pgf_all", 0) > avg_home * 1.1 and
                              away_s.get("pgf_all", 0) > avg_away * 1.1),
        "is_draw_prone":    home_draws >= 2 and away_draws >= 2,
        "combined_form_wins": home_form + away_form,
        "home_cs_rate":     round(home_cs_rate, 3),
        "away_cs_rate":     round(away_cs_rate, 3),
        "home_btts_rate":   home_s.get("btts_rate", 0.5),
        "away_btts_rate":   away_s.get("btts_rate", 0.5),
        "statsH": {
            "attack_rating":  home_s.get("attack_rating_home"),
            "defense_rating": home_s.get("defense_rating_home"),
            "pgf": home_s.get("pgf_home"), "pga": home_s.get("pga_home"),
            "form": home_s.get("form"), "btts_rate": home_s.get("btts_rate"),
            "clean_sheets": home_s.get("clean_sheets"),
            "played_all": home_s.get("played_all"),
            "failed_score": home_s.get("failed_score"),
            "rank": home_s.get("league_rank"),
            "win_pct": home_s.get("win_pct")
        },
        "statsA": {
            "attack_rating":  away_s.get("attack_rating_away"),
            "defense_rating": away_s.get("defense_rating_away"),
            "pgf": away_s.get("pgf_away"), "pga": away_s.get("pga_away"),
            "form": away_s.get("form"), "btts_rate": away_s.get("btts_rate"),
            "clean_sheets": away_s.get("clean_sheets"),
            "played_all": away_s.get("played_all"),
            "failed_score": away_s.get("failed_score"),
            "rank": away_s.get("league_rank"),
            "win_pct": away_s.get("win_pct")
        },
        "metadata": {},
    }

    # Default config — matches the shape FootballEngine.calculate() expects
    default_config = {
        "regression_factor":    0.88,
        "min_games_played":     min_req,
        "btts_base_rate":       round((home_s.get("btts_rate", 0.5) + away_s.get("btts_rate", 0.5)) / 2, 3),
        "draw_base_rate":       0.27,
        "btts_edge_threshold":  0.04,   # minimum edge to trigger PLAY decision
        "draw_edge_threshold":  0.05,
        "btts_market_avg":      0.52,   # typical sportsbook implied BTTS probability
        "hca_goals":            0.25,
        "mode":                 mode,
        "sharp_params": {
            "defensive_btts_drag":      -0.06,
            "defensive_draw_boost":      0.03,
            "attacking_btts_boost":      0.05,
            "btts_historical_weight":    0.15,
            "draw_prone_boost":          0.04,
            "form_hot_threshold":        7,
            "form_hot_btts_boost":       0.03,
            "form_cold_threshold":       2,
            "form_cold_btts_drag":      -0.03,
            "max_btts_adjustment":       0.12,
        },
    }

    try:
        engine_mode = "safe" if country.lower() == "world" else mode
        engine = FootballEngine(default_config, mode=engine_mode, trace=trace)
        result = engine.calculate(game_row)
        return result, None
    except Exception as e:
        return None, str(e)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Universal Daily Football Predictions (All Leagues)")
    parser.add_argument("--date",       help="Date YYYY-MM-DD (default: today)")
    parser.add_argument("--league_id",  type=int, help="Only run one league by API ID")
    parser.add_argument("--mode",       choices=["safe", "full"], default="safe")
    parser.add_argument("--min_games",  type=int, default=1,
                        help="Skip leagues with fewer than this many fixtures today")
    parser.add_argument("--refresh",    action="store_true", help="Re-fetch fixtures and stats")
    parser.add_argument("--trace",      action="store_true", help="Show engine math trace")
    parser.add_argument("--all-leagues",action="store_true", help="DISABLE Priority Filter and run EVERY league (WILL BURN API CREDITS!)")
    parser.add_argument("--low-data",   action="store_true", help="Skip expensive H2H/Recent for Match Center")
    args = parser.parse_args()

    date_str = get_today_str(args.date)

    print("\n" + "=" * 70)
    print(f"  UNIVERSAL FOOTBALL PREDICTIONS | {date_str} | {args.mode.upper()}")
    print("=" * 70)

    # Check for stale international elo ratings and auto-update if strictly necessary
    try:
        from utils.update_international_elo import generate_elo_ratings
        generate_elo_ratings(force=False)
    except Exception as e:
        print(f"  [ELO] Warning: Could not auto-check ratings: {e}")

    # Step 1: Fixtures
    leagues_map = fetch_all_fixtures(date_str, refresh=args.refresh)
    if not leagues_map:
        print("  No fixtures found. Check API key or try --refresh.")
        return

    # Filter
    leagues = list(leagues_map.values())
    if args.league_id:
        leagues = [l for l in leagues if l["league_id"] == args.league_id]
    elif not args.all_leagues:
        # Enforce API priority filter!
        leagues = [l for l in leagues if l["league_id"] in PRIORITY_LEAGUES]
        
    if args.min_games > 1:
        leagues = [l for l in leagues if len(l["games"]) >= args.min_games]

    # Sort by name for readable output
    leagues.sort(key=lambda l: l["league_name"])
    print(f"  Running predictions for {len(leagues)} league(s)...\n")

    all_predictions = []
    total_predicted = 0
    total_skipped   = 0

    for entry in leagues:
        lid      = entry["league_id"]
        lname    = entry["league_name"]
        country  = entry.get("country", "")
        season   = entry.get("season")
        games    = entry["games"]

        # Only predict upcoming / not yet finished
        upcoming = [g for g in games if not g.get("is_completed")]
        if not upcoming:
            upcoming = games  # useful for backtesting past dates

        print(f"  [{lid}] {lname} ({country}) — {len(games)} game(s)")

        # Step 2: Team stats
        teams, league_avgs = get_or_fetch_stats(lid, season, games, refresh=args.refresh)
        if not teams:
            print(f"    SKIP -- no team stats available\n")
            total_skipped += len(games)
            continue

        avg_home = league_avgs.get("avg_home_goals_for", 1.5)
        avg_away = league_avgs.get("avg_away_goals_for", 1.2)

        # Fetch and cache standings for the league early
        league_standings = fetch_standings(lid, season, refresh=args.refresh)
        if not league_standings and season == 2025:
            # print(f"    [DEBUG] No standings for {lid} in 2025, trying 2026...")
            league_standings = fetch_standings(lid, 2026, args.refresh)

        # Step 3: Predict each game
        for game in upcoming:
            home = game["home_team"]
            away = game["away_team"]

            hk, home_s = find_team(game.get("home_id"), home, teams)
            ak, away_s = find_team(game.get("away_id"), away, teams)


            if not home_s or not away_s:
                missing = []
                if not home_s: missing.append(home)
                if not away_s: missing.append(away)
                print(f"    {away:28} @ {home:28}  -- SKIP (stats missing: {', '.join(missing)})")
                total_skipped += 1
                continue

            result, err = predict_game(game, home_s, away_s, avg_home, avg_away, args.mode, args.trace, country)
            if err:
                print(f"    {away:28} @ {home:28}  -- SKIP ({err})")
                total_skipped += 1
                continue
                
            # Grab latest ranks
            home_rank = next((s.get("rank") for s in league_standings if s.get("team", {}).get("id") == home_s.get("team_id")), None)
            away_rank = next((s.get("rank") for s in league_standings if s.get("team", {}).get("id") == away_s.get("team_id")), None)

            # Inject the ranks directly into the stats dicts for extraction later
            home_s["league_rank"] = home_rank
            away_s["league_rank"] = away_rank

            btts_pct = result["btts_prob_final"] * 100
            draw_pct = result["draw_prob_final"] * 100
            edge_pct = result["btts_edge"] * 100
            conf     = result["btts_confidence"]
            decision = result["btts_decision"]
            xg_h     = result["xg_home"]
            xg_a     = result["xg_away"]

            print(f"    {away:28} @ {home:28}")
            print(f"      xG {xg_h:.2f}-{xg_a:.2f}  BTTS:{btts_pct:.1f}%  "
                  f"Draw:{draw_pct:.1f}%  Edge:{edge_pct:+.1f}%  [{conf}] {decision}")
            # 1X2 line
            hw_pct = result.get("home_win_prob", 0)
            dw_pct = result.get("draw_prob_1x2", 0)
            aw_pct = result.get("away_win_prob", 0)
            hw_odds = result.get("home_win_odds", 0)
            dw_odds = result.get("draw_odds", 0)
            aw_odds = result.get("away_win_odds", 0)
            pred    = result.get("predicted_result", "?")
            print(f"      1X2:  Home {hw_pct:.1f}% ({hw_odds}x)  "
                  f"Draw {dw_pct:.1f}% ({dw_odds}x)  "
                  f"Away {aw_pct:.1f}% ({aw_odds}x)  → {pred}")

            if args.trace:
                for log in result.get("logs", []):
                    print(f"        > {log}")

            # Check actual result if game finished
            if game.get("is_completed") and game.get("home_goals") is not None:
                hg = game["home_goals"]; ag = game["away_goals"]
                actual_btts = "Y" if (hg > 0 and ag > 0) else "N"
                actual_draw = "Y" if hg == ag else "N"
                if hg > ag:   actual_result = "HOME"
                elif hg == ag: actual_result = "DRAW"
                else:          actual_result = "AWAY"
                print(f"      Final: {ag}-{hg}  BTTS:{actual_btts}  Result:{actual_result}  "
                      f"(Pred:{pred})")

            all_predictions.append({
                "league_id":   lid,
                "league":      lname,
                "country":     country,
                "date":        date_str,
                "away_team":   away,
                "home_team":   home,
                "status":      game.get("status", ""),
                "kickoff":     game.get("kickoff", ""),
                "xg_home":     round(xg_h, 3),
                "xg_away":     round(xg_a, 3),
                "xg_total":    round(xg_h + xg_a, 3),
                # BTTS
                "btts_prob":        round(btts_pct, 1),
                "btts_edge":        round(edge_pct, 1),
                "btts_decision":    decision,
                "btts_confidence":  conf,
                "draw_prob":        round(draw_pct, 1),
                "draw_fair_odds":   result.get("draw_fair_odds"),
                "draw_value_flag":  result.get("draw_value_flag", False),
                # 1X2
                "home_win_prob":    result.get("home_win_prob"),
                "draw_prob_1x2":    result.get("draw_prob_1x2"),
                "away_win_prob":    result.get("away_win_prob"),
                "home_win_odds":    result.get("home_win_odds"),
                "draw_odds":        result.get("draw_odds"),
                "away_win_odds":    result.get("away_win_odds"),
                "predicted_result": result.get("predicted_result"),
                "mode":        args.mode,
                "timestamp":   datetime.now(ET_TZ).isoformat(),
                # Actual results for backtesting
                "actual_home_goals": game.get("home_goals") if game.get("is_completed") else None,
                "actual_away_goals": game.get("away_goals") if game.get("is_completed") else None,
                "actual_btts":   game.get("btts_result"),
                "actual_draw":   game.get("draw_result"),
                "actual_result": (
                    "HOME" if (game.get("is_completed") and game.get("home_goals") is not None
                               and game["home_goals"] > game["away_goals"]) else
                    "DRAW" if (game.get("is_completed") and game.get("home_goals") is not None
                               and game["home_goals"] == game["away_goals"]) else
                    "AWAY" if (game.get("is_completed") and game.get("home_goals") is not None) else None
                ),
                # Match Center Data for UI Drawer
                "match_center": {
                    "h2h": fetch_h2h(home_s.get("team_id"), away_s.get("team_id"), args.refresh) if not args.low_data else [],
                    "recentH": fetch_team_recent_fixtures(home_s.get("team_id"), last=5, refresh=args.refresh) if not args.low_data else [],
                    "recentA": fetch_team_recent_fixtures(away_s.get("team_id"), last=5, refresh=args.refresh) if not args.low_data else [],
                    "full_standings": league_standings if len(league_standings) > 0 else None,
                    "over_1_5_prob": round(calc_over_prob(xg_h + xg_a, 1.5) * 100, 1),
                    "over_2_5_prob": round(calc_over_prob(xg_h + xg_a, 2.5) * 100, 1),
                    "statsH": {
                        "played": home_s.get("played_all"),
                        "win_pct": home_s.get("win_pct"),
                        "scored": home_s.get("pgf_all"),
                        "conceded": home_s.get("pga_all"),
                        "clean_sheets": home_s.get("clean_sheets"),
                        "failed_to_score": home_s.get("failed_to_score"),
                        "btts_rate": home_s.get("btts_rate"),
                        "rank": home_s.get("league_rank"),
                        "form": home_s.get("form_wins")
                    },
                    "statsA": {
                        "played": away_s.get("played_all"),
                        "win_pct": away_s.get("win_pct"),
                        "scored": away_s.get("pgf_all"),
                        "conceded": away_s.get("pga_all"),
                        "clean_sheets": away_s.get("clean_sheets"),
                        "failed_to_score": away_s.get("failed_to_score"),
                        "btts_rate": away_s.get("btts_rate"),
                        "rank": away_s.get("league_rank"),
                        "form": away_s.get("form_wins")
                    }
                }
            })

            total_predicted += 1

        print()

    # Summary
    print("=" * 70)
    print(f"  COMPLETE: {total_predicted} predictions  |  {total_skipped} skipped")
    print("=" * 70)

    if all_predictions:
        out_path = f"data/football/universal_predictions_{date_str}.json"
        save_json(out_path, {
            "date":              date_str,
            "mode":              args.mode,
            "total_predictions": total_predicted,
            "predictions":       all_predictions,
        })
        print(f"\n  Saved -> {out_path}")

    print()


if __name__ == "__main__":
    main()
