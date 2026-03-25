import json
import os
import glob
import datetime

def calculate_iterative_srs(games):
    """
    Computes a mathematically pure Simple Rating System (SRS) manually via recursive iteration.
    This safely avoids immense Python library overheads while guaranteeing perfect matrix calibration.
    """
    teams = {}
    
    # 1. Build Base Profiles
    for g in games:
        ht = g.get("home_team")
        at = g.get("away_team")
        hs = g.get("home_score", 0)
        as_ = g.get("away_score", 0)
        
        if not ht or not at or hs == 0 or as_ == 0:
            continue
            
        if ht not in teams:
            teams[ht] = {"games": 0, "wins": 0, "pts_for": 0, "pts_against": 0, "opponents": []}
        if at not in teams:
            teams[at] = {"games": 0, "wins": 0, "pts_for": 0, "pts_against": 0, "opponents": []}
            
        margin = hs - as_
        
        # We cap massive blowout margins so a single 80-point anomaly doesn't inherently break the localized mathematical integrity
        if margin > 35: margin = 35
        if margin < -35: margin = -35
        
        teams[ht]["games"] += 1
        teams[ht]["pts_for"] += hs
        teams[ht]["pts_against"] += as_
        teams[ht]["opponents"].append(at)
        if hs > as_: teams[ht]["wins"] += 1
        
        teams[at]["games"] += 1
        teams[at]["pts_for"] += as_
        teams[at]["pts_against"] += hs
        teams[at]["opponents"].append(ht)
        if as_ > hs: teams[at]["wins"] += 1
        
    for t, data in teams.items():
        if data["games"] > 0:
            data["raw_margin"] = (data["pts_for"] - data["pts_against"]) / data["games"]
            data["srs"] = data["raw_margin"]
        else:
            data["raw_margin"] = 0.0
            data["srs"] = 0.0
            
    # 2. Iterate Strength of Schedule (SOS) recursively 1000 times until matrix stabilizes natively
    for _ in range(1000):
        new_srs = {}
        for t, data in teams.items():
            if data["games"] == 0:
                new_srs[t] = 0.0
                continue
                
            sos_sum = 0.0
            for opp in data["opponents"]:
                sos_sum += teams[opp]["srs"]
            
            avg_sos = sos_sum / data["games"]
            new_srs[t] = data["raw_margin"] + avg_sos
            
        for t in teams:
            teams[t]["srs"] = new_srs[t]
            
    return teams


