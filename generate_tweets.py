"""
generate_tweets.py
══════════════════
Reads today's football prediction JSON and generates 3 formatted X (Twitter)
posts ready for copy-paste or automated posting via the X API.

Posts generated:
  1. Top 5 BTTS Value Picks   (ranked by model edge over the market)
  2. Top 5 Multi-Market Best  (composite score across BTTS + 1X2 + consensus)
  3. High Confidence Board    (all games where any market >= THRESHOLD%)

Usage:
  python generate_tweets.py                        # today
  python generate_tweets.py --date 2026-08-25      # specific date
  python generate_tweets.py --threshold 75         # raise confidence floor
  python generate_tweets.py --min-odds 1.15        # stricter value filter
  python generate_tweets.py --output tweets.txt    # save to file
  python generate_tweets.py --post                 # auto-post via X API (requires .env keys)
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ── Constants ─────────────────────────────────────────────────────────────────

SITE_URL   = "blowrout.com"
DATA_DIR   = os.path.join(os.path.dirname(__file__), "data", "football")

# BTTS decisions the model considers an active YES play
BTTS_PLAY_DECISIONS = {"PLAY YES", "[STRONG] PLAY YES"}

# Minimum odds for a pick to be "interesting" on social media.
# Filters out 1.02 sure-things that read as noise.
DEFAULT_MIN_ODDS  = 1.10
DEFAULT_THRESHOLD = 70   # % confidence floor for Post 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(val, default=0.0):
    """Return val as float, or default if None/missing."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def btts_no_prob(p):
    """BTTS-No probability = 100 - btts_prob (BTTS-Yes prob)."""
    return 100.0 - _safe(p.get("btts_prob", 50))


def get_btts_market_odds(p):
    """Return market odds for BTTS YES."""
    mo = p.get("market_odds") or {}
    return _safe(mo.get("btts_yes_odds") or mo.get("btts_market_prob"))


def real_market_edge(p):
    """
    True edge = model BTTS-YES probability minus implied probability from
    actual bookmaker BTTS-YES odds.  Falls back to stored btts_edge if
    no market odds are available (e.g. smaller leagues).
    """
    mkt_odds = get_btts_market_odds(p)
    if mkt_odds > 1.0:
        implied = (1 / mkt_odds) * 100      # e.g. 1/1.25 = 80%
        return round(_safe(p.get("btts_prob", 0)) - implied, 1)
    # Fallback: stored edge (calculated against 0.52 baseline)
    return _safe(p.get("btts_edge", 0))


def is_value_btts(p, min_odds=DEFAULT_MIN_ODDS):
    """True if game has an active BTTS YES play with real positive edge and decent odds."""
    decision = p.get("btts_decision", "")
    if decision not in BTTS_PLAY_DECISIONS:
        return False
    if real_market_edge(p) <= 0:
        return False
    mkt_odds = get_btts_market_odds(p)
    return mkt_odds >= min_odds


def btts_display(p):
    """Always BTTS YES (NO plays are filtered out)."""
    return "BTTS YES"


def best_1x2(p):
    """Return (side_label, prob%, odds) for the strongest 1X2 side."""
    home_prob = _safe(p.get("home_win_prob", 0))
    away_prob = _safe(p.get("away_win_prob", 0))
    draw_prob = _safe(p.get("draw_prob_1x2", 0))

    if home_prob >= away_prob and home_prob >= draw_prob:
        return "HOME", home_prob, _safe(p.get("home_win_odds"))
    elif away_prob >= home_prob and away_prob >= draw_prob:
        return "AWAY", away_prob, _safe(p.get("away_win_odds"))
    else:
        return "DRAW", draw_prob, _safe(p.get("draw_odds"))


def composite_score(p, min_odds=DEFAULT_MIN_ODDS):
    """
    Composite ranking score for Post 2.
    Combines BTTS edge, 1X2 dominance, and consensus alignment.
    """
    score = 0.0

    # BTTS signal (up to 50 pts) — uses real market edge
    if p.get("btts_decision") in BTTS_PLAY_DECISIONS:
        edge = real_market_edge(p)
        score += max(0, edge) * 2.5   # e.g. edge=10 → +25 pts

    # 1X2 dominance signal (up to 40 pts)
    side, prob, odds = best_1x2(p)
    if prob >= 65 and odds >= min_odds:
        score += (prob - 65) * 1.5    # e.g. prob=80 → +22.5 pts

    # Consensus alignment bonus (up to 10 pts)
    consensus = p.get("api_consensus") or {}
    c_winner = consensus.get("consensus_winner", "")
    predicted = p.get("predicted_result", "")
    if c_winner and predicted and c_winner.upper() == predicted.upper():
        score += 10.0

    # Penalise very short odds (boring for social)
    _, _, top_odds = best_1x2(p)
    if top_odds < min_odds:
        score *= 0.5

    return round(score, 2)


