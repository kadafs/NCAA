"""
env_confidence.py
=================
Layer 2 of the Pure Core + Directional Filter model redesign.

Role: After the MC and Top-Down models produce a talent-only (park/weather/umpire-neutral)
run projection, this module evaluates the environmental context and returns a structured
confidence assessment — NOT a numeric multiplier.

The assessment captures:
  - Whether the park CONFIRMS or CONTRADICTS the model's betting lean
  - Whether weather conditions are notable and directionally consistent
  - Whether the plate umpire's tendencies align with the model's prediction

Usage in consensus_f5_v4.py:
    env = compute_env_confidence(pf, weather, umpire_profile, pure_f5, posted_line, sport_id)
    # env['combined_signal'] is used by the Gatekeeper
    # env['confidence_delta'] adjusts the edge threshold

Design notes:
  - All thresholds are conservative starting points, calibrate via backtest
  - Positive confidence_delta = environment confirms the model lean (raise conviction)
  - Negative confidence_delta = environment contradicts the model lean (reduce conviction)
  - STRONG_CONTRADICT forces a skip regardless of model edge
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Park Factor thresholds
# ---------------------------------------------------------------------------
_PF_EXTREME  = 0.15   # |PF - 1.0| > this → extreme park, large confidence shift
_PF_NOTABLE  = 0.10   # |PF - 1.0| > this → notable park, smaller confidence shift

_DELTA_PF_EXTREME = 15
_DELTA_PF_NOTABLE = 8

# ---------------------------------------------------------------------------
# Weather thresholds
# ---------------------------------------------------------------------------
_TEMP_HOT  = 85.0   # °F — ball carries further
_TEMP_COLD = 55.0   # °F — ball drops faster
_WIND_SIGNIFICANT = 12.0  # mph — meaningful impact on HR

_DELTA_WEATHER = 5

# ---------------------------------------------------------------------------
# Umpire thresholds
# ---------------------------------------------------------------------------
_UMP_K_DEV_THRESHOLD = 0.08   # |raw_k_mod - 1.0| > this → meaningful umpire bias
_MIN_UMP_GAMES = 15           # below this, treat umpire as neutral

_DELTA_UMPIRE = 6

# ---------------------------------------------------------------------------
# Combined signal boundaries
# ---------------------------------------------------------------------------
_STRONG_CONFIRM_THRESHOLD    =  20
_CONFIRM_THRESHOLD           =   8
_CONTRADICT_THRESHOLD        =  -8
_STRONG_CONTRADICT_THRESHOLD = -20


def _classify_signal(delta: float) -> str:
    if delta >= _STRONG_CONFIRM_THRESHOLD:
        return "STRONG_CONFIRM"
    if delta >= _CONFIRM_THRESHOLD:
        return "CONFIRM"
    if delta <= _STRONG_CONTRADICT_THRESHOLD:
        return "STRONG_CONTRADICT"
    if delta <= _CONTRADICT_THRESHOLD:
        return "CONTRADICT"
    return "NEUTRAL"


def _park_assessment(park_factor: float, lean: str) -> tuple[str, str, float, str]:
    """
    Returns (park_flag, park_signal, delta, note).
    lean: 'OVER' or 'UNDER'
    """
    deviation = park_factor - 1.0

    if abs(deviation) > _PF_EXTREME:
        park_flag = "HITTERS_PARK" if deviation > 0 else "PITCHERS_PARK"
        park_note = f"PF={park_factor:.3f} (extreme)"
        delta_mag  = _DELTA_PF_EXTREME
    elif abs(deviation) > _PF_NOTABLE:
        park_flag = "HITTERS_PARK" if deviation > 0 else "PITCHERS_PARK"
        park_note = f"PF={park_factor:.3f} (notable)"
        delta_mag  = _DELTA_PF_NOTABLE
    else:
        return "NEUTRAL", "NEUTRAL", 0.0, f"PF={park_factor:.3f} (neutral)"

    # Confirm when park direction matches bet direction
    confirms = (
        (park_flag == "HITTERS_PARK" and lean == "OVER") or
        (park_flag == "PITCHERS_PARK" and lean == "UNDER")
    )
    park_signal = "CONFIRMS" if confirms else "CONTRADICTS"
    delta       = delta_mag if confirms else -delta_mag

    return park_flag, park_signal, delta, park_note


def _weather_assessment(weather_ctx: dict | None, lean: str) -> tuple[str, str, float, str]:
    """
    Returns (weather_flag, weather_signal, delta, note).
    Directional: hot/wind-out boosts OVER lean, cold/wind-in boosts UNDER lean.
    """
    if not weather_ctx or weather_ctx.get("is_indoor"):
        return "NEUTRAL", "NEUTRAL", 0.0, "Indoor/no weather"

    temp     = weather_ctx.get("temp", 72)
    wind_mph = float(weather_ctx.get("wind_mph", 0))
    wind_dir = weather_ctx.get("wind_dir", "Calm")

    delta = 0.0
    flags = []
    notes = []

    # --- Temperature signal ---
    if temp >= _TEMP_HOT:
        flags.append("HOT")
        notes.append(f"{temp}F")
        if lean == "OVER":
            delta += _DELTA_WEATHER
        else:
            delta -= _DELTA_WEATHER
    elif temp <= _TEMP_COLD:
        flags.append("COLD")
        notes.append(f"{temp}F")
        if lean == "UNDER":
            delta += _DELTA_WEATHER
        else:
            delta -= _DELTA_WEATHER

    # --- Wind signal ---
    if wind_mph >= _WIND_SIGNIFICANT:
        if wind_dir == "Out":
            flags.append("WIND_OUT")
            notes.append(f"{wind_mph:.0f}mph out")
            if lean == "OVER":
                delta += _DELTA_WEATHER
            else:
                delta -= _DELTA_WEATHER
        elif wind_dir == "In":
            flags.append("WIND_IN")
            notes.append(f"{wind_mph:.0f}mph in")
            if lean == "UNDER":
                delta += _DELTA_WEATHER
            else:
                delta -= _DELTA_WEATHER

    if not flags:
        return "NEUTRAL", "NEUTRAL", 0.0, f"{temp}F | {wind_dir}"

    weather_flag   = "+".join(flags)
    weather_signal = "CONFIRMS" if delta > 0 else "CONTRADICTS"
    note           = " | ".join(notes)
    return weather_flag, weather_signal, delta, note


def _umpire_assessment(umpire_profile: dict | None, lean: str) -> tuple[str, str, float, str]:
    """
    Returns (umpire_flag, umpire_signal, delta, note).
    Tight zone (more K's) → lean UNDER. Loose zone (fewer K's) → lean OVER.
    """
    if not umpire_profile:
        return "NEUTRAL", "NEUTRAL", 0.0, "No umpire data"

    games_called = umpire_profile.get("games_called", 0)
    if games_called < _MIN_UMP_GAMES:
        return "NEUTRAL", "NEUTRAL", 0.0, f"Insufficient sample ({games_called} G)"

    raw_k_mod = umpire_profile.get("raw_k_mod", 1.0)
    k_deviation = raw_k_mod - 1.0   # positive = more K's than avg (tight zone)

    if abs(k_deviation) < _UMP_K_DEV_THRESHOLD:
        return "NEUTRAL", "NEUTRAL", 0.0, f"K-dev={k_deviation:+.3f} (within threshold)"

    umpire_flag = "TIGHT_ZONE" if k_deviation > 0 else "LOOSE_ZONE"
    note        = f"K-dev={k_deviation:+.3f} ({games_called}G)"

    # Tight zone (more K's) depresses scoring → confirms UNDER, contradicts OVER
    confirms = (
        (umpire_flag == "TIGHT_ZONE"  and lean == "UNDER") or
        (umpire_flag == "LOOSE_ZONE"  and lean == "OVER")
    )
    umpire_signal = "CONFIRMS" if confirms else "CONTRADICTS"
    delta         = _DELTA_UMPIRE if confirms else -_DELTA_UMPIRE

    return umpire_flag, umpire_signal, delta, note


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_env_confidence(
    park_factor:     float,
    weather_context: dict | None,
    umpire_profile:  dict | None,
    pure_f5:         float,
    posted_line:     float,
    sport_id:        int = 1,
) -> dict:
    """
    Evaluate PF / weather / umpire as directional confidence weights.

    Parameters
    ----------
    park_factor     : Blended park factor from get_park_factor()
    weather_context : Output of weather_f5.get_weather_context() or None
    umpire_profile  : Output of umpire_engine.load_umpire_profile() or None
    pure_f5         : Talent-only F5 run total from pure MC model
    posted_line     : The book's posted F5 total
    sport_id        : 1=MLB, 11=AAA, 12=AA

    Returns
    -------
    dict with:
      park_flag, park_signal, park_delta
      weather_flag, weather_signal, weather_delta
      umpire_flag, umpire_signal, umpire_delta
      combined_signal  : str  (STRONG_CONFIRM / CONFIRM / NEUTRAL / CONTRADICT / STRONG_CONTRADICT)
      confidence_delta : float (net delta, +ve = more confidence in the bet)
      lean             : str  ('OVER' / 'UNDER' / 'PUSH')
      env_note         : str  (human-readable summary for dashboard)
    """
    # Determine model lean from pure talent projection vs posted line
    if posted_line <= 0 or pure_f5 <= 0:
        lean = "PUSH"
    elif pure_f5 > posted_line + 0.05:
        lean = "OVER"
    elif pure_f5 < posted_line - 0.05:
        lean = "UNDER"
    else:
        lean = "PUSH"

    # --- Assess each factor ---
    park_flag,    park_signal,    park_delta,    park_note    = _park_assessment(park_factor, lean)
    weather_flag, weather_signal, weather_delta, weather_note = _weather_assessment(weather_context, lean)
    umpire_flag,  umpire_signal,  umpire_delta,  umpire_note  = _umpire_assessment(umpire_profile, lean)

    # --- Combine ---
    total_delta    = park_delta + weather_delta + umpire_delta
    combined_signal = _classify_signal(total_delta)

    # --- Build human-readable note ---
    parts = [f"Park: {park_flag} {park_signal}"]
    if weather_flag != "NEUTRAL":
        parts.append(f"Weather: {weather_flag} {weather_signal} ({weather_note})")
    if umpire_flag != "NEUTRAL":
        parts.append(f"Ump: {umpire_flag} {umpire_signal} ({umpire_note})")
    env_note = " | ".join(parts) + f" -> {combined_signal} ({total_delta:+.0f})"

    return {
        # Park
        "park_flag":        park_flag,
        "park_signal":      park_signal,
        "park_delta":       park_delta,
        "park_note":        park_note,
        # Weather
        "weather_flag":     weather_flag,
        "weather_signal":   weather_signal,
        "weather_delta":    weather_delta,
        "weather_note":     weather_note,
        # Umpire
        "umpire_flag":      umpire_flag,
        "umpire_signal":    umpire_signal,
        "umpire_delta":     umpire_delta,
        "umpire_note":      umpire_note,
        # Summary
        "lean":             lean,
        "combined_signal":  combined_signal,
        "confidence_delta": total_delta,
        "env_note":         env_note,
    }


if __name__ == "__main__":
    # Quick self-test
    test_cases = [
        # Las Vegas: extreme hitter park + hot day + neutral ump, model says OVER
        {
            "label": "Las Vegas OVER (should STRONG_CONFIRM)",
            "pf": 1.375, "pure_f5": 5.2, "line": 4.5,
            "weather": {"temp": 104, "wind_mph": 5, "wind_dir": "Calm", "is_indoor": False},
            "ump": {"raw_k_mod": 1.02, "games_called": 80},
        },
        # Las Vegas: extreme hitter park, model says UNDER — park contradicts
        {
            "label": "Las Vegas UNDER (park CONTRADICTS)",
            "pf": 1.375, "pure_f5": 3.8, "line": 4.5,
            "weather": {"temp": 104, "wind_mph": 5, "wind_dir": "Calm", "is_indoor": False},
            "ump": {"raw_k_mod": 1.15, "games_called": 80},  # tight zone confirms UNDER
        },
        # Gwinnett: pitcher park, model says UNDER, cold day + wind in
        {
            "label": "Gwinnett UNDER (should STRONG_CONFIRM)",
            "pf": 0.768, "pure_f5": 3.5, "line": 4.5,
            "weather": {"temp": 52, "wind_mph": 15, "wind_dir": "In", "is_indoor": False},
            "ump": {"raw_k_mod": 1.12, "games_called": 50},
        },
        # Neutral park, no weather, neutral ump
        {
            "label": "Neutral everything",
            "pf": 1.002, "pure_f5": 4.6, "line": 4.5,
            "weather": {"temp": 72, "wind_mph": 3, "wind_dir": "Calm", "is_indoor": False},
            "ump": None,
        },
    ]

    for tc in test_cases:
        result = compute_env_confidence(
            park_factor=tc["pf"],
            weather_context=tc["weather"],
            umpire_profile=tc.get("ump"),
            pure_f5=tc["pure_f5"],
            posted_line=tc["line"],
        )
        print(f"\n{tc['label']}")
        print(f"  pure_f5={tc['pure_f5']} vs line={tc['line']} -> lean={result['lean']}")
        print(f"  {result['env_note']}")
        print(f"  combined_signal={result['combined_signal']}  confidence_delta={result['confidence_delta']:+.0f}")
