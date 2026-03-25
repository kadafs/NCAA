"""
calibrate_league.py
====================
Auto-calibrates a basketball league config from historical api-basketball.com data.
Derives: hca_total_bump, pace_pivot, eff_pivot, regression_factor.
Falls back to tier templates for thin-data leagues.

Usage:
    python calibrate_league.py --league_id 40 --season 2025         # BBL Germany
    python calibrate_league.py --league_id 40 --tier top_domestic   # Force tier
    python calibrate_league.py --all                                 # All leagues seen today
    python calibrate_league.py --league_id 40 --dry_run             # Print only, don't save
"""

import io
import sys
import os
import json
import math
import argparse
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ET_TZ = ZoneInfo("America/New_York")

# ------------------------------------------------------------------
# TIER TEMPLATES
# Sensible defaults for leagues without enough historical data
# ------------------------------------------------------------------
TIER_TEMPLATES = {
    "elite_pro": {
        "_tier": "elite_pro",
        "_tier_desc": "Top professional leagues (NBA, EuroLeague, ACB)",
        "game_duration_mins": 40,
        "pace_pivot": 98.0,
        "eff_pivot": 113.0,
        "regression_factor": 0.96,
        "hca_total_bump": 2.5,
        "pace_delta_weight": 1.4,
        "eff_delta_weight": 0.75,
        "situational": {
            "b2b_penalty_single": -1.5,
            "b2b_penalty_double": -3.0,
            "fatigue_impact_cap": -4.0
        },
        "thresholds": {"mode_a": 8.0, "mode_b": 4.5, "min_edge": 0.0},
    },
    "top_domestic": {
        "_tier": "top_domestic",
        "_tier_desc": "Competitive domestic leagues (BBL, B League, CBA, BNXT)",
        "game_duration_mins": 40,
        "pace_pivot": 78.0,
        "eff_pivot": 108.0,
        "regression_factor": 0.92,
        "hca_total_bump": 3.5,
        "pace_delta_weight": 1.1,
        "eff_delta_weight": 0.7,
        "situational": {
            "b2b_penalty_single": -1.5,
            "b2b_penalty_double": -3.0,
            "fatigue_impact_cap": -4.0
        },
        "thresholds": {"mode_a": 7.0, "mode_b": 4.0, "min_edge": 0.0},
    },
    "second_division": {
        "_tier": "second_division",
        "_tier_desc": "Second-tier domestic leagues",
        "game_duration_mins": 40,
        "pace_pivot": 74.0,
        "eff_pivot": 105.0,
        "regression_factor": 0.88,
        "hca_total_bump": 4.5,
        "pace_delta_weight": 0.9,
        "eff_delta_weight": 0.65,
        "situational": {
            "b2b_penalty_single": -1.0,
            "b2b_penalty_double": -2.0,
            "fatigue_impact_cap": -3.0
        },
        "thresholds": {"mode_a": 7.5, "mode_b": 4.0, "min_edge": 0.0},
    },
    "lower": {
        "_tier": "lower",
        "_tier_desc": "National / regional leagues",
        "game_duration_mins": 40,
        "pace_pivot": 70.0,
        "eff_pivot": 103.0,
        "regression_factor": 0.82,
        "hca_total_bump": 5.5,
        "pace_delta_weight": 0.7,
        "eff_delta_weight": 0.6,
        "situational": {
            "b2b_penalty_single": -1.0,
            "b2b_penalty_double": -2.0,
            "fatigue_impact_cap": -3.0
        },
        "thresholds": {"mode_a": 9.0, "mode_b": 5.0, "min_edge": 0.0},
    },
}

# Known league_id → tier mappings for well-known leagues
KNOWN_TIER_MAP = {
    # Elite
    12:  "elite_pro",   # NBA
    117: "elite_pro",   # ACB Spain
    # Top domestic
    40:  "top_domestic",  # BBL Germany
    56:  "top_domestic",  # B League Japan
    31:  "top_domestic",  # CBA China
    368: "top_domestic",  # BNXT League
    45:  "top_domestic",  # Basket League Greece
    104: "top_domestic",  # Super Ligi Turkey
    198: "top_domestic",  # ABA League
    82:  "top_domestic",  # VTB United League
    72:  "top_domestic",  # Energa Basket Liga Poland
    # Second division
    407: "second_division",  # B2.League Japan
    96:  "second_division",  # Segunda FEB Spain
    34:  "second_division",  # Basketligaen Denmark
    99:  "second_division",  # Superettan Sweden
    68:  "second_division",  # BLNO Norway
    # Lower
    251: "lower",   # CIBACOPA Mexico
    275: "lower",   # Superliga Venezuela
    388: "lower",   # Superliga Albania
}

