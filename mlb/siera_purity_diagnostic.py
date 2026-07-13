"""
siera_purity_diagnostic.py
==========================
Audits home/away SIERA splits for today's AAA starting pitchers.

For each pitcher, computes:
  - Combined SIERA  (what the model uses)
  - Away SIERA      (park-neutral talent baseline)
  - Home SIERA      (home-park-inflated/deflated)

Then compares:
  Model's projection  = combined_siera x park_factor   (current method)
  Pure projection     = away_siera x park_factor        (park-neutral method)

A large delta means the model is double-counting the home park effect
into both the SIERA input AND the park factor multiplier.

Run: python mlb/siera_purity_diagnostic.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import statsapi
from park_factors import get_park_factor
from run_daily_f5 import _calc_siera, _parse_ip, FALLBACK_FIP

TODAY = "07/12/2026"  # change if needed
SPORT_ID = 11         # 11=AAA, 12=AA

# Extreme parks where home/away split matters most
EXTREME_PARKS = {
    "Las Vegas Ballpark":            1.375,
    "Southwest University Park":     1.297,
    "Isotopes Park":                 1.328,
    "CHS Field":                     1.177,
    "Louisville Slugger Field":      1.100,
    "Cheney Stadium":                0.919,
    "Constellation Field":           0.775,
    "Sahlen Field":                  0.830,
    "PNC Field":                     0.900,
    "Gwinnett Field":                0.768,
}


def _fetch_split_siera(player_id: int, season: int, split_type: str) -> tuple[float, float]:
    """
    Fetch SIERA for a player split by 'home' or 'away'.
    split_type: 'home' or 'away'
    Returns (siera, ip).
    """
    try:
        raw = statsapi.get('people', {
            'personIds': player_id,
            'hydrate': f'stats(group=[pitching],type=homeAndAway,season={season})'
        })
        for person in raw.get('people', []):
            for stat_grp in person.get('stats', []):
                for split in stat_grp.get('splits', []):
                    if split.get('split', {}).get('code', '').lower() == split_type[0]:
                        stats = split.get('stat', {})
                        ip    = _parse_ip(stats.get('inningsPitched', '0'))
                        siera = _calc_siera(stats)
                        return (siera or FALLBACK_FIP, ip)
    except Exception:
        pass
    return (FALLBACK_FIP, 0.0)


def _fetch_combined_siera(player_id: int, season: int) -> tuple[float, float]:
    """Fetch combined (home+away) SIERA for a player."""
    try:
        raw = statsapi.get('people', {
            'personIds': player_id,
            'hydrate': f'stats(group=[pitching],type=season,season={season})'
        })
        for person in raw.get('people', []):
            for stat_grp in person.get('stats', []):
                splits = stat_grp.get('splits', [])
                if splits:
                    stats = splits[0].get('stat', {})
                    ip    = _parse_ip(stats.get('inningsPitched', '0'))
                    siera = _calc_siera(stats)
                    return (siera or FALLBACK_FIP, ip)
    except Exception:
        pass
    return (FALLBACK_FIP, 0.0)


def audit_pitcher(name: str, player_id: int, venue: str, is_home: bool, season: int = 2026):
    comb_siera, comb_ip  = _fetch_combined_siera(player_id, season)
    away_siera, away_ip  = _fetch_split_siera(player_id, season, 'away')
    home_siera, home_ip  = _fetch_split_siera(player_id, season, 'home')

    pf = get_park_factor(venue)

    # F5 proxy: SIERA / 9 * 5 * park_factor  (simplified, directional)
    model_f5 = round((comb_siera / 9) * 5 * pf, 3)
    pure_f5  = round((away_siera  / 9) * 5 * pf, 3)
    delta    = round(pure_f5 - model_f5, 3)

    home_pct = round((home_ip / comb_ip * 100) if comb_ip > 0 else 0, 1)
    flag     = ""
    if abs(delta) >= 0.15:
        flag = " << SIGNIFICANT"
    elif abs(delta) >= 0.08:
        flag = " < notable"

    role = "HP" if is_home else "AP"
    print(f"  [{role}] {name:<28} IP={comb_ip:5.1f} ({home_pct}% home)")
    print(f"         Combined SIERA: {comb_siera:.2f}  |  Away SIERA: {away_siera:.2f}  |  Home SIERA: {home_siera:.2f}")
    print(f"         Model F5: {model_f5:.3f}  |  Pure F5: {pure_f5:.3f}  |  Delta: {delta:+.3f}{flag}")
    print()

    return {
        "pitcher": name,
        "role": role,
        "venue": venue,
        "pf": pf,
        "combined_siera": comb_siera,
        "away_siera": away_siera,
        "home_siera": home_siera,
        "home_pct": home_pct,
        "model_f5": model_f5,
        "pure_f5": pure_f5,
        "delta": delta,
        "ip": comb_ip,
    }


def main():
    print(f"\n{'='*70}")
    print(f"  SIERA PURITY DIAGNOSTIC -- {TODAY} -- Sport {SPORT_ID}")
    print(f"  Checks home/away SIERA splits to detect park double-counting")
    print(f"{'='*70}\n")

    sched = statsapi.get('schedule', {
        'sportId': SPORT_ID,
        'date':    TODAY,
        'hydrate': 'probablePitcher,linescore',
    })

    results = []
    for date_obj in sched.get('dates', []):
        for g in date_obj.get('games', []):
            venue     = g.get('venue', {}).get('name', 'Unknown')
            pf        = get_park_factor(venue)
            away_team = g['teams']['away']['team']['name']
            home_team = g['teams']['home']['team']['name']
            ap_data   = g['teams']['away'].get('probablePitcher', {})
            hp_data   = g['teams']['home'].get('probablePitcher', {})

            print(f"\n{'-'*70}")
            print(f"  {away_team} @ {home_team}  |  {venue}  |  PF={pf:.3f}")
            print(f"{'-'*70}")

            for pd, is_home in [(ap_data, False), (hp_data, True)]:
                if not pd:
                    print(f"  [{'HP' if is_home else 'AP'}] TBD\n")
                    continue
                r = audit_pitcher(
                    name      = pd.get('fullName', 'Unknown'),
                    player_id = pd.get('id'),
                    venue     = venue,
                    is_home   = is_home,
                )
                results.append(r)

    # Summary: biggest double-counting risks
    print(f"\n{'='*70}")
    print("  SUMMARY -- Pitchers with significant home/away SIERA divergence")
    print(f"{'='*70}")
    flagged = [r for r in results if abs(r['delta']) >= 0.08]
    if flagged:
        flagged.sort(key=lambda x: abs(x['delta']), reverse=True)
        print(f"  {'Pitcher':<28} {'Role':>4} {'PF':>5} {'CombSIERA':>10} {'AwaySIERA':>10} {'Delta':>7} {'Home%':>6}")
        print(f"  {'-'*75}")
        for r in flagged:
            sign = "+" if r['delta'] >= 0 else ""
            print(f"  {r['pitcher']:<28} {r['role']:>4} {r['pf']:>5.3f} "
                  f"{r['combined_siera']:>10.2f} {r['away_siera']:>10.2f} "
                  f"{sign}{r['delta']:>6.3f} {r['home_pct']:>5.1f}%")
    else:
        print("  No significant divergences found today.")

    # Overall stats
    if results:
        avg_delta = sum(abs(r['delta']) for r in results) / len(results)
        max_delta = max(abs(r['delta']) for r in results)
        print(f"\n  Avg |delta| across all pitchers: {avg_delta:.3f}")
        print(f"  Max |delta|: {max_delta:.3f}")
        print(f"  Pitchers audited: {len(results)}")

    print()


if __name__ == '__main__':
    main()
