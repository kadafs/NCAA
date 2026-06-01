"""
epoch_config.py
===============
Centralised helper for tracking epoch configuration.

Usage:
    from utils.epoch_config import get_global_epoch, get_earliest_epoch, is_game_valid

Config file: configs/tracking_epochs.json
    {
      "GLOBAL_EPOCH": "2026-03-25",
      "LEAGUE_EPOCHS": {
        "224": "2026-05-01"   // league_id as string key -> ISO date string
      }
    }

Two-level filtering pattern:
  1. File-level  : use get_earliest_epoch() so files needed by leagues with
                   earlier-than-global epochs are not skipped.
  2. Game-level  : use is_game_valid(league_id, file_date_str) inside the
                   prediction loop to apply the per-league epoch.
"""
import json
import os

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "configs", "tracking_epochs.json"
)


def _load() -> dict:
    """Load and return the raw epoch config dict."""
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_global_epoch() -> str:
    """Return the global tracking epoch as an ISO date string (YYYY-MM-DD)."""
    return _load()["GLOBAL_EPOCH"]


def get_league_epochs() -> dict:
    """Return league-specific epoch overrides as {league_id (int): date_str}."""
    return {int(k): v for k, v in _load().get("LEAGUE_EPOCHS", {}).items()}


def get_earliest_epoch() -> str:
    """
    Return the earliest date across the global epoch and all league-specific
    overrides. Use this for file-level filtering so no prediction file is
    skipped prematurely when a league has an earlier epoch than the global one.
    """
    cfg = _load()
    dates = [cfg["GLOBAL_EPOCH"]] + list(cfg.get("LEAGUE_EPOCHS", {}).values())
    return min(dates)


def is_game_valid(league_id, file_date_str: str) -> bool:
    """
    Return True if a prediction from *league_id* on *file_date_str* falls on
    or after the effective epoch for that league.

    Effective epoch = league-specific override (if defined) else global epoch.

    Args:
        league_id   : The league_id value from the prediction dict (int or str).
        file_date_str: Date string in YYYY-MM-DD format derived from the filename.
    """
    cfg = _load()
    league_epoch = cfg.get("LEAGUE_EPOCHS", {}).get(str(league_id))
    global_epoch = cfg["GLOBAL_EPOCH"]
    effective_epoch = league_epoch if league_epoch else global_epoch
    return file_date_str >= effective_epoch
