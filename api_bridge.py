import json
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
            now = datetime.now()
    else:
        now = datetime.now()
        
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

    # Get metrics for all models
    metrics_adv, avg_tempo, avg_off, avg_def = predict_advanced.get_team_metrics(stats_data, standings_data)
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
        tA, tH = metrics_adv[nameA_adv], metrics_adv[nameH_adv]
        adv_tempo = (tA['tempo'] * tH['tempo']) / avg_tempo
        adv_scoreA = (tA['off_eff'] * tH['def_eff'] / avg_def) * (adv_tempo / 100)
        adv_scoreH = (tH['off_eff'] * tA['def_eff'] / avg_def) * (adv_tempo / 100)
        # Apply HCA
        adv_scoreH += 3.5
        game_data["predictions"]["advanced"] = {
            "scoreA": round(adv_scoreA, 1),
            "scoreH": round(adv_scoreH, 1),
            "total": round(adv_scoreA + adv_scoreH, 1),
            "spread": round(adv_scoreH - adv_scoreA, 1)
        }

        # 2. Totals Model
        nameA_tot = predict_totals.find_team(away_name, metrics_tot)
        nameH_tot = predict_totals.find_team(home_name, metrics_tot)
        if nameA_tot and nameH_tot:
            tA_t, tH_t = metrics_tot[nameA_tot], metrics_tot[nameH_tot]
            base_total = (tA_t['off_eff'] + tH_t['off_eff']) * (adv_tempo / 100)
            # Simplified version of the complex adjustments for the bridge
            game_data["predictions"]["totals"] = {
                "total": round(base_total, 1)
            }

        # 3. Conservative Model
        nameA_con = predict_conservative.find_team(away_name, metrics_con)
        nameH_con = predict_conservative.find_team(home_name, metrics_con)
        if nameA_con and nameH_con:
            tA_c, tH_c = metrics_con[nameA_con], metrics_con[nameH_con]
            con_scoreA = (tA_c['off_eff'] * 0.95 * tH_c['def_eff'] / 100) * (adv_tempo * 0.9 / 100)
            con_scoreH = (tH_c['off_eff'] * tA_c['def_eff'] / 100) * (adv_tempo * 0.9 / 100)
            game_data["predictions"]["conservative"] = {
                "scoreA": round(con_scoreA, 1),
                "scoreH": round(con_scoreH, 1)
            }

        # 4. Simple Model
        nameA_sim = predict_simple.find_team(away_name, metrics_simple)
        nameH_sim = predict_simple.find_team(home_name, metrics_simple)
        if nameA_sim and nameH_sim:
            tA_s, tH_s = metrics_simple[nameA_sim], metrics_simple[nameH_sim]
            sim_scoreA = (tA_s['offense'] + tH_s['defense']) / 2
            sim_scoreH = (tH_s['offense'] + tA_s['defense']) / 2
            game_data["predictions"]["simple"] = {
                "scoreA": round(sim_scoreA, 1),
                "scoreH": round(sim_scoreH, 1)
            }

        # 5. Props (Top 2 per team)
        nameA_p = predict_props.find_team(away_name, metrics_props_team)
        nameH_p = predict_props.find_team(home_name, metrics_props_team)
        game_data["props"] = {"away": [], "home": []}
        
        if nameA_p and nameH_p:
            pts_list = player_data.get('pts_pg', [])
            for side, t_name in [("away", nameA_p), ("home", nameH_p)]:
                players = [p for p in pts_list if p.get('Team') == t_name]
                for p in sorted(players, key=lambda x: float(x.get('PPG', 0)), reverse=True)[:2]:
                    game_data["props"][side].append({
                        "name": p.get('Name', 'Unknown'),
                        "pts": round(float(p.get('PPG', 0)) * (adv_scoreA/avg_ppg if side=="away" else adv_scoreH/avg_ppg), 1)
                    })

        results.append(game_data)

    return {"date": now.strftime("%Y-%m-%d"), "games": results}

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    print(json.dumps(get_all_data(target)))
