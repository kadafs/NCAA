# Unified Basketball Runner v1.4
import argparse
import sys
import os
import json
from datetime import datetime
import zoneinfo

# Root addition
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.basketball_engine import UniversalBasketballEngine
from core.prop_engine import UniversalPropEngine
from core.data_bridge import UniversalDataBridge

# Set encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def main():
    parser = argparse.ArgumentParser(description="Universal Basketball Framework v1.4")
    parser.add_argument("--league", choices=["nba", "ncaa", "euro", "eurocup", "nbl", "nbl1", "acb",
                                              "epl", "la_liga", "a_league", "bundesliga", "serie_a", "ligue_1",
                                              'hk_1st', 'eng_dev_2', 'eng_pl_2', 'wales_champ', 'aus_landesliga', 'scot_highland', 'scot_lowland', 'ind_ileague', 'cro_1nl', 'swe_div1_norra', 'uefa_cl', 'nor_div1', 'den_superliga', 'ger_reg_west', 'eng_isthmian', 'lat_1liga', 'crc_segunda', 'ned_eredivisie', 'scot_prem', 'ban_pl', 'tha_pl', 'swe_damallsvenskan',
                                              'par_primera_ap', 'usa_mls', 'ven_primera', 'spa_tercera_6', 'hon_liga_nac', 'spa_tercera_18', 'ecu_primera_b', 'arg_nacional_b', 'arg_primera', 'ita_serie_b', 'col_primera_a', 'arg_primera_b', 'fra_national', 'egy_prem', 'uru_apertura',
                                              'eng_championship', 'eng_league_one', 'eng_league_two', 'eng_national',
                                              'bra_serie_a', 'bra_serie_b', 'chi_primera', 'bol_primera', 'per_primera', 'ecu_primera_a', 'uru_clausura', 'par_primera_cl', 'col_primera_b',
                                              'sui_super', 'sui_challenge', 'aut_bundesliga', 'aut_2liga', 'bel_pro', 'ned_eerste', 'swe_allsvenskan', 'nor_eliteserien', 'isl_urvalsdeild', 'ger_2bundesliga', 'tur_super_lig',
                                              'sau_div1', 'den_1div', 'mex_liga_mx', 'chi_segunda', 'fra_ligue2'],
                        default="nba", help="League to model")
    parser.add_argument("--sport", choices=["basketball", "football"], default="basketball",
                        help="Sport to model (football = soccer)")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--refresh", action="store_true", help="Refresh data before running")
    parser.add_argument("--push", action="store_true", help="Push results to Supabase dashboard")
    args = parser.parse_args()

    # 1. Config paths & Target Date
    from utils.mapping import get_target_date
    target_date = get_target_date(args.date)
    
    config_map = {
        # Basketball
        "nba":      "configs/leagues/nba.json",
        "ncaa":     "configs/leagues/ncaa.json",
        "euro":     "configs/leagues/euro.json",
        "eurocup":  "configs/leagues/eurocup.json",
        "nbl":      "configs/leagues/nbl.json",
        "nbl1":     "configs/leagues/nbl1.json",
        "acb":      "configs/leagues/acb.json",
        # Football (soccer)
        "epl":        "configs/leagues/epl.json",
        "la_liga":    "configs/leagues/la_liga.json",
        "a_league":   "configs/leagues/a_league.json",
        "bundesliga": "configs/leagues/bundesliga.json",
        "serie_a":    "configs/leagues/serie_a.json",
        "ligue_1":    "configs/leagues/ligue_1.json",
        "hk_1st": "configs/leagues/hk_1st.json",
        "eng_dev_2": "configs/leagues/eng_dev_2.json",
        "eng_pl_2": "configs/leagues/eng_pl_2.json",
        "wales_champ": "configs/leagues/wales_champ.json",
        "aus_landesliga": "configs/leagues/aus_landesliga.json",
        "scot_highland": "configs/leagues/scot_highland.json",
        "scot_lowland": "configs/leagues/scot_lowland.json",
        "ind_ileague": "configs/leagues/ind_ileague.json",
        "cro_1nl": "configs/leagues/cro_1nl.json",
        "swe_div1_norra": "configs/leagues/swe_div1_norra.json",
        "uefa_cl": "configs/leagues/uefa_cl.json",
        "nor_div1": "configs/leagues/nor_div1.json",
        "den_superliga": "configs/leagues/den_superliga.json",
        "ger_reg_west": "configs/leagues/ger_reg_west.json",
        "eng_isthmian": "configs/leagues/eng_isthmian.json",
        "lat_1liga": "configs/leagues/lat_1liga.json",
        "crc_segunda": "configs/leagues/crc_segunda.json",
        "ned_eredivisie": "configs/leagues/ned_eredivisie.json",
        "scot_prem": "configs/leagues/scot_prem.json",
        "ban_pl": "configs/leagues/ban_pl.json",
        "tha_pl": "configs/leagues/tha_pl.json",
        "swe_damallsvenskan": "configs/leagues/swe_damallsvenskan.json",
        "par_primera_ap": "configs/leagues/par_primera_ap.json",
        "usa_mls": "configs/leagues/usa_mls.json",
        "ven_primera": "configs/leagues/ven_primera.json",
        "spa_tercera_6": "configs/leagues/spa_tercera_6.json",
        "hon_liga_nac": "configs/leagues/hon_liga_nac.json",
        "spa_tercera_18": "configs/leagues/spa_tercera_18.json",
        "ecu_primera_b": "configs/leagues/ecu_primera_b.json",
        "arg_nacional_b": "configs/leagues/arg_nacional_b.json",
        "arg_primera": "configs/leagues/arg_primera.json",
        "ita_serie_b": "configs/leagues/ita_serie_b.json",
        "col_primera_a": "configs/leagues/col_primera_a.json",
        "arg_primera_b": "configs/leagues/arg_primera_b.json",
        "fra_national": "configs/leagues/fra_national.json",
        "egy_prem": "configs/leagues/egy_prem.json",
        "uru_apertura": "configs/leagues/uru_apertura.json",
        "eng_championship": "configs/leagues/eng_championship.json",
        "eng_league_one":   "configs/leagues/eng_league_one.json",
        "eng_league_two":   "configs/leagues/eng_league_two.json",
        "eng_national":     "configs/leagues/eng_national.json",
        "bra_serie_a":      "configs/leagues/bra_serie_a.json",
        "bra_serie_b":      "configs/leagues/bra_serie_b.json",
        "chi_primera":      "configs/leagues/chi_primera.json",
        "bol_primera":      "configs/leagues/bol_primera.json",
        "per_primera":      "configs/leagues/per_primera.json",
        "ecu_primera_a":    "configs/leagues/ecu_primera_a.json",
        "uru_clausura":     "configs/leagues/uru_clausura.json",
        "par_primera_cl":   "configs/leagues/par_primera_cl.json",
        "col_primera_b":    "configs/leagues/col_primera_b.json",
        "sui_super":        "configs/leagues/sui_super.json",
        "sui_challenge":    "configs/leagues/sui_challenge.json",
        "aut_bundesliga":   "configs/leagues/aut_bundesliga.json",
        "aut_2liga":        "configs/leagues/aut_2liga.json",
        "bel_pro":          "configs/leagues/bel_pro.json",
        "ned_eerste":       "configs/leagues/ned_eerste.json",
        "swe_allsvenskan":  "configs/leagues/swe_allsvenskan.json",
        "nor_eliteserien":  "configs/leagues/nor_eliteserien.json",
        "isl_urvalsdeild":  "configs/leagues/isl_urvalsdeild.json",
        "ger_2bundesliga":  "configs/leagues/ger_2bundesliga.json",
        "tur_super_lig":    "configs/leagues/tur_super_lig.json",
        "sau_div1":         "configs/leagues/sau_div1.json",
        "den_1div":         "configs/leagues/den_1div.json",
        "mex_liga_mx":      "configs/leagues/mex_liga_mx.json",
        "chi_segunda":      "configs/leagues/chi_segunda.json",
        "fra_ligue2":       "configs/leagues/fra_ligue2.json",
    }
    
    # 2. Refresh if needed
    if args.refresh:
        print(f"Refreshing {args.league.upper()} data for {target_date.strftime('%Y-%m-%d')}...")
        if args.league == "nba":
            from nba.fetch_nba_schedule import fetch_nba_daily_schedule
            from nba.fetch_nba_stats import fetch_nba_stats
            from nba.fetch_nba_player_stats import fetch_nba_player_stats
            from nba.fetch_nba_injuries import fetch_nba_injuries
            fetch_nba_daily_schedule(target_date)
            fetch_nba_stats()
            fetch_nba_player_stats()
            fetch_nba_injuries()
        elif args.league == "ncaa":
            from ncaa.fetch_injuries import fetch_injuries
            from ncaa.data_fetcher import main as ncaa_fetch_main
            fetch_injuries()
            ncaa_fetch_main()
        elif args.league == "euro":
            from euro.fetch_euro_schedule import fetch_euro_daily_schedule
            fetch_euro_daily_schedule(target_date)
        elif args.league == "eurocup":
            from eurocup.fetch_eurocup_schedule import fetch_eurocup_schedule
            fetch_eurocup_schedule(target_date)
        elif args.league == "nbl":
            from nbl.fetch_nbl_schedule import fetch_nbl_schedule
            from nbl.fetch_nbl_stats import fetch_nbl_stats
            fetch_nbl_schedule(target_date)
            fetch_nbl_stats()
        elif args.league == "nbl1":
            from nbl1.fetch_nbl1_schedule import fetch_nbl1_schedule
            from nbl1.fetch_nbl1_stats import fetch_nbl1_stats
            fetch_nbl1_schedule(target_date)
            fetch_nbl1_stats()
        elif args.league == "acb":
            from acb.fetch_acb_schedule import fetch_acb_schedule
            from acb.fetch_acb_stats import fetch_acb_stats
            fetch_acb_schedule(target_date)
            fetch_acb_stats()
        elif args.league in (
            "epl", "la_liga", "a_league", "bundesliga", "serie_a", "ligue_1",
            "hk_1st", "eng_dev_2", "eng_pl_2", "wales_champ", "aus_landesliga", 
            "scot_highland", "scot_lowland", "ind_ileague", "cro_1nl", 
            "swe_div1_norra", "uefa_cl", "nor_div1", "den_superliga", 
            "ger_reg_west", "eng_isthmian", "lat_1liga", "crc_segunda", 
            "ned_eredivisie", "scot_prem", "ban_pl", "tha_pl", "swe_damallsvenskan",
            "par_primera_ap", "usa_mls", "ven_primera", "spa_tercera_6", 
            "hon_liga_nac", "spa_tercera_18", "ecu_primera_b", "arg_nacional_b", 
            "arg_primera", "ita_serie_b", "col_primera_a", "arg_primera_b", 
            "fra_national", "egy_prem", "uru_apertura",
            "eng_championship", "eng_league_one", "eng_league_two", "eng_national",
            "bra_serie_a", "bra_serie_b", "chi_primera", "bol_primera", 
            "per_primera", "ecu_primera_a", "uru_clausura", "par_primera_cl", 
            "col_primera_b",
            "sui_super", "sui_challenge", "aut_bundesliga", "aut_2liga", 
            "bel_pro", "ned_eerste", "swe_allsvenskan", "nor_eliteserien", 
            "isl_urvalsdeild", "ger_2bundesliga", "tur_super_lig"
        ):
            from football.fetch_football_schedule import fetch_football_schedule
            from football.fetch_football_stats import fetch_football_stats
            fetch_football_schedule(args.league, date_obj=target_date)
            fetch_football_stats(args.league)

    # -------------------------------------------------------
    # FOOTBALL SPORT BRANCH — completely separate loop
    # -------------------------------------------------------
    if args.sport == "football" or args.league in (
        "epl", "la_liga", "a_league", "bundesliga", "serie_a", "ligue_1",
        "hk_1st", "eng_dev_2", "eng_pl_2", "wales_champ", "aus_landesliga", 
        "scot_highland", "scot_lowland", "ind_ileague", "cro_1nl", 
        "swe_div1_norra", "uefa_cl", "nor_div1", "den_superliga", 
        "ger_reg_west", "eng_isthmian", "lat_1liga", "crc_segunda", 
        "ned_eredivisie", "scot_prem", "ban_pl", "tha_pl", "swe_damallsvenskan",
        "par_primera_ap", "usa_mls", "ven_primera", "spa_tercera_6", 
        "hon_liga_nac", "spa_tercera_18", "ecu_primera_b", "arg_nacional_b", 
        "arg_primera", "ita_serie_b", "col_primera_a", "arg_primera_b", 
        "fra_national", "egy_prem", "uru_apertura",
        "eng_championship", "eng_league_one", "eng_league_two", "eng_national",
        "bra_serie_a", "bra_serie_b", "chi_primera", "bol_primera", 
        "per_primera", "ecu_primera_a", "uru_clausura", "par_primera_cl", 
        "col_primera_b",
        "sui_super", "sui_challenge", "aut_bundesliga", "aut_2liga", 
        "bel_pro", "ned_eerste", "swe_allsvenskan", "nor_eliteserien", 
        "isl_urvalsdeild", "ger_2bundesliga", "tur_super_lig"
    ):
        from core.football_engine import FootballEngine, load_football_config
        from football.v1_0.populate import get_daily_input_sheet as football_sheet

        daily_sheet = []
        try:
            fconfig = load_football_config(args.league)
            fengine = FootballEngine(fconfig, mode=args.mode, trace=args.trace)
            daily_sheet = football_sheet(args.league, date_obj=target_date, config=fconfig)
        except Exception as e:
            print(f"Failed to load football constraints for {args.league}: {e}")

        if not daily_sheet:
            print(f"No {args.league.upper()} fixtures found for {target_date.strftime('%Y-%m-%d')}.")
            return

        print("\n" + "="*80)
        print(f" [FOOTBALL ENGINE v1.0] {args.league.upper()} | {args.mode.upper()}")
        print(f" Target Date: {target_date.strftime('%Y-%m-%d')}")
        print("="*80)

        prediction_records = []

        for game in daily_sheet:
            result = fengine.calculate(game)

            btts_pct  = result['btts_prob_final'] * 100
            draw_pct  = result['draw_prob_final'] * 100
            edge_pct  = result['btts_edge']       * 100
            conf      = result['btts_confidence']
            decision  = result['btts_decision']

            print(f"\n[MATCH] {game['matchup']}")
            print(f"   xG: {result['xg_home']:.2f} (H) / {result['xg_away']:.2f} (A) | Total xG: {result['xg_total']:.2f}")
            print(f"   BTTS: {btts_pct:.1f}% | Mkt: {result['btts_market_prob']*100:.1f}% | Edge: {edge_pct:+.1f}% | [{conf}] {decision}")
            print(f"   Draw: {draw_pct:.1f}% | Fair Odds: {result['draw_fair_odds']:.2f}x", end="")
            if result.get('draw_value_flag'):
                print(" <- Check draw market")
            else:
                print()

            if args.trace:
                for t in result['logs']:
                    print(f"     > {t}")

            if result['notes']:
                for n in result['notes']:
                    print(f"   * {n}")

            # Build structured record for JSON output
            prediction_records.append({
                "matchup":          game['matchup'],
                "home_team":        game.get('home_team', ''),
                "away_team":        game.get('away_team', ''),
                "date":             target_date.strftime('%Y-%m-%d'),
                "league":           args.league,
                "mode":             args.mode,
                "xg_home":          round(result['xg_home'], 3),
                "xg_away":          round(result['xg_away'], 3),
                "xg_total":         round(result['xg_total'], 3),
                "btts_prob":        round(btts_pct, 1),
                "btts_market":      round(result['btts_market_prob'] * 100, 1),
                "btts_edge":        round(edge_pct, 1),
                "btts_confidence":  conf,
                "btts_decision":    decision,
                "draw_prob":        round(draw_pct, 1),
                "draw_fair_odds":   result['draw_fair_odds'],
                "draw_value_flag":  result.get('draw_value_flag', False),
                "notes":            result.get('notes', []),
                "timestamp":        datetime.now(ET_TZ).isoformat(),
            })

        # Save predictions to data/football/
        os.makedirs("data/football", exist_ok=True)
        out_path = f"data/football/{args.league}_predictions.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(prediction_records, f, indent=2)
        print(f"\nSaved {len(prediction_records)} predictions -> {out_path}")

        print("\n" + "="*80)
        print("Execution Finished.")
        print("="*80)
        return


    # -------------------------------------------------------
    # BASKETBALL BRANCH (original code below)
    # -------------------------------------------------------
    if not daily_sheet:
        print(f"No {args.league.upper()} games found today.")
        return

    # Initialize basketball engines
    engine = UniversalBasketballEngine(config_map[args.league], mode=args.mode)
    prop_engine = UniversalPropEngine(mode=args.mode)
    bridge = UniversalDataBridge(args.league)

    # Initialize data bridge with date support
    if args.league == "ncaa":
        daily_sheet = bridge.get_standardized_sheet(date_obj=target_date)
    else:
        daily_sheet = bridge.get_standardized_sheet()

    if not daily_sheet:
        print(f"No {args.league.upper()} games found today.")
        return

    # 5. Header
    print("\n" + "█"*80)
    print(f" UNIVERSAL BASKETBALL FRAMEWORK v1.4 | {args.league.upper()} | {args.mode.upper()}")
    print(f" Target Date: {target_date.strftime('%Y-%m-%d')} ET")
    print("█"*80)

    # 4. Load Metadata (Injuries & Players) - RESTORED
    p_stats = []
    injuries = {}
    if args.league == "nba":
        from nba.v1_2.populate import load_json, NBA_INJURY_FILE
        p_stats = load_json("data/nba_player_stats.json")
        if args.mode == "full":
            injuries = load_json(NBA_INJURY_FILE)
    elif args.league == "eurocup":
        from eurocup.v1_2.populate import load_json
        p_stats = load_json("data/eurocup_player_stats.json")
        if args.mode == "full":
            injuries = load_json("data/eurocup_injury_notes.json")
    elif args.league == "euro":
        from euro.v1_2.populate import load_json
        p_stats = load_json("data/euro_player_stats.json")
        if args.mode == "full":
            injuries = load_json("data/euro_injury_notes.json")

    for game in daily_sheet:
        away = game.get('team')
        home = game.get('opponent')
        
        # Injuries for this game
        game_injuries = []
        if args.mode == "full":
            game_injuries.extend(injuries.get(away, []))
            game_injuries.extend(injuries.get(home, []))
            
        res = engine.calculate_total(game, game_injuries)
        
        print(f"\n🏀 MATCHUP: {away} @ {home}")
        print(f"   Market: {res['market_total']:5.1f} | Model: {res['final_model_total']:5.1f} | Edge: {res['edge']:+5.2f} | [{res['mode']}] {res['decision']}")
        
        if args.trace:
            for t in res['trace']: print(f"     > {t}")
        
        # Advanced Metrics Display (NCAA)
        # Advanced Metrics Display (NCAA)
        if args.league == "ncaa" and "statsA" in game and "statsH" in game:
            sA = game['statsA']
            sH = game['statsH']
            print("\n   Advanced Metrics:")
            
            def fmt_stat(label, s):
                ff = s.get('four_factors', {})
                # Try top level first (raw), then nested (bridge normalized)
                efg = s.get('efg', ff.get('efg', 0))
                to = s.get('to', ff.get('tov', 0))
                orb = s.get('or', ff.get('orb', 0))
                ftr = s.get('ftr', ff.get('ftr', 0))
                
                return f"{label}: {s.get('adj_t', 0):4.1f} | OE: {s.get('adj_off', 0):5.1f} | DE: {s.get('adj_def', 0):4.1f} | eFG: {efg:4.1f} | TO: {to:4.1f} | OR: {orb:4.1f} | FTR: {ftr:4.1f}"

            print(f"     [Away] {fmt_stat('AdjT', sA)}")
            print(f"     [Home] {fmt_stat('AdjT', sH)}")
            
        # Props
        if args.league in ["nba", "euro", "eurocup"] and p_stats:
            print(f"   Top Player Projections ({args.league.upper()}):")
            from utils.mapping import NBA_TRICODES, EURO_TRICODES, EUROCUP_TRICODES
            
            tricode_map = NBA_TRICODES if args.league == "nba" else EURO_TRICODES if args.league == "euro" else EUROCUP_TRICODES
            full_to_tricode = {v: k for k, v in tricode_map.items()}
            
            triA = full_to_tricode.get(away)
            triH = full_to_tricode.get(home)
            
            # Use codes directly if mapping fails (e.g. Euro API already using codes)
            if not triA: triA = away if any(p['team'] == away for p in p_stats) else None
            if not triH: triH = home if any(p['team'] == home for p in p_stats) else None
            
            pivot_val = 230.0 if args.league == "nba" else 160.0 if args.league == "euro" else 165.0
            factor = res['final_model_total'] / pivot_val
            context = {"factor": factor, "vol_factor": 1.0}

            for team_tri, label in [(triA, 'A'), (triH, 'H')]:
                if not team_tri: continue
                # Handling seasonal vs flat stats
                def get_p_stats(p):
                    if 'seasonal' in p: return p['seasonal']
                    return {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)}

                players = [p for p in p_stats if p['team'] == team_tri]
                players.sort(key=lambda x: get_p_stats(x)['pts'], reverse=True)
                
                for p in players[:3]:
                    team_injs = injuries.get(away if label == 'A' else home, [])
                    # Wrap flat stats for prop engine if needed
                    if 'seasonal' not in p:
                        p = {**p, "seasonal": get_p_stats(p), "recent": get_p_stats(p)}
                    p_proj = prop_engine.project_player(p, context, team_injs)
                    print(f"     [{label}] {p['name']:20} | Pts: {p_proj['proj_pts']:4.1f} | Reb: {p_proj['proj_reb']:4.1f} | Ast: {p_proj['proj_ast']:3.1f}")
            
    print("\n" + "█"*80)
    print("Execution Finished.")

    # 7. Optional Push to Supabase Dashboard
    if args.push:
        print(f"\nPushing {args.league.upper()} predictions to Dashboard...")
        import asyncio
        from core.supabase_pusher import push_league_predictions
        try:
            asyncio.run(push_league_predictions(args.league, date_override=target_date if args.date else None))
            print("Dashboard update triggered successfully.")
        except Exception as e:
            print(f"Failed to push to dashboard: {e}")

if __name__ == "__main__":
    main()
