import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nbl1.fetch_nbl1_schedule import fetch_nbl1_schedule
from nbl1.fetch_nbl1_stats import fetch_nbl1_stats
from utils.mapping import get_target_date

# NBL1 league eff pivot (used for elite-offense thresholds)
NBL1_EFF_PIVOT = 100.0


def _count_form_wins(form_str):
    """Count W's in last-5 form string. Default 2 (neutral) if unavailable."""
    if not form_str:
        return 2
    return form_str.upper().count("W")


def get_daily_input_sheet(date_obj=None, refresh=False):
    """
    Standardizes NBL1 data for the universal prediction engine.
    Injects both aggregate stats and Full Mode sharp flags.
    """
    if refresh:
        fetch_nbl1_schedule(date_obj)
        fetch_nbl1_stats()

    try:
        with open("data/nbl1_matchups.json", "r") as f:
            matchups = json.load(f)
        with open("data/nbl1_stats.json", "r") as f:
            stats = json.load(f)
    except FileNotFoundError:
        print("NBL1 data files not found. Refreshing...")
        fetch_nbl1_schedule(date_obj)
        stats = fetch_nbl1_stats()
        with open("data/nbl1_matchups.json", "r") as f:
            matchups = json.load(f)

    standardized_matchups = []

    for m in matchups:
        home_name = m.get("home_team")
        away_name = m.get("away_team")

        home_stats = stats.get(home_name, {})
        away_stats = stats.get(away_name, {})

        if not home_stats or not away_stats:
            print(f"Skipping NBL1 matchup: {away_name} @ {home_name} (Missing stats)")
            continue

        # --- Aggregate pace & efficiency ---
        home_pace = home_stats.get("pace", 72.0)
        away_pace = away_stats.get("pace", 72.0)
        avg_pace  = (home_pace + away_pace) / 2

        home_off = home_stats.get("offensive_rating", 100.0)
        away_off = away_stats.get("offensive_rating", 100.0)
        home_def = home_stats.get("defensive_rating", 100.0)
        away_def = away_stats.get("defensive_rating", 100.0)
        avg_eff  = (home_off + away_off + home_def + away_def) / 4

        # Market total estimated from team PPG averages
        est_total = home_stats.get("points_for_average", 95.0) + away_stats.get("points_for_average", 95.0)

        conf = m.get("conference", "Unknown")

        # --- Full Mode Sharp Flag Calculations ---

        # 1. Home pace advantage: home team scores noticeably more at home
        home_ppg_avg  = home_stats.get("points_for_average", 95.0)
        home_ppg_home = home_stats.get("ppg_home", home_ppg_avg)
        is_home_pace_advantage = home_ppg_home > home_ppg_avg * 1.05 if home_ppg_avg > 0 else False

        # 2. Away pace drag: away team scores noticeably less on the road
        away_ppg_avg  = away_stats.get("points_for_average", 95.0)
        away_ppg_away = away_stats.get("ppg_away", away_ppg_avg)
        is_away_pace_drag = away_ppg_away < away_ppg_avg * 0.95 if away_ppg_avg > 0 else False

        # 3. Possession mismatch — away team high-turnover tendency OR rebound disparity
        #    Approximated: if away team has significantly lower OFF vs home DEF
        off_def_gap = away_off - home_def
        is_turnover_mismatch = off_def_gap < -8.0   # semi-pro: earlier trigger (was -10)

        # 4. Rebound mismatch — composite home dominance signal
        is_rebound_mismatch = (home_off - away_def) > 10.0  # semi-pro: earlier trigger (was 12)

        # 5. Form wins (last 5 games each)
        home_form_wins = _count_form_wins(home_stats.get("form", ""))
        away_form_wins = _count_form_wins(away_stats.get("form", ""))

        # 6. Win pct mismatch — blowout context flag
        home_wpc = home_stats.get("win_pct", 0.5)
        away_wpc = away_stats.get("win_pct", 0.5)
        win_pct_gap = abs(home_wpc - away_wpc)
        is_likely_blowout = win_pct_gap > 0.35  # 35+ pct gap → lopsided matchup

        # 7. Venue pace split for Sharp 7 in engine
        # Provide home team's home-pace and away team's away-pace
        pace_home_home = home_stats.get("pace_home", home_pace)
        pace_away_away = away_stats.get("pace_away", away_pace)

        std_matchup = {
            "matchup":   f"{away_name} @ {home_name}",
            "team":      away_name,
            "opponent":  home_name,
            "away_team": away_name,
            "home_team": home_name,
            "conf":      conf,

            # Engine inputs
            "pace_adjustment":       avg_pace,
            "efficiency_adjustment": avg_eff,
            "market_total":          round(est_total, 1),

            # Sharp boolean flags (consumed by engine Phase 2)
            "is_rebound_mismatch":   is_rebound_mismatch,
            "is_turnover_mismatch":  is_turnover_mismatch,
            "is_home_pace_advantage": is_home_pace_advantage,
            "is_away_pace_drag":     is_away_pace_drag,
            "is_likely_blowout":     is_likely_blowout,

            # Form data (NBL1-specific Sharp 4.5)
            "home_form_wins": home_form_wins,
            "away_form_wins": away_form_wins,

            # Full team stats blocks (Phase 1 + Sharp 2/7)
            "statsA": {
                "adj_off":   away_off,
                "adj_def":   away_def,
                "adj_t":     away_pace,
                "pace":      away_pace,
                "pace_away": pace_away_away,    # Sharp 7 (venue pace split)
                "avg_points":      away_stats.get("points_for_average"),
                "opp_avg_points":  away_stats.get("points_against_average"),
                "wins":            away_stats.get("wins"),
                "losses":          away_stats.get("losses"),
                "win_pct":         away_stats.get("win_pct", 0.5),
                "win_pct_away":    away_stats.get("win_pct_away", 0.5),
                "form_wins":       away_form_wins
            },
            "statsH": {
                "adj_off":   home_off,
                "adj_def":   home_def,
                "adj_t":     home_pace,
                "pace":      home_pace,
                "pace_home": pace_home_home,    # Sharp 7 (venue pace split)
                "avg_points":      home_stats.get("points_for_average"),
                "opp_avg_points":  home_stats.get("points_against_average"),
                "wins":            home_stats.get("wins"),
                "losses":          home_stats.get("losses"),
                "win_pct":         home_stats.get("win_pct", 0.5),
                "win_pct_home":    home_stats.get("win_pct_home", 0.5),
                "form_wins":       home_form_wins
            },
            # Legacy bridge fields
            "home_stats": {
                "adj_o": home_off, "adj_d": home_def, "adj_t": home_pace,
                "avg_points": home_stats.get("points_for_average"),
                "opp_avg_points": home_stats.get("points_against_average"),
                "wins": home_stats.get("wins"), "losses": home_stats.get("losses")
            },
            "away_stats": {
                "adj_o": away_off, "adj_d": away_def, "adj_t": away_pace,
                "avg_points": away_stats.get("points_for_average"),
                "opp_avg_points": away_stats.get("points_against_average"),
                "wins": away_stats.get("wins"), "losses": away_stats.get("losses")
            },
            "metadata": {
                "league":     "NBL1",
                "conference": conf,
                "start_time": m.get("start_time"),
                "gravity":    1.0,
                "home_logo":  m.get("home_logo", home_stats.get("logo", "")),
                "away_logo":  m.get("away_logo", away_stats.get("logo", ""))
            }
        }
        standardized_matchups.append(std_matchup)

    return standardized_matchups


if __name__ == "__main__":
    sheet = get_daily_input_sheet(refresh=True)
    print(json.dumps(sheet, indent=2))
    print(f"\n{len(sheet)} NBL1 matchups standardized.")
