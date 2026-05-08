import json
import os
import glob
import datetime

# Cross-source canonical name map — applied BEFORE fuzzy normalization.
# Resolves cases where API and Proballers use different names for the same club,
# which would otherwise create two separate ghost entries in the matrix.
# Key = API name, Value = Proballers (canonical) name.
CROSS_SOURCE_CANONICAL_MAP = {
    # Iceland Premier League
    "KR Basket":           "KR Reykjavik",
    # Poland Energa Basket Liga (72)
    "Dabrowa Gornicza":    "MKS Dąbrowa Górnicza",
    "Zielona Gora":        "Enea Zastal Zielona Góra",
    "Torun":               "Twarde Pierniki Toruń",
    "Gornik Walbrzych":    "Górnik Trans.eu Walbrzych",
    "Ostrow Wielkopolski": "Stal Ostrów Wielkopolski",
    # European / International
    "Unicaja":             "Unicaja Malaga",
    "Unics Kazan":         "UNICS Kazan",
    "Ulm":                 "Ratiopharm Ulm",
    "Utsunomiya Brex":     "Utsunomiya",
    "Vaerlose":            "Vaerlose Blue Hawks",
    # Australia NBL1 (Official Sportradar -> API Basketball)
    "Hobart":                      "Hobart Chargers",
    "Southern Districts":          "Southern District Spartans",
    "Southern District":           "Southern District Spartans",
    "SW Slammers":                 "South West Slammers",
    "SW Metro":                    "South West Metro Pirates",
    "Albury Wodonga":              "Albury-Wodonga Bandits",
    "Albury W":                    "Albury-Wodonga Bandits",
    "Manly Warringah":             "Manly Warringah Sea Eagles",
    "Manly W.":                    "Manly Warringah Sea Eagles",
    "Manly W. W":                  "Manly Warringah Sea Eagles",
    "Hornsby KuRingGai":           "Hornsby Ku-Ring-Gai Spiders",
    "Hornsby S.":                  "Hornsby Ku-Ring-Gai Spiders",
    "Hornsby S. W":                "Hornsby Ku-Ring-Gai Spiders",
    "Northern Force":              "Northern Tasmania",
    "Eastern Suns":                "Kalamunda Eastern Suns",
    "Brisbane":                    "Brisbane Capitals",
    "North Adelaide":              "North Adelaide Rockets",
    "Central Districts":           "Central District Lions",
    "Sunshine Coast":              "Sunshine Coast Phoenix",
    "North Gold Coast":            "North Gold Coast Seahawks",
    "Beeliar Boodjar":             "Cockburn Cougars",
    "Cockburn Cougars":            "Cockburn Cougars",
    "Mandurah Magic":              "Mandurah Magic",
    "Warwick Senators":            "Warwick Senators",
    "Willetton Tigers":            "Willetton Tigers",
    "Lakeside Lightning":          "Lakeside Lightning",
    "Perry Lakes Hawks":           "Perry Lakes Hawks",
    "Rockingham Flames":           "Rockingham Flames",
    "Joondalup Wolves":            "Joondalup Wolves",
    "Geraldton Buccaneers":        "Geraldton Buccaneers",
    "Goldfields Giants":           "Goldfields Giants",
    "Perth Redbacks":              "Perth Redbacks",
    "East Perth Eagles":           "East Perth Eagles",
    "Forestville":                 "Forestville Eagles",
    "Sturt":                       "Sturt Sabres",
    "Mavericks":                   "Eastern Mavericks",
    "Norths":                      "Norths Bears",
    "Sutherland":                  "Sutherland Sharks",
    "Sydney":                      "Sydney Comets",
    "Penrith":                     "Penrith Panthers",
    "Penrith P.":                  "Penrith Panthers",
    "Penrith P. W":                "Penrith Panthers",
    "Maitland":                    "Maitland Mustangs",
    "Maitland M.":                  "Maitland Mustangs",
    "Hills":                       "Hills Hornets",
    # NBL1 South (209/210)
    "Nunawading Spectres":         "Nunawading Spectres",
    "Frankston Blues":             "Frankston Blues",
    "Geelong United":              "Geelong United",
    "Kilsyth Cobras":              "Kilsyth Cobras",
    "Ballarat Miners":             "Ballarat Miners",
    "Dandenong Rangers":           "Dandenong Rangers",
    "Diamond Valley Eagles":       "Diamond Valley Eagles",
    "Eltham Wildcats":             "Eltham Wildcats",
    "Knox Raiders":                "Knox Raiders",
    "Ringwood Hawks":              "Ringwood Hawks",
    "Waverley Falcons":            "Waverley Falcons",
}