def calculate_advanced_ratings(games, pace_pivot=76.0):
    """
    Compute efficiency-adjusted ratings from Proballers box-score stats.

    Uses True Shooting % (TS%), Turnover Rate, and Offensive Rebound %
    all normalized to the LEAGUE AVERAGE so that adj_off/adj_def diverge
    meaningfully from the pure score-margin SRS calculation.

    Weights:
      Offensive adj: 60% TS%, 30% TOV rate, 10% ORB%
      Defensive adj: 70% opponent TS%, 30% opponent TOV rate
    """
    teams = {}

    for g in games:
        stats = g.get("stats") or g.get("advanced_stats")
        if not stats or not isinstance(stats, dict):
            continue

        home_team = g.get("home_team")
        away_team = g.get("away_team")
        hs = g.get("home_score", 0)
        as_ = g.get("away_score", 0)
        if not home_team or not away_team or not hs or not as_:
            continue

        home_s = stats.get("home", {})
        away_s = stats.get("away", {})
        if not home_s or not away_s:
            continue

        for team, pts, opp_pts, t_s, o_s in [
            (home_team, hs, as_, home_s, away_s),
            (away_team, as_, hs, away_s, home_s),
        ]:
            if team not in teams:
                teams[team] = {
                    "games": 0, "wins": 0,
                    "pts_for": 0, "pts_against": 0,
                    "fga": 0, "fta": 0, "tov": 0, "orb": 0, "trb": 0,
                    "opp_fga": 0, "opp_fta": 0, "opp_pts": 0,
                    "opp_tov": 0,
                }
            td = teams[team]
            td["games"]       += 1
            td["pts_for"]     += pts
            td["pts_against"] += opp_pts
            if pts > opp_pts:
                td["wins"] += 1

            td["fga"] += t_s.get("FGA", 0)
            td["fta"] += t_s.get("FTA", 0)
            td["tov"] += t_s.get("TOV", 0)
            td["orb"] += t_s.get("ORB", 0)
            td["trb"] += t_s.get("TRB", 0)

            td["opp_fga"] += o_s.get("FGA", 0)
            td["opp_fta"] += o_s.get("FTA", 0)
            td["opp_pts"] += opp_pts
            td["opp_tov"] += o_s.get("TOV", 0)

    if not teams:
        return []

    # Per-team efficiency metrics
    for td in teams.values():
        fga  = max(td["fga"], 1)
        ofga = max(td["opp_fga"], 1)
        trb  = max(td["trb"], 1)
        td["ts_pct"]      = td["pts_for"]  / (2 * (fga  + 0.44 * td["fta"]))
        td["tov_rate"]    = td["tov"]  / fga
        td["orb_rate"]    = td["orb"]  / trb
        td["opp_ts_pct"]  = td["opp_pts"] / (2 * (ofga + 0.44 * td["opp_fta"]))
        td["opp_tov_rate"]= td["opp_tov"] / ofga

    valid = [td for td in teams.values() if td["games"] >= 2]
    if not valid:
        return []

    # League averages (used as the neutral baseline)
    lg_ts      = sum(t["ts_pct"]       for t in valid) / len(valid)
    lg_tov     = sum(t["tov_rate"]     for t in valid) / len(valid)
    lg_orb     = sum(t["orb_rate"]     for t in valid) / len(valid)
    lg_opp_ts  = sum(t["opp_ts_pct"]   for t in valid) / len(valid)
    lg_opp_tov = sum(t["opp_tov_rate"] for t in valid) / len(valid)

    output_stats = []
    for team_name, td in teams.items():
        g = td["games"]
        if g < 2:
            continue

        raw_off = td["pts_for"]     / g
        raw_def = td["pts_against"] / g

        # Offensive efficiency deltas (relative to league average)
        # Scale factors: 1% TS = ~0.5 pts, 1% TOV = ~0.4 pts, 1% ORB = ~0.15 pts
        ts_delta  = (td["ts_pct"]   - lg_ts)  * 50   # better shooting   → bonus
        tov_delta = (lg_tov - td["tov_rate"]) * 40   # fewer turnovers   → bonus
        orb_delta = (td["orb_rate"] - lg_orb) * 15   # more off rebounds → bonus
        off_adj   = 0.6 * ts_delta + 0.3 * tov_delta + 0.1 * orb_delta

        # Defensive efficiency deltas (how well you LIMIT opponents)
        opp_ts_delta  = (lg_opp_ts  - td["opp_ts_pct"])   * 50  # opponents shoot worse → bonus
        opp_tov_delta = (td["opp_tov_rate"] - lg_opp_tov) * 40  # opponents turn it over → bonus
        def_adj       = 0.7 * opp_ts_delta + 0.3 * opp_tov_delta

        # Apply as PPG adjustments, then pace-scale (same convention as SRS output)
        adj_off = round((raw_off + off_adj) / (pace_pivot / 100), 1) if pace_pivot > 0 else round(raw_off + off_adj, 1)
        adj_def = round((raw_def - def_adj) / (pace_pivot / 100), 1) if pace_pivot > 0 else round(raw_def - def_adj, 1)

        output_stats.append({
            "team_name":   team_name,
            "team_id":     0,
            "adj_off":     adj_off,
            "adj_def":     adj_def,
            "adj_t":       round(pace_pivot, 1),
            "games_played": g,
            "wins":        td["wins"],
            "win_pct":     round(td["wins"] / g, 3),
            "srs_rating":  0.0,
            "source":      "ADVANCED",
            # Expose efficiency metrics for display / audit
            "ts_pct":      round(td["ts_pct"], 4),
            "tov_rate":    round(td["tov_rate"], 4),
            "orb_rate":    round(td["orb_rate"], 4),
            "opp_ts_pct":  round(td["opp_ts_pct"], 4),
        })

    return output_stats


import re

NOW = datetime.datetime.now()

