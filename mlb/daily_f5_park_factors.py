"""
daily_f5_park_factors.py
========================
Computes and saves blended park factors for MLB (sport 1), AAA (sport 11),
and AA (sport 12) in a single run.  Must be run daily before consensus.

Blending formula:
    w_realized = min(1.0, games_at_venue / SEASON_GAMES)
    blended    = realized × w_realized + static × (1 - w_realized)

This means:
  - Early in season: static 3-year baseline dominates (stable, reliable)
  - Late in season: current-year realized data dominates (fresh, park-specific)

Season denominators:
  - MLB : 162 games / venue
  - MiLB: 90  games / venue (each venue hosts ~45 home games × both teams)

All results are written to Current_Blended_F5_PF.json (single combined file).
get_park_factor() reads this file first for all parks.
"""

import os
import json
import datetime
import statsapi
import park_factors as pf_module

# ── Sport configuration ────────────────────────────────────────────────────────
SPORTS = [
    {"id": 1,  "label": "MLB", "start": datetime.date(2026, 3, 28), "season_games": 162, "min_games": 5},
    {"id": 11, "label": "AAA", "start": datetime.date(2026, 4,  1), "season_games": 90,  "min_games": 5},
    {"id": 12, "label": "AA",  "start": datetime.date(2026, 4,  1), "season_games": 90,  "min_games": 5},
]

OUT_PATH = os.path.join(os.path.dirname(__file__), 'Current_Blended_F5_PF.json')


def _get_static_pf(venue: str) -> float:
    """Get the static 3-year baseline PF for a venue, bypassing the dynamic JSON."""
    pf_module._dynamic_pf_loaded = True   # prevent loading the JSON we're about to overwrite
    pf_module._cached_dynamic_pf = None
    pf = pf_module.get_park_factor(venue)
    pf_module._dynamic_pf_loaded = False  # restore for future calls
    return pf


def _fetch_venue_stats(sport_id: int, start_dt: datetime.date) -> tuple[dict, int, int]:
    """
    Fetch all F5 game results for a sport since start_dt.
    Returns (venue_stats, total_runs, total_games).
    Batches by 7-day windows to stay within statsapi limits.
    """
    venue_stats: dict = {}
    total_runs  = 0
    total_games = 0
    end_dt      = datetime.date.today()

    current = start_dt
    while current <= end_dt:
        window_end = min(current + datetime.timedelta(days=6), end_dt)
        s_str = current.strftime("%Y-%m-%d")
        e_str = window_end.strftime("%Y-%m-%d")

        try:
            data = statsapi.get('schedule', {
                'sportId':   sport_id,
                'startDate': s_str,
                'endDate':   e_str,
                'hydrate':   'linescore',
            })
            for date_obj in data.get('dates', []):
                for g in date_obj.get('games', []):
                    if g.get('status', {}).get('abstractGameState') != 'Final':
                        continue

                    venue   = g.get('venue', {}).get('name', 'Unknown')
                    innings = g.get('linescore', {}).get('innings', [])
                    if len(innings) < 5:
                        continue

                    f5 = (
                        sum(inn.get('away', {}).get('runs', 0) or 0 for inn in innings[:5]) +
                        sum(inn.get('home', {}).get('runs', 0) or 0 for inn in innings[:5])
                    )

                    if venue not in venue_stats:
                        venue_stats[venue] = {'games': 0, 'runs': 0}
                    venue_stats[venue]['games'] += 1
                    venue_stats[venue]['runs']  += f5
                    total_runs  += f5
                    total_games += 1

        except Exception as exc:
            print(f"  Warning: {s_str}→{e_str} error — {exc}")

        current = window_end + datetime.timedelta(days=1)

    return venue_stats, total_runs, total_games


def _process_sport(cfg: dict, all_factors: dict) -> None:
    """
    Fetch, blend, and store park factors for one sport into all_factors dict.
    """
    sport_id     = cfg["id"]
    label        = cfg["label"]
    start_dt     = cfg["start"]
    season_games = cfg["season_games"]
    min_games    = cfg["min_games"]

    print(f"\n{'='*60}")
    print(f"  {label} (sport {sport_id})  |  start: {start_dt}  |  season: {season_games} games")
    print(f"{'='*60}")

    venue_stats, total_runs, total_games = _fetch_venue_stats(sport_id, start_dt)

    if total_games == 0:
        print(f"  No games found for {label}.")
        return

    league_avg = total_runs / total_games
    print(f"  {total_games} games processed | league avg F5: {league_avg:.3f} R/game\n")
    print(f"  {'Venue':<34} {'G':>4} {'AvgF5':>6}  {'Realized':>8}  {'Static':>7}  {'Blended':>8}")
    print(f"  {'-'*75}")

    for venue, stats in sorted(venue_stats.items()):
        if stats['games'] < min_games:
            continue

        avg_f5      = stats['runs'] / stats['games']
        realized_pf = avg_f5 / league_avg
        static_pf   = _get_static_pf(venue)

        # Dynamic weight — increases as more games are played this season
        w_realized  = min(1.0, stats['games'] / season_games)
        w_static    = 1.0 - w_realized
        blended_pf  = round((realized_pf * w_realized) + (static_pf * w_static), 3)

        all_factors[venue] = {
            "blended":  blended_pf,
            "static":   round(static_pf, 3),
            "realized": round(realized_pf, 3),
            "games":    stats['games'],
            "sport":    label,
        }

        delta = blended_pf - static_pf
        flag  = " <<" if abs(delta) > 0.05 else ""
        print(f"  {venue:<34} {stats['games']:>4} {avg_f5:>6.3f}  "
              f"{realized_pf:>8.3f}  {static_pf:>7.3f}  {blended_pf:>8.3f}"
              f"  ({delta:+.3f}){flag}")


def main():
    print("=== Daily F5 Park Factor Update ===")
    print(f"Date: {datetime.date.today()}")

    all_factors: dict = {}

    for cfg in SPORTS:
        _process_sport(cfg, all_factors)

    # Write combined JSON
    with open(OUT_PATH, 'w') as f:
        json.dump(all_factors, f, indent=4)

    print(f"\n[OK] Saved {len(all_factors)} park factors to {OUT_PATH}")
    print("     (MLB + AAA + AA -- all sports blended and ready for consensus)\n")


if __name__ == '__main__':
    main()
