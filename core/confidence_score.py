"""
core/confidence_score.py
=========================
Model Confidence Score (No Edge) — 75-point system normalized to 100.

Inputs per game:
    vol_a, vol_b     — std_dev_totals for home and away team
    mae_a, mae_b     — per-team historical MAE (model vs actual)
    bias_a, bias_b   — per-team historical bias (model − actual, signed)
    spread           — projected point spread (abs value)

Output:
    confidence_score — 0.0 to 100.0 (higher = more predictable game)
    raw_score        — 0 to 75
    avg_vol, avg_mae, avg_bias_abs — intermediate diagnostics

Usage:
    from core.confidence_score import compute_confidence

    result = compute_confidence({
        "vol_a": 13.5, "vol_b": 14.2,
        "mae_a": 8.1,  "mae_b": 7.4,
        "bias_a": 1.2, "bias_b": -0.8,
        "spread": 6.5
    })
    print(result["confidence_score"])  # e.g. 73.3
"""


# ---------------------------------------------------------------------------
# Scoring rubrics
# ---------------------------------------------------------------------------

def score_volatility(avg_vol: float) -> int:
    """
    Rewards low game-total volatility (std_dev across both teams' histories).

    Thresholds (avg std_dev of combined game totals):
        ≤ 14 pts → 20  (very stable — model loves this)
        ≤ 16 pts → 15
        ≤ 18 pts → 10
        ≤ 20 pts → 5
         > 20 pts → 0  (too chaotic to trust)
    """
    if avg_vol <= 14:
        return 20
    elif avg_vol <= 16:
        return 15
    elif avg_vol <= 18:
        return 10
    elif avg_vol <= 20:
        return 5
    else:
        return 0


def score_mae(avg_mae: float) -> int:
    """
    Rewards low Mean Absolute Error — how tightly the model tracked actuals.

    Thresholds (avg MAE across both teams):
        ≤ 7 pts  → 20
        ≤ 9 pts  → 15
        ≤ 11 pts → 10
        ≤ 13 pts → 5
         > 13 pts → 0
    """
    if avg_mae <= 7:
        return 20
    elif avg_mae <= 9:
        return 15
    elif avg_mae <= 11:
        return 10
    elif avg_mae <= 13:
        return 5
    else:
        return 0


def score_bias(avg_bias_abs: float) -> int:
    """
    Rewards low systematic directional bias (model consistently over/under).
    Uses absolute value of averaged signed bias.

    Thresholds (|avg bias| across both teams):
        ≤ 2 pts → 20  (model is unbiased)
        ≤ 4 pts → 15
        ≤ 6 pts → 10
        ≤ 8 pts → 5
         > 8 pts → 0  (strong systematic bias — avoid)
    """
    if avg_bias_abs <= 2:
        return 20
    elif avg_bias_abs <= 4:
        return 15
    elif avg_bias_abs <= 6:
        return 10
    elif avg_bias_abs <= 8:
        return 5
    else:
        return 0


def score_spread(spread: float) -> int:
    """
    Rewards tighter projected spreads — closer games reduce variance in totals.

    Thresholds (absolute projected point spread):
        < 5  pts → 10  (slight penalty for foul-fest/OT risk)
        ≤ 11 pts → 15  (best zone: competitive, no late fouls)
        ≤ 15 pts → 10  (minor blowout risk)
         > 15 pts → 5   (severe blowout risk, garbage time chaos)
    """
    if spread < 5:
        return 10
    elif spread <= 11:
        return 15
    elif spread <= 15:
        return 10
    else:
        return 5


# ---------------------------------------------------------------------------
# Confidence bands
# ---------------------------------------------------------------------------

CONFIDENCE_BANDS = [
    (90, "[ELITE]   ", "Model is firing on all cylinders -- very high trust"),
    (75, "[HIGH]    ", "Strong confidence -- play with conviction"),
    (60, "[SOLID]   ", "Above-average confidence -- worth monitoring"),
    (45, "[MODERATE]", "Model is uncertain on at least one dimension"),
    (30, "[LOW]     ", "Multiple red flags -- proceed with caution"),
    (0,  "[AVOID]   ", "Model confidence too low -- skip this game"),
]


