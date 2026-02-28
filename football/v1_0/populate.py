import json
import math
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from football.fetch_football_schedule import fetch_football_schedule
from football.fetch_football_stats import fetch_football_stats


def poisson_prob(lam, k):
    """P(X = k) for Poisson distribution with mean lam."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.e ** -lam) * (lam ** k) / math.factorial(k)


def calc_btts_prob(xg_home, xg_away):
    """P(BTTS Yes) = P(home scores ≥ 1) × P(away scores ≥ 1)"""
    p_home_scores = 1 - poisson_prob(xg_home, 0)
    p_away_scores = 1 - poisson_prob(xg_away, 0)
    return round(p_home_scores * p_away_scores, 4)


def calc_draw_prob(xg_home, xg_away, max_goals=6):
    """
    P(Draw) = sum of matching scorelines: P(0-0) + P(1-1) + ... + P(max_goals-max_goals)
    """
    draw_prob = 0.0
    for k in range(max_goals + 1):
        draw_prob += poisson_prob(xg_home, k) * poisson_prob(xg_away, k)
    return round(draw_prob, 4)


def _count_form_wins(form_str):
    return form_str.upper().count("W") if form_str else 0


def _count_form_draws(form_str):
    return form_str.upper().count("D") if form_str else 0


def get_daily_input_sheet(league_code, date_obj=None, refresh=False, config=None):
    """
    Standardizes football fixture + stats data for the football engine.
    Returns list of game rows, each with:
      - xg_home, xg_away (Poisson lambda values)
      - btts_prob, draw_prob (Poisson-derived)
      - sharp flags for Phase 2 adjustments
    """
    if refresh:
        fetch_football_schedule(league_code, date_obj=date_obj)
        fetch_football_stats(league_code)

    fixtures_path = f"data/football/{league_code}_fixtures.json"
    stats_path    = f"data/football/{league_code}_stats.json"

    try:
        with open(fixtures_path, "r") as f:
            fixtures = json.load(f)
        with open(stats_path, "r") as f:
            stats_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Data files missing: {e}. Run with refresh=True.")
        return []

    teams      = stats_data.get("teams", {})
    lg_avgs    = stats_data.get("league_averages", {})
    avg_home   = lg_avgs.get("avg_home_goals_for", 1.5)
    avg_away   = lg_avgs.get("avg_away_goals_for", 1.2)

    # Config overrides
    regression = config.get("regression_factor", 0.88) if config else 0.88
    min_games  = config.get("min_games_played", 4)    if config else 4

    matchups = []

    for fix in fixtures:
        if fix.get("is_completed"):
            continue   # skip already-played games

        home_name = fix.get("home_team")
        away_name = fix.get("away_team")
        home_s    = teams.get(home_name, {})
        away_s    = teams.get(away_name, {})

        if not home_s or not away_s:
            print(f"  Skipping {away_name} @ {home_name} (missing stats)")
            continue

        if home_s.get("played_all", 0) < min_games or away_s.get("played_all", 0) < min_games:
            print(f"  Skipping {away_name} @ {home_name} (insufficient games played)")
            continue

        # -------------------------------------------------------
        # STEP 1 — Expected Goals via Dixon-Coles style Poisson
        # xG = AttackRating_team × DefenseRating_opponent × league_avg
        # home team attacks at home → use home attack + away defense vs home
        # away team attacks away  → use away attack + home defense vs away
        # -------------------------------------------------------
        ar_home = home_s.get("attack_rating_home", 1.0)
        dr_away = away_s.get("defense_rating_away", 1.0)    # how many goals away team concedes away
        xg_home_raw = ar_home * dr_away * avg_home

        ar_away = away_s.get("attack_rating_away", 1.0)
        dr_home = home_s.get("defense_rating_home", 1.0)    # how many goals home team concedes home
        xg_away_raw = ar_away * dr_home * avg_away

        # Apply regression toward league mean (damps early-season spikes)
        xg_home = round(xg_home_raw * regression + avg_home * (1 - regression), 3)
        xg_away = round(xg_away_raw * regression + avg_away * (1 - regression), 3)

        # -------------------------------------------------------
        # STEP 2 — Poisson Probabilities
        # -------------------------------------------------------
        btts_prob = calc_btts_prob(xg_home, xg_away)
        draw_prob = calc_draw_prob(xg_home, xg_away)

        # -------------------------------------------------------
        # STEP 3 — Sharp Flags for Phase 2
        # -------------------------------------------------------
        home_form     = _count_form_wins(home_s.get("form", ""))
        away_form     = _count_form_wins(away_s.get("form", ""))
        home_draws    = _count_form_draws(home_s.get("form", ""))
        away_draws    = _count_form_draws(away_s.get("form", ""))
        combined_form = home_form + away_form

        # Clean sheet form: if both teams have been keeping CSs, BTTS less likely
        home_cs_rate  = home_s.get("clean_sheets", 0) / home_s.get("played_all", 1)
        away_cs_rate  = away_s.get("clean_sheets", 0) / away_s.get("played_all", 1)
        both_defensive = home_cs_rate > 0.35 and away_cs_rate > 0.35

        # Attacking form: if both teams scoring well, BTTS more likely
        home_attacking = home_s.get("pgf_all", 0) > avg_home * 1.1
        away_attacking = away_s.get("pgf_all", 0) > avg_away * 1.1
        both_attacking = home_attacking and away_attacking

        # Draw tendency: both teams draw-prone
        draw_prone = (home_draws >= 2 and away_draws >= 2)   # 2+ draws in last 5

        matchups.append({
            # Identity
            "fixture_id":  fix.get("fixture_id"),
            "matchup":     f"{away_name} @ {home_name}",
            "home_team":   home_name,
            "away_team":   away_name,
            "kickoff":     fix.get("kickoff"),
            "league_code": league_code,

            # Core Poisson outputs
            "xg_home":    xg_home,
            "xg_away":    xg_away,
            "xg_total":   round(xg_home + xg_away, 3),
            "btts_prob":  btts_prob,
            "draw_prob":  draw_prob,

            # Sharp flags
            "is_both_defensive":  both_defensive,
            "is_both_attacking":  both_attacking,
            "is_draw_prone":      draw_prone,
            "combined_form_wins": combined_form,
            "home_cs_rate":       round(home_cs_rate, 3),
            "away_cs_rate":       round(away_cs_rate, 3),
            "home_btts_rate":     home_s.get("btts_rate", 0.5),
            "away_btts_rate":     away_s.get("btts_rate", 0.5),

            # Team stats block (for trace output)
            "statsH": {
                "attack_rating": home_s.get("attack_rating_home"),
                "defense_rating": home_s.get("defense_rating_home"),
                "pgf": home_s.get("pgf_home"),
                "pga": home_s.get("pga_home"),
                "form": home_s.get("form"),
                "btts_rate": home_s.get("btts_rate"),
                "clean_sheets": home_s.get("clean_sheets"),
            },
            "statsA": {
                "attack_rating": away_s.get("attack_rating_away"),
                "defense_rating": away_s.get("defense_rating_away"),
                "pgf": away_s.get("pgf_away"),
                "pga": away_s.get("pga_away"),
                "form": away_s.get("form"),
                "btts_rate": away_s.get("btts_rate"),
                "clean_sheets": away_s.get("clean_sheets"),
            },
            "metadata": {
                "league_code": league_code,
                "home_logo":   fix.get("home_logo", ""),
                "away_logo":   fix.get("away_logo", ""),
            }
        })

    print(f"\n{len(matchups)} matchups standardized for {league_code.upper()}.")
    return matchups


if __name__ == "__main__":
    sheet = get_daily_input_sheet("epl", refresh=True)
    for m in sheet:
        print(f"{m['matchup']}: xG {m['xg_home']:.2f}-{m['xg_away']:.2f} | "
              f"BTTS {m['btts_prob']*100:.1f}% | Draw {m['draw_prob']*100:.1f}%")