MIN_GAMES_FOR_DATA = 10   # Minimum finished games to trust derived values


def fetch_season_games(league_id, season):
    """Fetch all finished games for a league+season from api-basketball."""
    try:
        r = requests.get(
            f"{BASE_URL}/games",
            headers=HEADERS,
            params={"league": league_id, "season": season},
            timeout=15,
        )
        all_games = r.json().get("response", [])
        # Only consider finished games with valid scores
        finished = []
        for g in all_games:
            status = g.get("status", {}).get("short", "")
            if status not in ("FT", "AOT"):
                continue
            home_score = g.get("scores", {}).get("home", {}).get("total")
            away_score = g.get("scores", {}).get("away", {}).get("total")
            if home_score is None or away_score is None:
                continue
            finished.append({
                "home": g.get("teams", {}).get("home", {}).get("name"),
                "away": g.get("teams", {}).get("away", {}).get("name"),
                "home_score": int(home_score),
                "away_score": int(away_score),
                "total": int(home_score) + int(away_score),
                "margin": int(home_score) - int(away_score),
            })
        return finished
    except Exception as e:
        print(f"  [API Error] league={league_id} season={season}: {e}")
        return []


def get_current_season(league_id):
    """Try to determine the current season for a league."""
    try:
        r = requests.get(
            f"{BASE_URL}/leagues",
            headers=HEADERS,
            params={"id": league_id},
            timeout=10,
        )
        leagues = r.json().get("response", [])
        if leagues:
            seasons = leagues[0].get("seasons", [])
            if seasons:
                # Pick the most recent season
                return sorted(seasons, key=lambda s: s.get("season", 0))[-1].get("season")
    except Exception:
        pass
    # Fallback: current year or year - 1
    now = datetime.now(ET_TZ)
    return now.year if now.month >= 9 else now.year - 1


def derive_params(games, league_id, league_name="Unknown"):
    """
    Derive calibration params from finished game data.
    Returns a dict of derived parameters + confidence metadata.
    """
    n = len(games)
    if n < MIN_GAMES_FOR_DATA:
        return None  # Not enough data

    totals  = [g["total"]  for g in games]
    margins = [g["margin"] for g in games]

    # --- HCA: mean home margin ---
    hca = sum(margins) / n
    # Clip to reasonable range
    hca = max(0.5, min(8.0, hca))

    # --- Scoring average (pace proxy) ---
    avg_total = sum(totals) / n
    std_total = math.sqrt(sum((t - avg_total) ** 2 for t in totals) / n)

    # --- Pace estimation ---
    # Engine formula: avg_total = ((eff * pace) / 100) * 2
    # Strategy: use tier template pace, back-derive eff from avg_total
    # This ensures derived configs are dimensionally consistent with the engine
    tier_name = KNOWN_TIER_MAP.get(league_id, "top_domestic")
    tier_pace = TIER_TEMPLATES[tier_name]["pace_pivot"]

    # eff = (avg_total * 100) / (2 * pace)
    eff_pivot = (avg_total * 100) / (2 * tier_pace)
    eff_pivot = max(90.0, min(140.0, eff_pivot))

    # Use tier pace as pace_pivot
    pace_pivot = tier_pace

    # --- Regression factor: more data → trust more ---
    regression_factor = min(0.96, 0.50 + 0.46 * (min(n, 100) / 100))
    regression_factor = round(regression_factor, 3)

    return {
        "n_games": n,
        "avg_total": round(avg_total, 1),
        "std_total": round(std_total, 1),
        "hca": round(hca, 2),
        "pace_pivot": round(pace_pivot, 1),
        "eff_pivot": round(eff_pivot, 1),
        "regression_factor": regression_factor,
    }


def build_config(league_id, league_name, derived, tier_name):
    """
    Build a full engine config dict, starting from the tier template
    and overriding with derived values where available.
    """
    template = dict(TIER_TEMPLATES[tier_name])

    config = {
        "name": league_name,
        "_league_id": league_id,
        "_calibrated_at": datetime.now(ET_TZ).strftime("%Y-%m-%d"),
        "_tier": tier_name,
        "_source": "auto-calibrated" if derived else "tier-template",
    }

    # Copy all template fields
    for k, v in template.items():
        if not k.startswith("_"):
            config[k] = v

    # Override with derived values if we have them
    if derived:
        config["hca_total_bump"]    = derived["hca"]
        config["pace_pivot"]        = derived["pace_pivot"]
        config["eff_pivot"]         = derived["eff_pivot"]
        config["regression_factor"] = derived["regression_factor"]
        config["_n_games"]          = derived["n_games"]
        config["_avg_total"]        = derived["avg_total"]
        config["_std_total"]        = derived["std_total"]
        config["_source"]           = "auto-calibrated"

    return config


