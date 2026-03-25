"""
migrate_legacy_configs.py
=========================
One-shot migration: converts legacy auto-calibrated configs
(pace_pivot = raw total, eff_pivot = decimal fraction)
to the correct dimensional units expected by the engine
(pace_pivot = possessions/game ~70-100, eff_pivot = pts/100poss ~95-120).

Also populates missing 'name' fields and ensures all configs have
the required tier-template structure.

Usage:
    python migrate_legacy_configs.py                # migrate all
    python migrate_legacy_configs.py --dry_run      # preview without writing
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

CONFIGS_DIR = "configs/leagues"
BACKUP_DIR  = "configs/leagues/_backup"

# Tier templates — sensible defaults when we can't derive from data
TIER_DEFAULTS = {
    "elite_pro":      {"pace": 98.0,  "eff": 113.0, "reg": 0.96, "hca": 2.5,  "pdw": 0.0, "std": 11.0},
    "top_domestic":   {"pace": 78.0,  "eff": 108.0, "reg": 0.92, "hca": 3.5,  "pdw": 0.0, "std": 12.0},
    "second_division":{"pace": 74.0,  "eff": 105.0, "reg": 0.88, "hca": 4.5,  "pdw": 0.0, "std": 13.0},
    "lower":          {"pace": 70.0,  "eff": 103.0, "reg": 0.82, "hca": 5.5,  "pdw": 0.0, "std": 14.0},
}

# Slug-to-name lookup for common leagues
SLUG_NAME_MAP = {
    "australia_nbl": "NBL",
    "germany_bbl": "BBL",
    "turkey_tbl": "TBL",
    "france_pro_b": "Pro B",
    "switzerland_sb_league": "SB League",
    "spain_liga_acb": "Liga ACB",
    "italy_serie_a": "Serie A",
    "greece_basket_league": "Basket League",
}


def is_legacy(cfg):
    """Detect legacy format: eff_pivot < 10 (decimal) or pace_pivot > 110 (raw total)."""
    eff = cfg.get("eff_pivot", 108)
    pace = cfg.get("pace_pivot", 78)
    return eff < 10 or pace > 110


def derive_correct_units(cfg):
    """
    Convert legacy units to correct dimensional values.
    
    Legacy system stored:
      pace_pivot = avg_game_total (e.g. 168.8)
      eff_pivot  = scoring_efficiency_fraction (e.g. 0.844)
    
    Strategy: Use the tier template's pace as the baseline, then
    back-derive efficiency so that the engine's base formula
    reproduces the correct avg_total:
      avg_total = ((eff * pace) / 100) * 2
      → eff = (avg_total * 100) / (2 * pace)
    """
    raw_pace = cfg.get("pace_pivot", 150)  # This is actually avg_total
    avg_total = raw_pace
    
    # Use tier-appropriate pace
    tier = infer_tier(cfg)
    tier_pace = TIER_DEFAULTS[tier]["pace"]
    
    # Back-derive efficiency from: avg_total = ((eff * pace) / 100) * 2
    # → eff = (avg_total * 100) / (2 * pace)
    est_eff = (avg_total * 100) / (2 * tier_pace)
    est_eff = max(90.0, min(140.0, round(est_eff, 1)))
    
    return tier_pace, est_eff, round(avg_total, 1)


def infer_tier(cfg):
    """Guess tier from existing data or default to top_domestic."""
    tier = cfg.get("_tier")
    if tier and tier in TIER_DEFAULTS:
        return tier
    
    # Infer from avg_total (legacy pace_pivot)
    avg_total = cfg.get("pace_pivot", 150)  # legacy = avg total
    if avg_total > 200:
        return "elite_pro"
    elif avg_total > 155:
        return "top_domestic"
    elif avg_total > 135:
        return "second_division"
    else:
        return "lower"


def infer_name(cfg, filename):
    """Get a league name from config or derive from slug/filename."""
    name = cfg.get("name")
    if name and name != f"League-{cfg.get('_league_id', '?')}":
        return name
    
    slug = cfg.get("flashscore_slug", "")
    if slug in SLUG_NAME_MAP:
        return SLUG_NAME_MAP[slug]
    
    # Try to make something readable from the slug
    if slug:
        parts = slug.split("_")
        if len(parts) >= 2:
            return " ".join(p.capitalize() for p in parts[1:])
    
    # Use the league ID
    lid = filename.replace(".json", "")
    return f"League-{lid}"


def migrate_config(filepath, dry_run=False):
    """Migrate a single config file. Returns (status, details)."""
    filename = os.path.basename(filepath)
    lid = filename.replace(".json", "")
    
    with open(filepath, encoding="utf-8") as f:
        cfg = json.load(f)
    
    if not is_legacy(cfg):
        # Still check if name is missing
        if not cfg.get("name"):
            cfg["name"] = infer_name(cfg, filename)
            if not dry_run:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            return "name_only", f"Added name: {cfg['name']}"
        return "skip", "Already in correct format"
    
    # Derive correct units
    new_pace, new_eff, avg_total = derive_correct_units(cfg)
    tier = infer_tier(cfg)
    tier_defaults = TIER_DEFAULTS[tier]
    name = infer_name(cfg, filename)
    
    old_pace = cfg.get("pace_pivot")
    old_eff = cfg.get("eff_pivot")
    old_hca = cfg.get("hca_value", cfg.get("hca_total_bump", tier_defaults["hca"]))
    
    # Build migrated config
    migrated = {
        "name": name,
        "_league_id": int(lid) if lid.isdigit() else lid,
        "_calibrated_at": datetime.now().strftime("%Y-%m-%d"),
        "_tier": tier,
        "_source": "migrated-from-legacy",
        "_avg_total": avg_total,
        "_pre_migration": {
            "pace_pivot": old_pace,
            "eff_pivot": old_eff,
        },
        "game_duration_mins": cfg.get("game_duration_mins", 40),
        "pace_pivot": new_pace,
        "eff_pivot": new_eff,
        "regression_factor": cfg.get("regression_factor", tier_defaults["reg"]),
        "hca_total_bump": round(max(0.5, min(8.0, old_hca)), 1),
        "pace_delta_weight": 0.0,  # Fix 5: disabled (was causing double-counting)
        "eff_delta_weight": cfg.get("eff_delta_weight", 0.7),
        "win_prob_std_dev": tier_defaults["std"],  # Fix 8: configurable std_dev
        "situational": cfg.get("situational", {
            "b2b_penalty_single": -1.5,
            "b2b_penalty_double": -3.0,
            "fatigue_impact_cap": -4.0,
        }),
        "thresholds": cfg.get("thresholds", {
            "mode_a": tier_defaults.get("mode_a", 7.0) if isinstance(tier_defaults, dict) else 7.0,
            "mode_b": tier_defaults.get("mode_b", 4.0) if isinstance(tier_defaults, dict) else 4.0,
            "min_edge": 0.0,
        }),
    }
    
    # Fix thresholds if not present
    if "thresholds" not in migrated or not migrated["thresholds"]:
        migrated["thresholds"] = {"mode_a": 7.0, "mode_b": 4.0, "min_edge": 0.0}
    
    if not dry_run:
        # Backup original
        os.makedirs(BACKUP_DIR, exist_ok=True)
        shutil.copy2(filepath, os.path.join(BACKUP_DIR, filename))
        
        # Write migrated
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(migrated, f, indent=2)
    
    return "migrated", f"pace: {old_pace} -> {new_pace}, eff: {old_eff} -> {new_eff}, name: {name}"


def main():
    parser = argparse.ArgumentParser(description="Migrate legacy basketball configs")
    parser.add_argument("--dry_run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    
    print("\n" + "=" * 65)
    print("  LEGACY CONFIG MIGRATION")
    print("=" * 65)
    
    files = sorted([f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")])
    print(f"  Scanning {len(files)} config files...\n")
    
    counts = {"migrated": 0, "name_only": 0, "skip": 0, "error": 0}
    
    for filename in files:
        filepath = os.path.join(CONFIGS_DIR, filename)
        try:
            status, detail = migrate_config(filepath, dry_run=args.dry_run)
            counts[status] += 1
            if status != "skip":
                prefix = "[DRY] " if args.dry_run else ""
                print(f"  {prefix}[{status.upper():>10}] {filename}: {detail}")
        except Exception as e:
            counts["error"] += 1
            print(f"  [     ERROR] {filename}: {e}")
    
    print(f"\n{'=' * 65}")
    print(f"  RESULTS: {counts['migrated']} migrated | {counts['name_only']} name-only | "
          f"{counts['skip']} skipped | {counts['error']} errors")
    if not args.dry_run and counts['migrated'] > 0:
        print(f"  Backups saved to: {BACKUP_DIR}/")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
