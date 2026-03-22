"""
audit_basketball.py
───────────────────
Comprehensive terminal audit of basketball prediction performance.
Reads local prediction JSON files — no API calls, no frontend needed.

Usage:
    python audit_basketball.py --date 2026-03-21
    python audit_basketball.py --from 2026-03-19 --to 2026-03-21
    python audit_basketball.py --from 2026-03-19 --to 2026-03-21 --league "NBA"
    python audit_basketball.py --from 2026-03-19 --to 2026-03-21 --tier BUST
    python audit_basketball.py --from 2026-03-19 --to 2026-03-21 --sort delta
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DATA_DIR = Path(__file__).parent / "data" / "basketball"

TIER_ORDER = {"BULLSEYE": 0, "EXCELLENT": 1, "SOLID": 2, "MISS": 3, "BUST": 4, "OT WARP": 5}

# ── ANSI colours ───────────────────────────────────────────────────────────────
R  = "\033[91m"   # red
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
B  = "\033[94m"   # blue
M  = "\033[95m"   # magenta
C  = "\033[96m"   # cyan
W  = "\033[97m"   # white
DIM= "\033[2m"    # dim
BO = "\033[1m"    # bold
RS = "\033[0m"    # reset

def col(text, *codes): return "".join(codes) + str(text) + RS

def tier_color(tier):
    if not tier: return RS
    if "BULLSEYE"  in tier: return M
    if "EXCELLENT" in tier: return G
    if "SOLID"     in tier: return Y
    if "MISS"      in tier: return "\033[33m"   # orange-ish
    if "BUST"      in tier: return R
    if "OT"        in tier: return C
    return RS

def pct_color(p):
    if p is None: return DIM
    if p >= 60: return G
    if p >= 45: return Y
    return R

def pct(n, total):
    if not total: return None
    return round(n / total * 100)

def fmt_signed(v):
    if v is None: return col("—", DIM)
    s = f"{v:+.1f}"
    return col(s, G) if v < 0 else col(s, R)

def tier_key(tier):
    if not tier: return 9
    for k, v in TIER_ORDER.items():
        if k in tier: return v
    return 9

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_model_total(p):
    """Basketball stores model total as top-level 'model_total' OR nested 'model.total'."""
    mt = p.get("model_total")
    if mt: return mt
    nested = p.get("model")
    if isinstance(nested, dict): return nested.get("total")
    return None

# ── Load files ─────────────────────────────────────────────────────────────────

def date_range(start: str, end: str):
    d = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end,   "%Y-%m-%d")
    while d <= e:
        yield d.strftime("%Y-%m-%d")
        d += timedelta(days=1)

def load_predictions(start: str, end: str):
    all_preds = []
    dates_loaded = []
    for date in date_range(start, end):
        path = DATA_DIR / f"universal_predictions_{date}.json"
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        preds = data.get("predictions", [])
        for p in preds:
            p["_date"] = date
        all_preds.extend(preds)
        dates_loaded.append(date)
    return all_preds, dates_loaded

# ── Report sections ────────────────────────────────────────────────────────────

def section(title):
    print(f"\n{col('═' * 60, DIM)}")
    print(f"  {col(title, BO, W)}")
    print(col('═' * 60, DIM))

def print_kpis(graded, pending):
    wins   = [p for p in graded if p.get("predicted_result") == p.get("actual_result")]
    losses = [p for p in graded if p.get("predicted_result") != p.get("actual_result")]
    win_rate = pct(len(wins), len(graded))

    with_delta  = [p for p in graded if p.get("total_delta") is not None and "OT" not in (p.get("accuracy_tier") or "")]
    with_signed = [p for p in graded if p.get("signed_delta") is not None]

    avg_delta  = sum(p["total_delta"]  for p in with_delta)  / len(with_delta)  if with_delta  else None
    avg_signed = sum(p["signed_delta"] for p in with_signed) / len(with_signed) if with_signed else None

    # Count graded games that have model total (for % of graded with tier data)
    with_model = [p for p in graded if get_model_total(p)]

    wr_c = pct_color(win_rate)
    print(f"\n  {'Games graded':<26} {col(len(graded), BO, W)}   ({col(len(pending), DIM)} pending)")
    print(f"  {'Winner accuracy':<26} {col(f'{win_rate}%', BO, wr_c)}   {col(f'{len(wins)}W – {len(losses)}L', DIM)}")
    if with_delta:
        avg_d_val = avg_delta
        delta_c = G if avg_d_val <= 8.5 else Y if avg_d_val <= 14.5 else R
        print(f"  {'Avg abs delta (Δ)':<26} {col(f'{avg_d_val:.1f} pts', BO, delta_c)}   {col(f'from {len(with_delta)} graded totals', DIM)}")
    else:
        print(f"  {'Avg abs delta (Δ)':<26} {col('No graded totals yet — run grade_basketball.py', DIM)}")
    if avg_signed is not None:
        bias = "model UNDERSHOOTS (games go Over)" if avg_signed > 0 else "model OVERSHOOTS (games go Under)"
        print(f"  {'Avg signed delta':<26} {fmt_signed(avg_signed)}   {col(bias, DIM)}")
    elif with_delta:
        print(f"  {'Avg signed delta':<26} {col('Run: python grade_basketball.py --regrade --date <date>', DIM)}")

def print_tier_distribution(graded):
    with_delta = [p for p in graded if p.get("total_delta") is not None and "OT" not in (p.get("accuracy_tier") or "")]
    ots        = [p for p in graded if "OT" in (p.get("accuracy_tier") or "")]
    total      = len(with_delta)
    if not total: print(col("  No graded totals data.", DIM)); return

    tiers = [
        ("🎯 BULLSEYE",  "BULLSEYE",  M),
        ("🟢 EXCELLENT", "EXCELLENT", G),
        ("🟡 SOLID",     "SOLID",     Y),
        ("🟠 MISS",      "MISS",      "\033[33m"),
        ("🔴 BUST",      "BUST",      R),
    ]
    bar_width = 30
    for label, key, c in tiers:
        count = sum(1 for p in with_delta if p.get("accuracy_tier") and key in p["accuracy_tier"])
        frac  = count / total
        filled = round(frac * bar_width)
        bar   = col("█" * filled, c) + col("░" * (bar_width - filled), DIM)
        p_val = round(frac * 100)
        print(f"  {label:<16} {bar}  {col(count, BO):>3}  {col(f'{p_val}%', DIM)}")
    if ots:
        print(f"  {'🚨 OT WARP':<16} {'':30}  {col(len(ots), BO, C)}")

def print_league_breakdown(graded):
    leagues = {}
    for p in graded:
        key = p.get("league", "Unknown")
        if key not in leagues:
            leagues[key] = {"w": 0, "l": 0, "deltas": [], "signed": []}
        entry = leagues[key]
        if p.get("predicted_result") == p.get("actual_result"): entry["w"] += 1
        else:                                                     entry["l"] += 1
        if p.get("total_delta") is not None and "OT" not in (p.get("accuracy_tier") or ""):
            entry["deltas"].append(p["total_delta"])
        if p.get("signed_delta") is not None:
            entry["signed"].append(p["signed_delta"])

    rows = []
    for name, s in leagues.items():
        total = s["w"] + s["l"]
        wr    = pct(s["w"], total)
        avg_d = sum(s["deltas"]) / len(s["deltas"]) if s["deltas"] else None
        avg_s = sum(s["signed"]) / len(s["signed"]) if s["signed"] else None
        bias  = ("Under" if avg_s and avg_s > 3 else "Over" if avg_s and avg_s < -3 else "Neutral") if avg_s is not None else "—"
        rows.append((name, s["w"], s["l"], wr, avg_d, avg_s, bias))

    rows.sort(key=lambda r: -(r[1] + r[2]))

    # Fixed-width columns — pad BEFORE colorizing
    C1, C2, C3, C4, C5, C6, C7 = 30, 4, 4, 6, 7, 9, 10
    hdr = (f"  {'LEAGUE':<{C1}} {'W':>{C2}} {'L':>{C3}} {'WIN%':>{C4}} "
           f"{'AVG Δ':>{C5}} {'SIGNED Δ':>{C6}}  {'BIAS':<{C7}}")
    print(col(hdr, DIM))
    print(col("  " + "─" * (C1+C2+C3+C4+C5+C6+C7+10), DIM))

    for name, w, l, wr, avg_d, avg_s, bias in rows:
        name_s  = name[:C1].ljust(C1)
        w_s     = str(w).rjust(C2)
        l_s     = str(l).rjust(C3)
        wr_s    = (f"{wr}%").rjust(C4) if wr is not None else "—".rjust(C4)
        d_s     = f"{avg_d:.1f}".rjust(C5) if avg_d is not None else "—".rjust(C5)
        signed_raw = (f"{avg_s:+.1f}") if avg_s is not None else "—"
        s_s        = signed_raw.rjust(C6)
        bias_icon  = ("📉 " if bias == "Under" else "📈 " if bias == "Over" else "✅ ") + bias
        bias_s  = bias_icon.ljust(C7)

        # Now apply colours
        w_c    = col(w_s, G)
        l_c    = col(l_s, R)
        wr_c   = col(wr_s, pct_color(wr))
        s_c    = col(s_s, R if (avg_s or 0) > 0 else G if (avg_s or 0) < 0 else DIM)

        print(f"  {col(name_s, BO)}  {w_c}  {l_c}  {wr_c}  {d_s}  {s_c}  {bias_s}")

def print_team_breakdown(graded, min_games=3):
    """
    Build a per-team performance table and surface standout teams.
    Each game contributes twice — once as home team, once as away team.
    min_games: minimum appearances before a team is shown.
    """
    teams = {}

    for p in graded:
        is_win  = p.get("predicted_result") == p.get("actual_result")
        delta   = p.get("total_delta")
        signed  = p.get("signed_delta")
        ot      = "OT" in (p.get("accuracy_tier") or "")
        tier    = p.get("accuracy_tier") or ""

        for role, key in [("home", p.get("home_team")), ("away", p.get("away_team"))]:
            if not key: continue
            if key not in teams:
                teams[key] = {"w": 0, "l": 0, "deltas": [], "signed": [], "tiers": [], "league": p.get("league", "")}
            entry = teams[key]
            if is_win:  entry["w"] += 1
            else:       entry["l"] += 1
            if delta  is not None and not ot: entry["deltas"].append(delta)
            if signed is not None:            entry["signed"].append(signed)
            entry["tiers"].append(tier)

    # Build rows
    rows = []
    for name, s in teams.items():
        total = s["w"] + s["l"]
        if total < min_games:
            continue
        wr    = pct(s["w"], total)
        avg_d = sum(s["deltas"]) / len(s["deltas"]) if s["deltas"] else None
        avg_s = sum(s["signed"]) / len(s["signed"]) if s["signed"] else None
        bullseyes = sum(1 for t in s["tiers"] if "BULLSEYE" in t)
        busts     = sum(1 for t in s["tiers"] if "BUST"     in t)
        rows.append({
            "name": name, "w": s["w"], "l": s["l"], "total": total,
            "wr": wr, "avg_d": avg_d, "avg_s": avg_s,
            "bullseyes": bullseyes, "busts": busts, "league": s["league"]
        })

    if not rows:
        print(col(f"  No team appeared ≥{min_games} times. Widen your date range.", DIM))
        return

    rows.sort(key=lambda r: -(r["w"] + r["l"]))

    # ── Auto-detect cash cows and problem cases ──────────────────────────────
    cash_teams    = [r for r in rows if (r["wr"] or 0) >= 75 and (r["avg_d"] or 999) <= 10]
    problem_teams = [r for r in rows if (r["avg_d"] or 0) >= 18 or
                     (r["avg_s"] is not None and abs(r["avg_s"]) >= 10)]

    if cash_teams:
        print(f"\n  {col('💰  CASH TEAMS  (Win rate ≥75% + Avg Δ ≤10)', BO, G)}")
        for r in sorted(cash_teams, key=lambda x: -(x["wr"] or 0)):
            wr_s   = f"{r['wr']}%".rjust(4)
            d_s    = f"{r['avg_d']:.1f}".rjust(5) if r["avg_d"] is not None else "  —  "
            league = r["league"][:28]
            print(f"    {col('★', G, BO)} {col(r['name'][:30].ljust(30), BO, G)}  "
                  f"{col(r['w'], G)}W-{col(r['l'], R)}L  "
                  f"WR:{col(wr_s, G, BO)}  Δ:{col(d_s, G)}  {col(league, DIM)}")

    if problem_teams:
        print(f"\n  {col('🚨  PROBLEM TEAMS  (Avg Δ ≥18 OR Signed Δ bias ≥±10)', BO, R)}")
        for r in sorted(problem_teams, key=lambda x: -(x["avg_d"] or 0)):
            d_s    = f"{r['avg_d']:.1f}".rjust(5) if r["avg_d"] is not None else "  —  "
            s_raw  = f"{r['avg_s']:+.1f}" if r["avg_s"] is not None else "—"
            bias   = ("model undershoots" if (r["avg_s"] or 0) > 0 else "model overshoots") if r["avg_s"] else ""
            print(f"    {col('⚠', R, BO)} {col(r['name'][:30].ljust(30), BO, R)}  "
                  f"{col(r['w'], G)}W-{col(r['l'], R)}L  "
                  f"Δ:{col(d_s, R)}  ±Δ:{col(s_raw.rjust(6), R)}  {col(bias, DIM)}")

    # ── Full table ───────────────────────────────────────────────────────────
    print(f"\n  {col('ALL TEAMS  (min ' + str(min_games) + ' appearances)', DIM)}")
    C1, C2, C3, C4, C5, C6, C7 = 28, 3, 3, 5, 6, 8, 8
    hdr = (f"  {'TEAM':<{C1}} {'W':>{C2}} {'L':>{C3}} {'WIN%':>{C4}} "
           f"{'AVG Δ':>{C5}} {'SIGNED Δ':>{C6}}  {'🎯':>{C7}}  {'💀':>{C7}}")
    print(col(hdr, DIM))
    print(col("  " + "─" * (C1+C2+C3+C4+C5+C6+C7+16), DIM))

    for r in rows:
        name_s = r["name"][:C1].ljust(C1)
        w_s    = str(r["w"]).rjust(C2)
        l_s    = str(r["l"]).rjust(C3)
        wr_s   = (f"{r['wr']}%").rjust(C4) if r["wr"] is not None else "—".rjust(C4)
        d_s    = f"{r['avg_d']:.1f}".rjust(C5) if r["avg_d"] is not None else "—".rjust(C5)
        s_raw  = f"{r['avg_s']:+.1f}" if r["avg_s"] is not None else "—"
        s_s    = s_raw.rjust(C6)
        bull_s = str(r["bullseyes"]).rjust(C7)
        bust_s = str(r["busts"]).rjust(C7)

        # Flag rows with notable characteristics
        is_cash    = (r["wr"] or 0) >= 75 and (r["avg_d"] or 999) <= 10
        is_problem = (r["avg_d"] or 0) >= 18 or (r["avg_s"] is not None and abs(r["avg_s"]) >= 10)
        flag = col(" ★", G) if is_cash else col(" ⚠", R) if is_problem else "  "

        name_c = col(name_s, G, BO) if is_cash else col(name_s, R) if is_problem else col(name_s, BO)
        w_c    = col(w_s, G)
        l_c    = col(l_s, R)
        wr_c   = col(wr_s, pct_color(r["wr"]))
        s_c    = col(s_s, R if (r["avg_s"] or 0) > 0 else G if (r["avg_s"] or 0) < 0 else DIM)
        bull_c = col(bull_s, M)
        bust_c = col(bust_s, R)

        print(f"  {name_c}  {w_c}  {l_c}  {wr_c}  {d_s}  {s_c}  {bull_c}  {bust_c}{flag}")

def print_game_log(games, sort_mode, filter_result, filter_tier, filter_league):

    filtered = list(games)

    if filter_result == "win":       filtered = [p for p in filtered if p.get("actual_result") and p.get("predicted_result") == p.get("actual_result")]
    elif filter_result == "loss":    filtered = [p for p in filtered if p.get("actual_result") and p.get("predicted_result") != p.get("actual_result")]
    elif filter_result == "pending": filtered = [p for p in filtered if not p.get("actual_result")]

    if filter_tier:
        filtered = [p for p in filtered if (p.get("accuracy_tier") or "").upper().find(filter_tier.upper()) >= 0]
    if filter_league:
        filtered = [p for p in filtered if filter_league.lower() in (p.get("league") or "").lower()]

    if sort_mode == "delta":
        filtered.sort(key=lambda p: p.get("total_delta") or -1, reverse=True)
    elif sort_mode == "tier":
        filtered.sort(key=lambda p: tier_key(p.get("accuracy_tier")))
    else:
        filtered.sort(key=lambda p: p.get("_date", ""))

    print(f"\n  {col(len(filtered), BO)} games shown\n")

    # Column widths (all padding on raw strings, color applied after)
    NC, DC, HC, AC, MC, XC, RC, TC, DLC, SC = 3, 5, 20, 20, 7, 7, 6, 11, 6, 7
    hdr = (f"  {'#':>{NC}}  {'DATE':<{DC}}  {'HOME':<{HC}}  {'AWAY':<{AC}}"
           f"  {'MODEL':>{MC}}  {'ACTUAL':>{XC}}  {'RESULT':<{RC}}  {'TIER':<{TC}}  {'Δ':>{DLC}}  {'±Δ':>{SC}}")
    print(col(hdr, DIM))
    print(col("  " + "─" * (NC+DC+HC+AC+MC+XC+RC+TC+DLC+SC+20), DIM))

    for i, p in enumerate(filtered, 1):
        graded   = p.get("actual_result") is not None
        is_win   = p.get("predicted_result") == p.get("actual_result")
        hs       = p.get("actual_home_score")
        av       = p.get("actual_away_score")
        actual_total = (hs + av) if (hs is not None and av is not None) else None
        tier     = p.get("accuracy_tier") or ""
        tc       = tier_color(tier)
        # Strip emoji from tier for alignment
        tier_short = tier.replace("🎯 ","").replace("🟢 ","").replace("🟡 ","").replace("🟠 ","").replace("🔴 ","").replace("🚨 ","")

        # Build plain padded strings first
        num_s    = str(i).rjust(NC)
        date_s   = (p.get("_date", "")[-5:]).ljust(DC)   # MM-DD
        home_s   = (p.get("home_team") or "")[:HC].ljust(HC)
        away_s   = (p.get("away_team") or "")[:AC].ljust(AC)
        model_total = get_model_total(p)
        model_s  = (f"{model_total:.1f}" if model_total else "—").rjust(MC)
        actual_s = (str(actual_total) if actual_total is not None else "—").rjust(XC)
        result_s = ("WIN" if is_win else "LOSS" if graded else "PEND").ljust(RC)
        # Only show tier/delta if graded and has accuracy data
        has_tier = bool(tier and tier != "—")
        tier_s   = (tier_short[:TC] if has_tier else ("—" if graded else "")).ljust(TC)
        delta_s  = (f"{p['total_delta']:.1f}" if p.get("total_delta") is not None else ("—" if graded else "")).rjust(DLC)
        sgn      = p.get("signed_delta")
        signed_s = ((f"{sgn:+.1f}") if sgn is not None else ("—" if graded else "")).rjust(SC)

        # Apply colour AFTER padding
        result_c = col(result_s, G, BO) if is_win else (col(result_s, R, BO) if graded else col(result_s, DIM))
        signed_c = col(signed_s, R) if (sgn or 0) > 0 else col(signed_s, G) if (sgn or 0) < 0 else col(signed_s, DIM)

        print(f"  {col(num_s, DIM)}  {date_s}  {home_s}  {away_s}"
              f"  {model_s}  {actual_s}  {result_c}  {col(tier_s, tc)}  {delta_s}  {signed_c}")

# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Audit basketball prediction performance (terminal only)")
    parser.add_argument("--date",   help="Single date (YYYY-MM-DD). Shortcut for --from=X --to=X")
    parser.add_argument("--from",   dest="date_from", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to",     dest="date_to",   help="End date (YYYY-MM-DD). Defaults to same as --from")
    parser.add_argument("--league", help="Filter by league name (partial match, case-insensitive)")
    parser.add_argument("--tier",   help="Filter game log by tier (BULLSEYE / EXCELLENT / SOLID / MISS / BUST)")
    parser.add_argument("--result", choices=["win", "loss", "pending"], help="Filter game log by outcome")
    parser.add_argument("--sort",   choices=["date", "delta", "tier"], default="date", help="Sort game log")
    parser.add_argument("--no-log", action="store_true", help="Skip the full game log (faster summary-only view)")
    args = parser.parse_args()

    # Resolve date range
    if args.date:
        start = end = args.date
    elif args.date_from:
        start = args.date_from
        end   = args.date_to or args.date_from
    else:
        parser.error("Provide --date or --from (and optionally --to)")

    print(f"\n{col('▶ BASKETBALL PREDICTION AUDIT', BO, C)}")
    print(col(f"  {start}" + (f"  →  {end}" if end != start else ""), DIM))

    all_preds, dates_loaded = load_predictions(start, end)

    if not dates_loaded:
        print(col(f"\n  ❌ No prediction files found between {start} and {end}.", R))
        return

    print(col(f"  Loaded {len(all_preds)} predictions across {len(dates_loaded)} day(s): {', '.join(dates_loaded)}", DIM))

    # Apply league filter globally if specified
    if args.league:
        all_preds = [p for p in all_preds if args.league.lower() in (p.get("league") or "").lower()]
        print(col(f"  League filter: '{args.league}' → {len(all_preds)} predictions", Y))

    graded  = [p for p in all_preds if p.get("actual_result") is not None]
    pending = [p for p in all_preds if p.get("actual_result") is None]

    if not graded:
        print(col("\n  ⚠️  No graded games in this range. Run grade_basketball.py first.", Y))
        return

    # Section 1: KPIs
    section("📊  OVERALL PERFORMANCE")
    print_kpis(graded, pending)

    # Section 2: Tier distribution
    section("🎯  TOTAL ACCURACY DISTRIBUTION")
    print_tier_distribution(graded)

    # Section 3: League breakdown
    section("🏆  LEAGUE BREAKDOWN")
    print_league_breakdown(graded)

    # Section 4: Team breakdown
    section("👤  TEAM BREAKDOWN")
    print_team_breakdown(graded)

    # Section 5: Game log
    if not args.no_log:
        section("📋  GAME LOG")
        print_game_log(all_preds, args.sort, args.result, args.tier, None)

    print(f"\n{col('═' * 60, DIM)}\n")

if __name__ == "__main__":
    main()
