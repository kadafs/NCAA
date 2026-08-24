"""
patch_corners_today.py
───────────────────────
Reads today's existing prediction JSON and injects corners/booking predictions
from local team_profiles_*.json files. Zero API calls required.

Usage:
    python patch_corners_today.py
    python patch_corners_today.py --date 2026-08-24
"""

import os, sys, json, argparse, glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from build_corner_booking_profiles import corners_prediction

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "football")


def load_all_profiles() -> tuple[dict[int, dict], dict[str, dict]]:
    """
    Returns:
        profiles_by_league: {league_id: {team_id_str: profile_dict}}
        name_to_profile:    {team_name_lower: profile_dict}  (global lookup)
    """
    profiles_by_league: dict[int, dict] = {}
    name_to_profile: dict[str, dict] = {}

    for fpath in glob.glob(os.path.join(DATA_DIR, "team_profiles_*.json")):
        try:
            lid_str = os.path.basename(fpath).replace("team_profiles_", "").replace(".json", "")
            lid = int(lid_str)
            data = json.load(open(fpath, encoding="utf-8"))
            teams = data.get("teams", {})
            profiles_by_league[lid] = teams
            for tid, prof in teams.items():
                name = prof.get("name", "")
                if name:
                    name_to_profile[name.lower()] = prof
        except Exception:
            continue

    print(f"Loaded profiles for {len(profiles_by_league)} league(s), "
          f"{len(name_to_profile)} teams total.")
    return profiles_by_league, name_to_profile


def find_profile(team_name: str, team_id, league_id: int,
                 profiles_by_league: dict, name_to_profile: dict):
    """
    Look up a team profile using (in priority order):
    1. Direct team_id lookup within the league's profiles
    2. Exact name match in global name lookup
    3. Partial name match (contains)
    """
    # 1. Direct ID match within league
    league_profiles = profiles_by_league.get(league_id, {})
    if team_id:
        prof = league_profiles.get(str(team_id))
        if prof:
            return prof

    # 2. Exact name match
    name_lower = team_name.lower()
    prof = name_to_profile.get(name_lower)
    if prof:
        return prof

    # 3. Partial match — team name contains or is contained by profile name
    for pname, prof in name_to_profile.items():
        if pname in name_lower or name_lower in pname:
            return prof

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.utcnow().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    pred_path = os.path.join(DATA_DIR, f"universal_predictions_{args.date}.json")
    if not os.path.exists(pred_path):
        print(f"No predictions file found for {args.date}: {pred_path}")
        return

    profiles_by_league, name_to_profile = load_all_profiles()
    if not name_to_profile:
        print("No team profiles found. Run build_corner_booking_profiles.py first.")
        return

    with open(pred_path, encoding="utf-8") as f:
        payload = json.load(f)

    predictions = payload.get("predictions", [])
    patched = already_had = skipped = 0

    for game in predictions:
        if game.get("corners"):
            already_had += 1
            continue

        lid        = game.get("league_id")
        home_name  = game.get("home_team", "")
        away_name  = game.get("away_team", "")
        home_id    = game.get("home_team_id")
        away_id    = game.get("away_team_id")

        home_profile = find_profile(home_name, home_id, lid, profiles_by_league, name_to_profile)
        away_profile = find_profile(away_name, away_id, lid, profiles_by_league, name_to_profile)

        corner_data = corners_prediction(home_profile, away_profile)
        if corner_data:
            game["corners"] = corner_data
            patched += 1
        else:
            skipped += 1

    with open(pred_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f"\n✅ Patch complete for {args.date}:")
    print(f"   {patched:>4} games patched with corners/booking data")
    print(f"   {already_had:>4} already had corners data")
    print(f"   {skipped:>4} skipped (no matching profile for their league)")


if __name__ == "__main__":
    main()