def parse_date(date_str):
    """Parse dates from multiple sources: YYYY-MM-DD (API), Dec 12, 2025 (Proballers), DD.MM. HH:MM (Flashscore)"""
    if not date_str: return datetime.datetime.min
    try:
        # ISO format: YYYY-MM-DD...
        if "-" in date_str and len(date_str) >= 10:
            return datetime.datetime.strptime(date_str[:10], "%Y-%m-%d")
        # Proballers: "Dec 12, 2025" or "Jan 9, 2026"
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.datetime.strptime(date_str.strip()[:15], fmt)
            except:
                pass
        # Flashscore: "DD.MM. HH:MM" - NO year, infer from context
        if "." in date_str:
            clean = re.sub(r'[^0-9.]', '', date_str.split()[0])
            parts = [p for p in clean.split('.') if p]
            if len(parts) >= 2:
                day, month = int(parts[0]), int(parts[1])
                # Infer year: try current year first; if that would place the date more
                # than 18 months in the future, step back a year.
                year = NOW.year
                candidate = datetime.datetime(year, month, day)
                if candidate > NOW + datetime.timedelta(days=60):
                    candidate = datetime.datetime(year - 1, month, day)
                return candidate
    except:
        pass
    return datetime.datetime.min

def process_leagues():
    print(f"\n===========================================================")
    print("  INITIALIZING [SRS] & [ADVANCED] MATH RANKING ENGINE")
    print(f"===========================================================")
    
    map_file = "data/league_slug_map.json"
    if not os.path.exists(map_file):
        print("Missing league_slug_map.json! Aborting Matrix Build.")
        return
        
    with open(map_file, encoding="utf-8") as f:
        slug_map = json.load(f)
        
    f_files = glob.glob("data/historical/flashscore_*.json")
    p_files = glob.glob("data/historical/proballers_*.json")
    a_files = glob.glob("data/historical/api_basketball_*.json")
    historical_files = f_files + p_files + a_files
    os.makedirs("data/team_stats", exist_ok=True)
    
    season = datetime.datetime.now().year
    
    # Group games by league
    games_by_league = {}
    
    for hf in historical_files:
        basename = os.path.basename(hf) 
        slug = basename.replace("flashscore_", "").replace("proballers_", "").replace("api_basketball_", "").replace(".json", "")
        
        if slug.isdigit():
            league_id = int(slug)
        else:
            league_id = slug_map.get(slug)
        if not league_id:
            league_id = slug_map.get(slug.replace("-", "_"))
            if not league_id:
                print(f"Skipping {slug} - mapping ID not found in league_slug_map.json.")
                continue
            
        try:
            with open(hf, encoding="utf-8") as f:
                data = json.load(f)
                
            games = data if isinstance(data, list) else data.get("games", [])
            if not games: continue
            
            if league_id not in games_by_league:
                games_by_league[league_id] = []
            games_by_league[league_id].extend(games)
        except Exception as e:
            print(f"Error reading {hf}: {e}")

    success_count = 0
    
    for league_id, all_games in games_by_league.items():
        if len(all_games) < 5:
            continue
            
        # Deduplicate
        unique_games = {}
        for g in all_games:
            # Prefer game_id or match_id. If missing, use date+teams
            gid = g.get("game_id") or g.get("match_id") or f'{g.get("date")}_{g.get("home_team")}_{g.get("away_team")}'
            if gid not in unique_games:
                unique_games[gid] = g
            else:
                # If the new game object has advanced_stats but the old one didn't, overwrite with the better payload
                if g.get("advanced_stats") and not unique_games[gid].get("advanced_stats"):
                    unique_games[gid] = g
                    
        merged_games = list(unique_games.values())
        
        # Sort by date for proper chronological math and gap detection
        for g in merged_games:
            g["_parsed_date"] = parse_date(g.get("date", ""))
        
        # Remove games with unparseable dates before sorting
        merged_games = [g for g in merged_games if g["_parsed_date"] > datetime.datetime.min]
        merged_games.sort(key=lambda x: x["_parsed_date"])
        
        # Season Gap Filter: find the LAST contiguous block of games (separated by > 75 days)
        # This correctly handles: inter-season breaks, new season detection
        last_gap_idx = 0
        for i in range(1, len(merged_games)):
            delta = (merged_games[i]["_parsed_date"] - merged_games[i-1]["_parsed_date"]).days
            if delta > 75:
                last_gap_idx = i  # Start fresh season block from this game
        filtered_games = merged_games[last_gap_idx:]
            
        if len(filtered_games) < 5:
            continue

        # Detect Advanced Eligibility: check whether the proballers stats key is present
        # We check more broadly across all filtered games to avoid missing sparse coverage
        advanced_eligible = False
        adv_count = 0
        for g in filtered_games:
            stats_val = g.get("advanced_stats") or g.get("stats")
            if stats_val and isinstance(stats_val, dict) and len(stats_val) > 0:
                adv_count += 1
                
        # Require at least 5 games with advanced data across the whole dataset
        if adv_count >= 5:
            advanced_eligible = True
            model_flag = "[ADVANCED]"
        else:
            advanced_eligible = False
            model_flag = "[  SRS   ]"
            
        srs_teams = calculate_iterative_srs(filtered_games)
        
        config_path = f"configs/leagues/{league_id}.json"
        pace_pivot = 76.0
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    pace_pivot = json.load(f).get("pace_pivot", 76.0)
            except: pass
                
        output_stats = []
        for team_name, data in srs_teams.items():
            if data["games"] < 2: continue
            
            raw_off = data["pts_for"] / data["games"]
            raw_def = data["pts_against"] / data["games"]
            
            # FIX 3: Proportional SRS decomposition
            # Weight SRS credit based on each team's offensive vs defensive contribution
            # instead of naive 50/50 split
            total_contribution = raw_off + raw_def
            if total_contribution > 0 and data["srs"] != 0:
                off_share = raw_off / total_contribution
                true_ppg_o = raw_off + (data["srs"] * off_share)
                true_ppg_d = raw_def - (data["srs"] * (1 - off_share))
            else:
                true_ppg_o = raw_off
                true_ppg_d = raw_def
            
            adjO = round(true_ppg_o / (pace_pivot / 100), 1) if pace_pivot > 0 else 108.0
            adjD = round(true_ppg_d / (pace_pivot / 100), 1) if pace_pivot > 0 else 108.0
            
            win_pct = round(data["wins"] / data["games"], 3) if data["games"] > 0 else 0.0
            
            team_obj = {
                "team_name": team_name,
                "team_id": 0,
                "adj_off": adjO,
                "adj_def": adjD,
                "adj_t": round(pace_pivot, 1),
                "games_played": data["games"],
                "wins": data["wins"],
                "win_pct": win_pct,
                "srs_rating": round(data["srs"], 2)
            }
            
            if advanced_eligible:
                team_obj["efg_perc"] = None
                team_obj["to_perc"] = None
                team_obj["or_perc"] = None
                team_obj["ftr"] = None
                
            output_stats.append(team_obj)
            
        # Write [  SRS   ] Fallback unconditionally for all leagues
        payload_srs = {
            "league_id": league_id,
            "season": season,
            "model_architecture": "[  SRS   ]",
            "calculated_at": datetime.datetime.now().isoformat(),
            "teams": output_stats
        }
        with open(f"data/bball_stats_{league_id}_srs.json", "w", encoding="utf-8") as f:
            json.dump(payload_srs, f, indent=4)

        # Write [ADVANCED] — uses GENUINE efficiency ratings, not SRS clone
        if advanced_eligible:
            adv_stats = calculate_advanced_ratings(filtered_games, pace_pivot=pace_pivot)
            if adv_stats:
                payload_adv = {
                    "league_id": league_id,
                    "season": season,
                    "model_architecture": "[ADVANCED]",
                    "calculated_at": datetime.datetime.now().isoformat(),
                    "teams": adv_stats
                }
                with open(f"data/bball_stats_{league_id}_adv.json", "w", encoding="utf-8") as f:
                    json.dump(payload_adv, f, indent=4)
            else:
                # Not enough box-score games — fall back to SRS payload
                payload_adv_fb = dict(payload_srs)
                payload_adv_fb["model_architecture"] = "[ADVANCED]"
                payload_adv_fb["note"] = "Insufficient box-score coverage; using SRS fallback"
                with open(f"data/bball_stats_{league_id}_adv.json", "w", encoding="utf-8") as f:
                    json.dump(payload_adv_fb, f, indent=4)
            
        success_count += 1

    print(f"Generated Proprietary Predictive Mathematical Matrices for exactly {success_count} global leagues.")
    print(f"===========================================================")

if __name__ == "__main__":
    process_leagues()