def shorten(name, max_len=22):
    """Truncate long team names with ellipsis."""
    return name if len(name) <= max_len else name[:max_len - 1] + "…"


# ── Post Generators ───────────────────────────────────────────────────────────

def post_btts_top5(preds, min_odds=DEFAULT_MIN_ODDS, n=5):
    """Post 1 — Top N BTTS value picks ranked by real market edge."""
    candidates = [p for p in preds if is_value_btts(p, min_odds)]
    candidates.sort(key=lambda p: real_market_edge(p), reverse=True)
    picks = candidates[:n]

    date_str = datetime.now().strftime("%d %b %Y")
    lines = [
        f"⚽ BTTS TOP {n} — {date_str}",
        f"Our model's highest-edge BTTS plays today:\n",
    ]

    for i, p in enumerate(picks, 1):
        ht = shorten(p["home_team"])
        at = shorten(p["away_team"])
        label    = btts_display(p)
        prob     = round(_safe(p.get("btts_prob", 0)), 1)
        edge     = real_market_edge(p)
        league   = p.get("league", "")
        kick     = str(p.get("kickoff", ""))[-5:]   # HH:MM portion
        icon     = "🟢" if "STRONG" in p.get("btts_decision", "") else "🔵"
        mkt_odds = get_btts_market_odds(p)
        odds_str = f" | Odds: {mkt_odds:.2f}" if mkt_odds > 1.0 else ""
        edge_str = f"+{edge:.1f}%" if edge > 0 else f"{edge:.1f}%"

        lines.append(
            f"{icon} {i}. {ht} vs {at}\n"
            f"   {label} | Model: {prob}% | Edge: {edge_str}{odds_str}\n"
            f"   {league} | KO: {kick}"
        )

    lines += [
        f"\nFull analysis 👉 {SITE_URL}",
        "#Football #Predictions #BTTS #SportsBetting"
    ]
    return "\n".join(lines)


def post_composite_top5(preds, min_odds=DEFAULT_MIN_ODDS, n=5):
    """Post 2 — Top N picks by composite multi-market score."""
    scored = [(p, composite_score(p, min_odds)) for p in preds]
    scored.sort(key=lambda x: x[1], reverse=True)
    picks = [p for p, s in scored[:n]]

    date_str = datetime.now().strftime("%d %b %Y")
    lines = [
        f"🧠 MODEL'S BEST {n} — {date_str}",
        f"Highest-scoring picks across all markets:\n",
    ]

    for i, p in enumerate(picks, 1):
        ht = shorten(p["home_team"])
        at = shorten(p["away_team"])
        league = p.get("league", "")
        kick   = str(p.get("kickoff", ""))[-5:]

        # Determine primary market to highlight
        decision = p.get("btts_decision", "")
        side, prob_1x2, odds_1x2 = best_1x2(p)

        btts_real_edge = real_market_edge(p)
        has_btts_play = decision in BTTS_PLAY_DECISIONS and btts_real_edge > 0

        if has_btts_play and btts_real_edge >= (prob_1x2 - 65) * 0.5:
            # BTTS is the stronger signal
            label = btts_display(p)
            prob  = _safe(p.get("btts_prob", 0)) if "YES" in label else btts_no_prob(p)
            mkt   = get_btts_market_odds(p)
            detail = f"{label} | {prob:.0f}% | Odds: {mkt:.2f}" if mkt > 1 else f"{label} | {prob:.0f}%"
        else:
            # 1X2 is the stronger signal
            detail = f"{side} WIN | {prob_1x2:.0f}% | Odds: {odds_1x2:.2f}"

        # Consensus alignment note
        consensus = p.get("api_consensus") or {}
        c_winner = consensus.get("consensus_winner", "")
        predicted = p.get("predicted_result", "")
        aligned = "✅" if (c_winner and predicted and c_winner.upper() == predicted.upper()) else ""

        cs = composite_score(p, min_odds)
        lines.append(
            f"{i}. {ht} vs {at} {aligned}\n"
            f"   {detail}\n"
            f"   {league} | KO: {kick} | Score: {cs:.0f}"
        )

    lines += [
        f"\nFull picks 👉 {SITE_URL}",
        "#Football #Predictions #ValueBets #SportsBetting"
    ]
    return "\n".join(lines)