def calibrate_one(league_id, season=None, force_tier=None, dry_run=False, verbose=True):
    """
    Full calibration pipeline for one league.
    Returns the config dict (and saves it unless dry_run).
    """
    # 1. Get season
    if season is None:
        season = get_current_season(league_id)

    if verbose:
        print(f"\n  League {league_id} | Season {season}")

    # 2. Determine tier
    tier_name = force_tier or KNOWN_TIER_MAP.get(league_id, "top_domestic")
    if verbose:
        print(f"  Tier: {tier_name}")

    # 3. Fetch historical games
    games = fetch_season_games(league_id, season)
    if verbose:
        print(f"  Finished games found: {len(games)}")

    # 4. Derive params (or fall back to template)
    derived = derive_params(games, league_id) if games else None
    if derived:
        if verbose:
            print(f"  Derived: HCA={derived['hca']:+.2f}  Pace={derived['pace_pivot']:.1f}  "
                  f"Eff={derived['eff_pivot']:.1f}  RegF={derived['regression_factor']}")
    else:
        if verbose:
            print(f"  Insufficient data ({len(games)} games < {MIN_GAMES_FOR_DATA}) — using tier template")

    # 5. Determine league name
    league_name = f"League-{league_id}"
    try:
        r = requests.get(f"{BASE_URL}/leagues", headers=HEADERS, params={"id": league_id}, timeout=8)
        leagues = r.json().get("response", [])
        if leagues:
            league_name = leagues[0].get("name", league_name)
    except Exception:
        pass

    # 6. Build config
    config = build_config(league_id, league_name, derived, tier_name)

    # 7. Save
    if not dry_run:
        os.makedirs("configs/leagues", exist_ok=True)
        out_path = f"configs/leagues/{league_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        if verbose:
            print(f"  Saved -> {out_path}")
    else:
        if verbose:
            print(f"  [DRY RUN] Would save configs/leagues/{league_id}.json")
            print(json.dumps(config, indent=2))

    return config


def calibrate_all_from_today(dry_run=False):
    """
    Calibrate all leagues that appeared in today's fixture fetch.
    Reads from the most recent data/api_basketball_today_*.json file.
    """
    from glob import glob
    files = sorted(glob("data/api_basketball_today_*.json"), reverse=True)
    if not files:
        print("No today's fixture file found. Run explore_api_basketball_today.py first.")
        return

    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)

    leagues = data.get("leagues_summary", [])
    print(f"\nCalibrating {len(leagues)} leagues from {files[0]}...")
    print("=" * 60)

    results = []
    for entry in leagues:
        lid = entry["league_id"]
        name = entry["league_name"]
        print(f"\n[{lid}] {name}")
        try:
            cfg = calibrate_one(lid, dry_run=dry_run, verbose=True)
            results.append({"league_id": lid, "name": name, "status": "ok",
                            "source": cfg.get("_source"), "tier": cfg.get("_tier")})
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"league_id": lid, "name": name, "status": "error", "error": str(e)})

    print("\n" + "=" * 60)
    print(f"Done. {sum(1 for r in results if r['status']=='ok')}/{len(results)} leagues calibrated.")
    return results


def main():
    parser = argparse.ArgumentParser(description="Auto-calibrate basketball league configs")
    parser.add_argument("--league_id", type=int, help="Single league ID to calibrate")
    parser.add_argument("--season",    type=int, help="Season year (default: auto-detect)")
    parser.add_argument("--tier",      choices=list(TIER_TEMPLATES.keys()), help="Force a tier template")
    parser.add_argument("--all",       action="store_true", help="Calibrate all leagues from today's fixture file")
    parser.add_argument("--dry_run",   action="store_true", help="Print config without saving")
    parser.add_argument("--list_tiers", action="store_true", help="Show all tier templates and exit")
    args = parser.parse_args()

    if args.list_tiers:
        for name, tmpl in TIER_TEMPLATES.items():
            print(f"\n[{name}] {tmpl['_tier_desc']}")
            print(f"  HCA: {tmpl['hca_total_bump']}  Pace: {tmpl['pace_pivot']}  "
                  f"Eff: {tmpl['eff_pivot']}  Regression: {tmpl['regression_factor']}")
        return

    if not API_KEY:
        print("ERROR: API_BASKETBALL_KEY not set in .env")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  LEAGUE AUTO-CALIBRATOR")
    print("=" * 60)

    if args.all:
        calibrate_all_from_today(dry_run=args.dry_run)
    elif args.league_id:
        calibrate_one(
            league_id=args.league_id,
            season=args.season,
            force_tier=args.tier,
            dry_run=args.dry_run,
            verbose=True,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
