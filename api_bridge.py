import json
import zoneinfo
from datetime import datetime
import predict_advanced
import predict_totals
import predict_conservative
import predict_simple
import predict_props

def get_all_data(target_date=None):
    if target_date:
        try:
            now = datetime.strptime(target_date, "%Y-%m-%d")
        except:
           # Use ET for today's date if none provided
            now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    else:
        # Use ET for today's date if none provided
        now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
        
    year, month, day = now.year, now.month, now.day
    
    # Fetch scoreboard for today
    board = predict_advanced.fetch_scoreboard(year, month, day)
    
    # Fallback to yesterday if no games found (handles US timezone rollover)
    if not board or 'games' not in board or not board['games']:
        from datetime import timedelta
        yesterday = now - timedelta(days=1)
        year, month, day = yesterday.year, yesterday.month, yesterday.day
        board = predict_advanced.fetch_scoreboard(year, month, day)

    if not board or 'games' not in board or not board['games']:
        return {"error": f"No games found for {now.strftime('%Y-%m-%d')} or fallback."}

    # Load necessary data
    stats_data = predict_advanced.load_json(predict_advanced.TEAM_STATS_FILE)
    standings_data = predict_advanced.load_json(predict_advanced.STANDINGS_FILE)
    player_data = predict_advanced.load_json(predict_props.INDIV_STATS_FILE)

    if not stats_data:
        return {"error": "Stats data missing"}

    # Load BartTorvik stats for better precision
    bt_stats = predict_advanced.load_json(predict_advanced.BARTTORVIK_STATS_FILE)
    
    # Get metrics for all models
    metrics_adv, avg_tempo, avg_off, avg_def = predict_advanced.get_team_metrics(stats_data, standings_data)
    
    if bt_stats:
        # Calculate BartTorvik league averages for more consistent normalization
        avg_tempo = sum(t['adj_t'] for t in bt_stats.values()) / len(bt_stats)
        avg_off = sum(t['adj_off'] for t in bt_stats.values()) / len(bt_stats)
        avg_def = sum(t['adj_def'] for t in bt_stats.values()) / len(bt_stats)

    metrics_tot, _, _ = predict_totals.get_total_metrics(stats_data)
    metrics_con, _, _ = predict_conservative.get_pessimistic_metrics(stats_data, standings_data)
    metrics_simple = predict_simple.get_simple_metrics(stats_data)
    metrics_props_team, avg_ppg, avg_tempo_props, avg_eff_props = predict_props.get_team_metrics(stats_data)

    results = []

    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue

        away_name = game['away']['names']['short']
        home_name = game['home']['names']['short']
        
        # Match teams for all models
        nameA_adv = predict_advanced.find_team(away_name, metrics_adv)
        nameH_adv = predict_advanced.find_team(home_name, metrics_adv)
        
        # We'll use the advanced matching as the anchor
        if not nameA_adv or not nameH_adv:
            continue

        game_data = {
            "id": game.get('gameID', 'unknown'),
            "away": away_name,
            "home": home_name,
            "awayRank": game['away'].get('rank', ''),
            "homeRank": game['home'].get('rank', ''),
            "awayScore": game['away'].get('score', '0'),
            "homeScore": game['home'].get('score', '0'),
            "status": game.get('gameState', 'UPCOMING').upper(),
            "clock": game.get('contestClock', ''),
            "period": game.get('currentPeriod', ''),
            "tv": game.get('network', ''),
            "startTime": game.get('startTime', ''),
            "predictions": {}
        }

        # 1. Advanced Model
        adv_res = predict_advanced.predict_game(away_name, home_name, metrics_adv, (avg_tempo, avg_off, avg_def), bt_stats)
        if adv_res:
            game_data["predictions"]["advanced"] = adv_res

        # 2. Totals Model
        tot_res = predict_totals.predict_total(away_name, home_name, metrics_tot, (avg_tempo, avg_def))
        if tot_res:
            game_data["predictions"]["totals"] = {
                "total": tot_res["adj_total"]
            }

        # 3. Conservative Model
        con_res = predict_conservative.predict_pessimistic(away_name, home_name, metrics_con, (avg_tempo, avg_off))
        if con_res:
            game_data["predictions"]["conservative"] = {
                "scoreA": con_res["scoreA"],
                "scoreH": con_res["scoreH"]
            }

        # 4. Simple Model
        sim_res = predict_simple.predict_simple(away_name, home_name, metrics_simple)
        if sim_res:
            game_data["predictions"]["simple"] = {
                "scoreA": sim_res["scoreA"],
                "scoreH": sim_res["scoreH"]
            }

        # 5. Props (Top 2 per team)
        nameA_p = predict_props.find_team(away_name, metrics_props_team)
        nameH_p = predict_props.find_team(home_name, metrics_props_team)
        game_data["props"] = {"away": [], "home": []}
        
        if nameA_p and nameH_p and adv_res:
            pts_list = player_data.get('pts_pg', [])
            for side, t_name in [("away", nameA_p), ("home", nameH_p)]:
                players = [p for p in pts_list if p.get('Team') == t_name]
                for p in sorted(players, key=lambda x: float(x.get('PPG', 0)), reverse=True)[:2]:
                    game_data["props"][side].append({
                        "name": p.get('Name', 'Unknown'),
                        "pts": round(float(p.get('PPG', 0)) * (adv_res['scoreA']/avg_ppg if side=="away" else adv_res['scoreH']/avg_ppg), 1)
                    })

        results.append(game_data)

    return {"date": now.strftime("%Y-%m-%d"), "games": results}

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    print(json.dumps(get_all_data(target)))