def post_confidence_board(preds, threshold=DEFAULT_THRESHOLD, min_odds=DEFAULT_MIN_ODDS):
    """Post 3 — All games where any market >= threshold%."""
    home_wins, away_wins, btts_yes, btts_no, draws = [], [], [], [], []

    for p in preds:
        home_prob = _safe(p.get("home_win_prob", 0))
        away_prob = _safe(p.get("away_win_prob", 0))
        draw_prob = _safe(p.get("draw_prob_1x2", 0))
        b_yes_prob = _safe(p.get("btts_prob", 0))
        home_odds  = _safe(p.get("home_win_odds"))
        away_odds  = _safe(p.get("away_win_odds"))
        draw_odds  = _safe(p.get("draw_odds"))

        ht = shorten(p["home_team"])
        at = shorten(p["away_team"])
        league = p.get("league", "")
        kick   = str(p.get("kickoff", ""))[-5:]

        def row(label, prob, odds):
            o = f" @ {odds:.2f}" if odds >= min_odds else ""
            return f"  ✅ {ht} vs {at} | {label} {prob:.0f}%{o} | {league}"

        if home_prob >= threshold and home_odds >= min_odds:
            home_wins.append((home_prob, row("HOME", home_prob, home_odds)))
        if away_prob >= threshold and away_odds >= min_odds:
            away_wins.append((away_prob, row("AWAY", away_prob, away_odds)))
        if b_yes_prob >= threshold:
            btts_yes.append((b_yes_prob, row("BTTS YES", b_yes_prob, 0)))
        if draw_prob >= threshold and draw_odds >= min_odds:
            draws.append((draw_prob, row("DRAW", draw_prob, draw_odds)))

    # Sort each bucket by prob descending
    for lst in (home_wins, away_wins, btts_yes, btts_no, draws):
        lst.sort(key=lambda x: x[0], reverse=True)

    total = sum(len(lst) for lst in (home_wins, away_wins, btts_yes, btts_no, draws))
    date_str = datetime.now().strftime("%d %b %Y")

    lines = [
        f"📊 {threshold}%+ CONFIDENCE BOARD — {date_str}",
        f"{total} picks hit the threshold today:\n",
    ]

    if home_wins:
        lines.append("🏠 HOME WINS:")
        lines += [r for _, r in home_wins]
    if away_wins:
        lines.append("\n✈️ AWAY WINS:")
        lines += [r for _, r in away_wins]
    if btts_yes:
        lines.append("\n🟢 BTTS YES:")
        lines += [r for _, r in btts_yes]
    if btts_no:
        lines.append("\n🔴 BTTS NO:")
        lines += [r for _, r in btts_no]
    if draws:
        lines.append("\n➖ DRAWS:")
        lines += [r for _, r in draws]

    if total == 0:
        lines.append(f"No picks above {threshold}% today.")

    lines += [
        f"\nFull dashboard 👉 {SITE_URL}",
        "#Football #Predictions #SportsBetting"
    ]
    return "\n".join(lines)


# ── Results Post (Yesterday's grading) ───────────────────────────────────────