def get_confidence_band(score: float) -> dict:
    """Return the label and description for a given confidence score."""
    for threshold, label, description in CONFIDENCE_BANDS:
        if score >= threshold:
            return {"label": label, "description": description}
    return {"label": "🔴 AVOID", "description": "Model confidence too low — skip this game"}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_confidence(game: dict) -> dict:
    """
    Compute the Model Confidence Score for a single game.

    Parameters
    ----------
    game : dict
        {
            "vol_a": float,   # std_dev_totals for home team
            "vol_b": float,   # std_dev_totals for away team
            "mae_a": float,   # historical MAE for home team
            "mae_b": float,   # historical MAE for away team
            "bias_a": float,  # historical signed bias for home team (model - actual)
            "bias_b": float,  # historical signed bias for away team (model - actual)
            "spread": float   # projected absolute spread (always positive)
        }

    Returns
    -------
    dict with:
        avg_vol          — average volatility used in scoring
        avg_mae          — average MAE used in scoring
        avg_bias_abs     — absolute average bias used in scoring
        vol_score        — points from volatility  (0-20)
        mae_score        — points from MAE          (0-20)
        bias_score       — points from bias         (0-20)
        spread_score     — points from spread       (0-15)
        raw_score        — total raw points          (0-75)
        confidence_score — normalized 0-100
        band             — confidence band label + description
    """
    avg_vol      = (game["vol_a"]  + game["vol_b"])  / 2
    avg_mae      = (game["mae_a"]  + game["mae_b"])  / 2
    avg_bias_abs = abs((game["bias_a"] + game["bias_b"]) / 2)
    spread       = abs(game.get("spread", 0))

    vol_score    = score_volatility(avg_vol)
    mae_score    = score_mae(avg_mae)
    bias_score   = score_bias(avg_bias_abs)
    spread_score = score_spread(spread)

    raw_score         = vol_score + mae_score + bias_score + spread_score  # 0–75
    confidence_score  = round((raw_score / 75) * 100, 1)

    return {
        # Diagnostics
        "avg_vol":          round(avg_vol, 2),
        "avg_mae":          round(avg_mae, 2),
        "avg_bias_abs":     round(avg_bias_abs, 2),
        # Component scores
        "vol_score":        vol_score,
        "mae_score":        mae_score,
        "bias_score":       bias_score,
        "spread_score":     spread_score,
        # Overall
        "raw_score":        raw_score,
        "confidence_score": confidence_score,
        "band":             get_confidence_band(confidence_score),
    }


# ---------------------------------------------------------------------------
# Convenience: score a batch of games
# ---------------------------------------------------------------------------

def score_games(games: list[dict]) -> list[dict]:
    """
    Score a list of game dicts. Each game should include all 7 required keys
    plus optional metadata keys (home_team, away_team, league, etc.) which
    are passed through unchanged.

    Returns the same list with confidence results merged in.
    """
    results = []
    for g in games:
        conf = compute_confidence(g)
        results.append({**g, **conf})
    return results


# ---------------------------------------------------------------------------
# CLI demo / smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        {
            "label": "Elite Game (low vol, low MAE, unbiased, close spread)",
            "game": {"vol_a": 12.1, "vol_b": 13.8, "mae_a": 6.2, "mae_b": 7.1,
                     "bias_a": 0.5, "bias_b": -1.2, "spread": 4.0},
        },
        {
            "label": "Solid Game",
            "game": {"vol_a": 15.0, "vol_b": 15.5, "mae_a": 8.5, "mae_b": 9.0,
                     "bias_a": 2.5, "bias_b": 3.0, "spread": 7.0},
        },
        {
            "label": "Moderate Confidence",
            "game": {"vol_a": 17.5, "vol_b": 18.0, "mae_a": 10.5, "mae_b": 11.0,
                     "bias_a": 4.5, "bias_b": 5.5, "spread": 11.0},
        },
        {
            "label": "Low Confidence (high vol, high MAE, biased, blowout spread)",
            "game": {"vol_a": 22.0, "vol_b": 23.5, "mae_a": 14.0, "mae_b": 15.0,
                     "bias_a": 8.0, "bias_b": 9.5, "spread": 18.0},
        },
    ]

    header = f"{'Label':<50} {'Vol':>5} {'MAE':>5} {'Bias':>5} {'Sprd':>5} {'Raw':>4} {'Score':>6} Band"
    print("\n" + "=" * 110)
    print("  MODEL CONFIDENCE SCORE — SMOKE TEST")
    print("=" * 110)
    print(header)
    print("-" * 110)

    for tc in test_cases:
        r = compute_confidence(tc["game"])
        print(
            f"{tc['label']:<50} "
            f"{r['avg_vol']:>5.1f} "
            f"{r['avg_mae']:>5.1f} "
            f"{r['avg_bias_abs']:>5.1f} "
            f"{tc['game']['spread']:>5.1f} "
            f"{r['raw_score']:>4} "
            f"{r['confidence_score']:>6.1f} "
            f"{r['band']['label']}"
        )
    print("=" * 110)