def calculate_iterative_srs(games):
    """
    Computes a mathematically pure Simple Rating System (SRS) manually via recursive iteration.
    This safely avoids immense Python library overheads while guaranteeing perfect matrix calibration.
    """
    import math
    import datetime
    teams = {}
    
    if not games: return teams
        
    # Get the "current" date relative to the dataset
    max_date = max((g.get("_parsed_date", datetime.datetime.min) for g in games), default=datetime.datetime.now())
    if max_date == datetime.datetime.min:
        max_date = datetime.datetime.now()
    
    # 1. Build Base Profiles
    for g in games:
        ht = g.get("home_team")
        at = g.get("away_team")
        hs = g.get("home_score", 0)
        as_ = g.get("away_score", 0)
        
        if not ht or not at or not hs or not as_:
            continue
            
        g_date = g.get("_parsed_date", max_date)
        if g_date == datetime.datetime.min: 
            g_date = max_date
            
        days_old = (max_date - g_date).days
        
        # Time Decay: 14-day plateau, λ=0.030, hard cutoff at ~168 days.
        # Games within 14 days = full weight (authoritative recent form).
        # Exponential decay after that: Jan game in April ≈ 9%, Oct game ≈ 1%.
        # Games older than ~168 days (weight < 1%) are excluded entirely —
        # they pre-date the current season and have zero predictive value.
        weight = 1.0
        if days_old > 14:
            weight = math.exp(-0.030 * (days_old - 14))
        if weight < 0.01:
            continue  # Hard cutoff — game too old to contribute meaningfully
        
        if ht not in teams:
            teams[ht] = {"games": 0, "weight_sum": 0.0, "wins": 0, "pts_for": 0, "pts_against": 0, "scaled_margin_sum": 0.0, "opponents": [], "game_totals": []}
        if at not in teams:
            teams[at] = {"games": 0, "weight_sum": 0.0, "wins": 0, "pts_for": 0, "pts_against": 0, "scaled_margin_sum": 0.0, "opponents": [], "game_totals": []}
            
        raw_margin = hs - as_
        
        # True HCA Stripping: Subtract 2.5 from home team's margin
        ht_margin = raw_margin - 2.5
        at_margin = -raw_margin + 2.5
        
        # Logarithmic Blowout Scaling
        def scale_margin(m):
            sign = 1 if m >= 0 else -1
            abs_m = abs(m)
            if abs_m <= 12: return float(m)
            return sign * (12.0 + 4.0 * math.log(abs_m - 11.0))
            
        ht_scaled_margin = scale_margin(ht_margin)
        at_scaled_margin = scale_margin(at_margin)
        
        teams[ht]["games"] += 1
        teams[ht]["weight_sum"] += weight
        teams[ht]["pts_for"] += (hs * weight)
        teams[ht]["pts_against"] += (as_ * weight)
        teams[ht]["scaled_margin_sum"] += (ht_scaled_margin * weight)
        teams[ht]["opponents"].append((at, weight))
        teams[ht]["game_totals"].append(hs + as_)
        if hs > as_: teams[ht]["wins"] += 1
        
        teams[at]["games"] += 1
        teams[at]["weight_sum"] += weight
        teams[at]["pts_for"] += (as_ * weight)
        teams[at]["pts_against"] += (hs * weight)
        teams[at]["scaled_margin_sum"] += (at_scaled_margin * weight)
        teams[at]["opponents"].append((ht, weight))
        teams[at]["game_totals"].append(hs + as_)
        if as_ > hs: teams[at]["wins"] += 1
        
    for t, data in teams.items():
        if data["weight_sum"] > 0:
            data["raw_margin"] = data["scaled_margin_sum"] / data["weight_sum"]
            data["srs"] = data["raw_margin"]
        else:
            data["raw_margin"] = 0.0
            data["srs"] = 0.0
            
    # 2. Iterate Strength of Schedule (SOS) recursively 1000 times until matrix stabilizes natively
    for _ in range(1000):
        new_srs = {}
        for t, data in teams.items():
            if data["weight_sum"] == 0:
                new_srs[t] = 0.0
                continue
                
            sos_sum = 0.0
            for opp_name, opp_weight in data["opponents"]:
                sos_sum += (teams[opp_name]["srs"] * opp_weight)
            
            avg_sos = sos_sum / data["weight_sum"]
            new_srs[t] = data["raw_margin"] + avg_sos
            
        for t in teams:
            teams[t]["srs"] = new_srs[t]
            
    return teams