def post_results(preds_yesterday, yesterday_date_str=None):
    """Post 4 — Grade yesterday's BTTS YES picks with per-game detail."""
    # Only grade BTTS YES plays that have been resolved
    plays = [
        p for p in preds_yesterday
        if p.get("btts_decision") in BTTS_PLAY_DECISIONS
        and p.get("actual_btts") is not None
    ]
    if not plays:
        return None

    wins   = [p for p in plays if p.get("actual_btts") is True]
    losses = [p for p in plays if p.get("actual_btts") is False]
    total  = len(plays)
    correct = len(wins)
    pct    = round(correct / total * 100) if total else 0

    icon = "🟢" if pct >= 60 else ("🟡" if pct >= 50 else "🔴")
    date_label = yesterday_date_str or "Yesterday"

    lines = [
        f"📋 BTTS RESULTS — {date_label}",
        f"{icon} {correct}/{total} correct ({pct}%)\n",
    ]

    if wins:
        lines.append("✅ Won:")
        for p in wins:
            ht = shorten(p["home_team"], 20)
            at = shorten(p["away_team"], 20)
            hg = p.get("actual_home_goals", "?")
            ag = p.get("actual_away_goals", "?")
            prob = _safe(p.get("btts_prob", 0))
            lines.append(f"  ✅ {ht} vs {at} — {hg}-{ag} ({prob:.0f}%)")

    if losses:
        lines.append("\n❌ Lost:")
        for p in losses:
            ht = shorten(p["home_team"], 20)
            at = shorten(p["away_team"], 20)
            hg = p.get("actual_home_goals", "?")
            ag = p.get("actual_away_goals", "?")
            prob = _safe(p.get("btts_prob", 0))
            lines.append(f"  ❌ {ht} vs {at} — {hg}-{ag} ({prob:.0f}%)")

    lines += [
        f"\nFull record 👉 {SITE_URL}",
        "#Football #Results #Accountability"
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def load_predictions(date_str):
    """Load predictions JSON for a given date string (YYYY-MM-DD)."""
    path = os.path.join(DATA_DIR, f"universal_predictions_{date_str}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No predictions file found for {date_str}: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("predictions", [])


def main():
    parser = argparse.ArgumentParser(description="Generate X posts from football predictions")
    parser.add_argument("--date",      default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        help="Date to generate posts for (YYYY-MM-DD)")
    parser.add_argument("--yesterday", default=None,
                        help="Date of yesterday's file for results post (YYYY-MM-DD)")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help=f"Confidence floor for Post 3 (default {DEFAULT_THRESHOLD})")
    parser.add_argument("--min-odds",  type=float, default=DEFAULT_MIN_ODDS,
                        help=f"Minimum odds to include a pick (default {DEFAULT_MIN_ODDS})")
    parser.add_argument("--top-n",     type=int, default=5,
                        help="Number of picks for Posts 1 and 2 (default 5)")
    parser.add_argument("--output",    default=None,
                        help="Save posts to a specific file path")
    parser.add_argument("--save",      action="store_true",
                        help="Auto-save posts to tweets/tweets_YYYY-MM-DD.txt (always also prints to console)")
    parser.add_argument("--post",      action="store_true",
                        help="Auto-post to X via API (requires X_API_* env vars)")
    args = parser.parse_args()

    print(f"Loading predictions for {args.date}...")
    preds = load_predictions(args.date)
    print(f"  {len(preds)} predictions loaded.")

    separator = "\n" + "─" * 60 + "\n"

    post1 = post_btts_top5(preds,        min_odds=args.min_odds, n=args.top_n)
    post2 = post_composite_top5(preds,   min_odds=args.min_odds, n=args.top_n)
    post3 = post_confidence_board(preds, threshold=args.threshold, min_odds=args.min_odds)

    posts = [
        ("POST 3 — High Confidence Board (post first, highest reach)", post3),
        ("POST 1 — BTTS Top 5 Value Picks",                           post1),
        ("POST 2 — Multi-Market Top 5",                               post2),
    ]

    # Optional: results post from yesterday
    if args.yesterday:
        try:
            y_preds = load_predictions(args.yesterday)
            from datetime import datetime as _dt
            y_label = _dt.strptime(args.yesterday, "%Y-%m-%d").strftime("%d %b %Y")
            post4   = post_results(y_preds, yesterday_date_str=y_label)
            if post4:
                posts.insert(0, ("POST 4 — Yesterday's Results (post first)", post4))

        except FileNotFoundError as e:
            print(f"  [warn] {e}")

    output_lines = []
    for title, content in posts:
        block = f"{'=' * 60}\n{title}\n{'=' * 60}\n\n{content}"
        output_lines.append(block)
    full_output = ("\n" + separator).join(output_lines)

    # Always print to console
    print("\n" + full_output)

    # Save to file if --output or --save specified
    if args.output:
        save_path = args.output
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(full_output)
        print(f"\n✅ Posts saved to {save_path}")
    elif args.save:
        tweets_dir = os.path.join(os.path.dirname(__file__), "tweets")
        os.makedirs(tweets_dir, exist_ok=True)
        save_path = os.path.join(tweets_dir, f"tweets_{args.date}.txt")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(full_output)
        print(f"\n✅ Posts saved to {save_path}")

    # ── X API auto-posting (optional) ────────────────────────────────────────
    if args.post:
        _post_to_x([content for _, content in posts])


def _post_to_x(posts):
    """Post each tweet via the X API v2 using tweepy."""
    try:
        import tweepy
    except ImportError:
        print("\n[ERROR] tweepy not installed. Run: pip install tweepy")
        return

    from dotenv import load_dotenv
    load_dotenv()

    required = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    missing  = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"\n[ERROR] Missing X API env vars: {', '.join(missing)}")
        print("Add them to your .env file or GitHub secrets.")
        return

    client = tweepy.Client(
        consumer_key        = os.getenv("X_API_KEY"),
        consumer_secret     = os.getenv("X_API_SECRET"),
        access_token        = os.getenv("X_ACCESS_TOKEN"),
        access_token_secret = os.getenv("X_ACCESS_SECRET"),
    )

    for i, text in enumerate(posts, 1):
        try:
            response = client.create_tweet(text=text[:280])
            print(f"  [✓] Post {i} published. Tweet ID: {response.data['id']}")
        except Exception as e:
            print(f"  [✗] Post {i} failed: {e}")


if __name__ == "__main__":
    main()