def calculate_advanced_ratings(games, pace_pivot=76.0):
    """
    Compute efficiency-adjusted ratings from Proballers box-score stats.
    Integrates True Four Factors (eFG/TS%, TOV%, ORB/DRB%, FTR) + Time Decay Bias.
    """
    import math
    import datetime
    teams = {}
    if not games: return []
    
    max_date = max((g.get("_parsed_date", datetime.datetime.min) for g in games), default=datetime.datetime.now())
    if max_date == datetime.datetime.min: max_date = datetime.datetime.now()

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
            
        g_date = g.get("_parsed_date", max_date)
        if g_date == datetime.datetime.min: g_date = max_date
        days_old = (max_date - g_date).days
        weight = 1.0
        if days_old > 21:
            weight = math.exp(-0.015 * (days_old - 21))

        for team, pts, opp_pts, t_s, o_s in [
            (home_team, hs, as_, home_s, away_s),
            (away_team, as_, hs, away_s, home_s),
        ]:
            if team not in teams:
                teams[team] = {
                    "games": 0, "weight_sum": 0.0, "wins": 0,
                    "pts_for": 0, "pts_against": 0, "game_totals": [],
                    "fga": 0, "fta": 0, "tov": 0, "orb": 0, "drb": 0, "trb": 0,
                    "opp_fga": 0, "opp_fta": 0, "opp_pts": 0,
                    "opp_tov": 0, "opp_orb": 0,
                }
            td = teams[team]
            td["games"]       += 1
            td["weight_sum"]  += weight
            td["pts_for"]     += (pts * weight)
            td["pts_against"] += (opp_pts * weight)
            td["game_totals"].append(pts + opp_pts)
            if pts > opp_pts:
                td["wins"] += 1

            def get_stat(s_dict, key):
                # Try uppercase first (Proballers), then lowercase (NBL1)
                return s_dict.get(key.upper(), s_dict.get(key.lower(), 0))

            td["fga"] += (get_stat(t_s, "FGA") * weight)
            td["fta"] += (get_stat(t_s, "FTA") * weight)
            td["tov"] += (get_stat(t_s, "TOV") * weight)
            td["orb"] += (get_stat(t_s, "ORB") * weight)
            
            # Handle DRB/TRB logic with case-insensitivity
            t_drb = get_stat(t_s, "DRB")
            t_trb = get_stat(t_s, "TRB")
            t_orb = get_stat(t_s, "ORB")
            if not t_drb and t_trb:
                t_drb = max(0, t_trb - t_orb)
            td["drb"] += (t_drb * weight)
            td["trb"] += (t_trb * weight)

            td["opp_fga"] += (get_stat(o_s, "FGA") * weight)
            td["opp_fta"] += (get_stat(o_s, "FTA") * weight)
            td["opp_pts"] += (opp_pts * weight)
            td["opp_tov"] += (get_stat(o_s, "TOV") * weight)
            td["opp_orb"] += (get_stat(o_s, "ORB") * weight)

    if not teams:
        return []

    # Per-team efficiency metrics
    for td in teams.values():
        fga  = max(td["fga"], 0.001)
        ofga = max(td["opp_fga"], 0.001)
        drb_opp = td["drb"] + td["opp_orb"]
        
        td["ts_pct"]   = td["pts_for"]  / (2.0 * (fga  + 0.44 * td["fta"])) if (fga + 0.44 * td["fta"]) > 0 else 0
        td["tov_rate"] = td["tov"]  / fga
        td["orb_rate"] = td["orb"]  / (td["orb"] + max((td["trb"]-td["orb"]), 0.001))
        td["ft_rate"]  = td["fta"] / fga
        td["drb_rate"] = td["drb"] / drb_opp if drb_opp > 0 else 0.5
        
        td["opp_ts_pct"]  = td["opp_pts"] / (2.0 * (ofga + 0.44 * td["opp_fta"])) if (ofga + 0.44 * td["opp_fta"]) > 0 else 0
        td["opp_tov_rate"]= td["opp_tov"] / ofga
        td["opp_ft_rate"] = td["opp_fta"] / ofga

    valid = [td for td in teams.values() if td["weight_sum"] >= 1.5]
    if not valid:
        return []

    # League averages (used as the neutral baseline)
    lg_ts      = sum(t["ts_pct"]       for t in valid) / len(valid)
    lg_tov     = sum(t["tov_rate"]     for t in valid) / len(valid)
    lg_orb     = sum(t["orb_rate"]     for t in valid) / len(valid)
    lg_ftr     = sum(t["ft_rate"]      for t in valid) / len(valid)
    
    lg_opp_ts  = sum(t["opp_ts_pct"]   for t in valid) / len(valid)
    lg_opp_tov = sum(t["opp_tov_rate"] for t in valid) / len(valid)
    lg_drb     = sum(t["drb_rate"]     for t in valid) / len(valid)
    lg_opp_ftr = sum(t["opp_ft_rate"]  for t in valid) / len(valid)

    output_stats = []
    for team_name, td in teams.items():
        w = td["weight_sum"]
        g = td["games"]
        if w < 1.0:
            continue

        raw_off = td["pts_for"]     / w
        raw_def = td["pts_against"] / w

        # True Four Factors Offensive Adjustment
        ts_delta  = (td["ts_pct"]   - lg_ts)  * 60
        tov_delta = (lg_tov - td["tov_rate"]) * 50
        orb_delta = (td["orb_rate"] - lg_orb) * 20
        ftr_delta = (td["ft_rate"]  - lg_ftr) * 15
        off_adj   = 0.40 * ts_delta + 0.25 * tov_delta + 0.20 * orb_delta + 0.15 * ftr_delta

        # True Four Factors Defensive Adjustment
        opp_ts_delta  = (lg_opp_ts  - td["opp_ts_pct"])   * 60
        opp_tov_delta = (td["opp_tov_rate"] - lg_opp_tov) * 50
        drb_delta     = (td["drb_rate"] - lg_drb)         * 20
        opp_ftr_delta = (lg_opp_ftr - td["opp_ft_rate"])  * 15
        def_adj       = 0.40 * opp_ts_delta + 0.25 * opp_tov_delta + 0.20 * drb_delta + 0.15 * opp_ftr_delta

        # Apply as PPG adjustments, then pace-scale (same convention as SRS output)
        adj_off = round((raw_off + off_adj) / (pace_pivot / 100), 1) if pace_pivot > 0 else round(raw_off + off_adj, 1)
        adj_def = round((raw_def - def_adj) / (pace_pivot / 100), 1) if pace_pivot > 0 else round(raw_def - def_adj, 1)

        std_dev_totals = 15.0
        n_totals = len(td["game_totals"])
        if n_totals > 1:
            mean_tot = sum(td["game_totals"]) / n_totals
            variance = sum((x - mean_tot) ** 2 for x in td["game_totals"]) / (n_totals - 1)
            import math
            std_dev_totals = round(math.sqrt(variance), 2)

        output_stats.append({
            "team_name":   team_name,
            "team_id":     0,
            "adj_off":     adj_off,
            "adj_def":     adj_def,
            "adj_t":       round(pace_pivot, 1),
            "std_dev_totals": std_dev_totals,
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
    n_files = glob.glob("data/historical/nbl1_official_*.json")
    historical_files = f_files + p_files + a_files + n_files
    os.makedirs("data/team_stats", exist_ok=True)
    
    season = datetime.datetime.now().year
    
    # Group games by league
    games_by_league = {}
    
    for hf in historical_files:
        basename = os.path.basename(hf) 
        slug = basename.replace("flashscore_", "").replace("proballers_", "").replace("api_basketball_", "").replace("nbl1_official_", "").replace(".json", "")
        
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

    # Also ingest modern daily cache files (data/api_basketball_today_*.json)
    # These contain finalized scores that auto_update_historical.py may not have
    # processed yet, ensuring the SRS matrix is always fully up to date.
    d_files = glob.glob("data/api_basketball_today_*.json")
    for df in d_files:
        try:
            with open(df, encoding="utf-8") as f:
                day_data = json.load(f)
            for entry in day_data.get("leagues_summary", []):
                lid = entry.get("league_id")
                if not lid:
                    continue
                for g in entry.get("games", []):
                    hs = g.get("home_score")
                    as_ = g.get("away_score")
                    if hs is None or as_ is None:
                        continue
                    try:
                        hs = int(hs)
                        as_ = int(as_)
                    except (TypeError, ValueError):
                        continue
                    # Skip awarded/forfeited matches — not real game totals
                    if g.get("status") == "Game Awarded":
                        continue
                    if hs == 0 and as_ == 0:
                        continue
                    if g.get("status") not in ("Game Finished", "Final", "AOT", "FT") and hs == 0 and as_ == 0:
                        continue
                    clean = {
                        "date": str(g.get("time", "") or day_data.get("date", ""))[:10],
                        "home_team": g.get("home", ""),
                        "away_team": g.get("away", ""),
                        "home_score": hs,
                        "away_score": as_,
                        "game_id": f"daily_{g.get('home','')}_{g.get('away','')}_{hs}_{as_}"
                    }
                    if lid not in games_by_league:
                        games_by_league[lid] = []
                    games_by_league[lid].append(clean)
        except Exception as e:
            print(f"Error reading daily cache {df}: {e}")

    success_count = 0
    
    for league_id, all_games in games_by_league.items():
        league_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(league_id))
        if len(all_games) < 5:
            continue
            
        # 1. Parse dates and filter invalid games
        valid_games = []
        for g in all_games:
            pd = parse_date(g.get("date", ""))
            if pd > datetime.datetime.min:
                g["_parsed_date"] = pd
                valid_games.append(g)

        # 1.5. Apply cross-source canonical name mapping BEFORE fuzzy normalization.
        # This ensures games labelled with API names get merged with Proballers games
        # under the canonical (Proballers) name, preventing duplicate ghost entries.
        for g in valid_games:
            if g.get("home_team") in CROSS_SOURCE_CANONICAL_MAP:
                g["home_team"] = CROSS_SOURCE_CANONICAL_MAP[g["home_team"]]
            if g.get("away_team") in CROSS_SOURCE_CANONICAL_MAP:
                g["away_team"] = CROSS_SOURCE_CANONICAL_MAP[g["away_team"]]

        # 2. Normalize team names across all data sources
        import difflib
        team_name_map = {}
        all_names = set()
        for g in valid_games:
            if g.get("home_team"): all_names.add(g.get("home_team"))
            if g.get("away_team"): all_names.add(g.get("away_team"))
            
        sorted_names = sorted(list(all_names), key=len, reverse=True)
        for name in sorted_names:
            matched = False
            name_lower = name.lower()
            for primary in set(team_name_map.values()):
                pri_lower = primary.lower()
                
                # Rule 1: Exact substring overlap (e.g. 'AS Monaco' and 'Monaco')
                if name_lower in pri_lower or pri_lower in name_lower:
                    team_name_map[name] = primary
                    matched = True
                    break
                
                # Rule 2: High character overlap ratio via difflib
                similarity = difflib.SequenceMatcher(None, name_lower, pri_lower).ratio()
                if similarity >= 0.85:
                    team_name_map[name] = primary
                    matched = True
                    break
                    
            if not matched:
                team_name_map[name] = name


        # Apply normalized names
        for g in valid_games:
            g["home_team"] = team_name_map.get(g.get("home_team"), g.get("home_team"))
            g["away_team"] = team_name_map.get(g.get("away_team"), g.get("away_team"))
            
        # 3. Deduplicate using normalized identifiers
        unique_games = {}
        for g in valid_games:
            # Semantic dedupe key: Date + Standardized Home vs Away
            gid = f"{g['_parsed_date'].strftime('%Y-%m-%d')}_{g['home_team']}_{g['away_team']}"
            
            if gid not in unique_games:
                unique_games[gid] = g
            else:
                old_adv = unique_games[gid].get("advanced_stats") or unique_games[gid].get("stats")
                new_adv = g.get("advanced_stats") or g.get("stats")
                if new_adv and not old_adv:
                    unique_games[gid] = g
                    
        merged_games = list(unique_games.values())
        
        # Sort by date for chronological math
        merged_games.sort(key=lambda x: x["_parsed_date"])
        
        # Hard Date Cutoff Filter
        now = datetime.datetime.now()
        cur_year = now.year
        cur_month = now.month
        
        summer_league_ids = {"13", "66", "76", "222", "207", "208", "209", "210", "211", "212", "213", "214", "215", "216"}
        lid_str = str(league_id)
        
        if lid_str in summer_league_ids:
            cutoff_date = datetime.datetime(cur_year, 1, 1)
        else:
            # Global Winter Leagues default
            if cur_month >= 8:
                cutoff_date = datetime.datetime(cur_year, 8, 1)
            else:
                cutoff_date = datetime.datetime(cur_year - 1, 8, 1)
                
        filtered_games = [g for g in merged_games if g["_parsed_date"] >= cutoff_date]
            
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
            
            w = data.get("weight_sum", data["games"])
            if w <= 0.001: continue
            
            raw_off = data["pts_for"] / w
            raw_def = data["pts_against"] / w
            
            # FIX 3: Proportional SRS decomposition
            # Weight SRS credit based on each team's offensive vs defensive contribution
            # instead of naive 50/50 split
            total_contribution = raw_off + raw_def
            if total_contribution > 0 and data.get("srs", 0) != 0:
                off_share = raw_off / total_contribution
                true_ppg_o = raw_off + (data["srs"] * off_share)
                true_ppg_d = raw_def - (data["srs"] * (1 - off_share))
            else:
                true_ppg_o = raw_off
                true_ppg_d = raw_def
            
            adjO = round(true_ppg_o / (pace_pivot / 100), 1) if pace_pivot > 0 else 108.0
            adjD = round(true_ppg_d / (pace_pivot / 100), 1) if pace_pivot > 0 else 108.0
            
            win_pct = round(data["wins"] / data["games"], 3) if data["games"] > 0 else 0.0
            
            std_dev_totals = 15.0
            n_totals = len(data.get("game_totals", []))
            if n_totals > 1:
                mean_tot = sum(data["game_totals"]) / n_totals
                variance = sum((x - mean_tot) ** 2 for x in data["game_totals"]) / (n_totals - 1)
                import math
                std_dev_totals = round(math.sqrt(variance), 2)
            
            team_obj = {
                "team_name": team_name,
                "team_id": 0,
                "adj_off": adjO,
                "adj_def": adjD,
                "adj_t": round(pace_pivot, 1),
                "std_dev_totals": std_dev_totals,
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
        adv_stats = calculate_advanced_ratings(filtered_games, pace_pivot=pace_pivot) if advanced_eligible else []
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
            
            # --- ALGORITHMIC GHOST INJURY DETECTION ---
            if advanced_eligible:
                ghost_injuries = {}
                team_histories = {} 
                # chronologically ordered!
                sorted_games = sorted(filtered_games, key=lambda x: x.get("_parsed_date", datetime.datetime.min))
                
                for g in sorted_games:
                    ht = g.get("home_team")
                    at = g.get("away_team")
                    h_s = g.get("stats", {}).get("home", {})
                    a_s = g.get("stats", {}).get("away", {})
                    
                    for team, stats in [(ht, h_s), (at, a_s)]:
                        if team not in team_histories:
                            team_histories[team] = {"players": {}, "games_total": 0, "last_2_rosters": []}
                        
                        th = team_histories[team]
                        th["games_total"] += 1
                        
                        current_roster = set()
                        players = stats.get("players", [])
                        for p in players:
                            name = p.get("name")
                            pts = p.get("pts", 0)
                            if not name: continue
                            current_roster.add(name)
                            if name not in th["players"]:
                                th["players"][name] = {"games_played": 0, "total_pts": 0}
                            th["players"][name]["games_played"] += 1
                            th["players"][name]["total_pts"] += pts
                            
                        th["last_2_rosters"].append(current_roster)
                        if len(th["last_2_rosters"]) > 2:
                            th["last_2_rosters"].pop(0)
                            
                for team, th in team_histories.items():
                    if th["games_total"] < 5: continue
                    
                    last_2_combined = set()
                    for roster in th["last_2_rosters"]:
                        last_2_combined = last_2_combined.union(roster)
                        
                    injuries = []
                    for name, p in th["players"].items():
                        gp = max(p["games_played"], 1)
                        ppg = p["total_pts"] / gp
                        # Active rotational threshold (played in 30% of season)
                        if gp >= (th["games_total"] * 0.3):
                            if name not in last_2_combined:
                                # They missed the last 2 games!
                                if ppg >= 15.0:
                                    injuries.append({"player": name, "note": f"{name} (Ghost Injury All-Star - {ppg:.1f} PPG)", "status": "Out", "impact": "all_star_out"})
                                elif ppg >= 10.0:
                                    injuries.append({"player": name, "note": f"{name} (Ghost Injury Starter - {ppg:.1f} PPG)", "status": "Out", "impact": "starter_out"})
                                elif ppg >= 6.0:
                                    injuries.append({"player": name, "note": f"{name} (Ghost Injury Bench - {ppg:.1f} PPG)", "status": "Out", "impact": "bench_out"})
                                    
                    if injuries:
                        ghost_injuries[team] = injuries
                        
                with open(f"data/ghost_injuries_{league_id}.json", "w", encoding="utf-8") as f:
                    json.dump(ghost_injuries, f, indent=4)
                    
        success_count += 1

    print(f"Generated Proprietary Predictive Mathematical Matrices for exactly {success_count} global leagues.")
    print(f"===========================================================")

if __name__ == "__main__":
    process_leagues()
