#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D2 Conference-Only Prediction Model - NOT READY FOR TESTING

WARNING: IMPORTANT LIMITATION
This script currently uses FULL-SEASON D2 stats, NOT true conference-only stats.

Why? D2 data comes from NCAA.com API which provides cumulative season stats (PPG, FGA, etc.)
without conference filtering. To get TRUE conference-only stats, we would need to:
1. Fetch game-by-game schedules for each D2 team
2. Identify which games were against conference opponents  
3. Manually recalculate all stats from ONLY conference games

Until this is implemented, this model will produce IDENTICAL results to the full-season D2 model.

DO NOT USE THIS FOR TESTING until true conference filtering is implemented.
"""

import json
import os
import sys

print("\n" + "="*80)
print("WARNING: D2 CONFERENCE-ONLY MODEL - NOT READY FOR TESTING")
print("="*80)
print("\nThis model currently uses full-season D2 stats, not true conference-only stats.")
print("\nReason: D2 data from NCAA.com API doesn't support conference filtering.")
print("        Game-by-game schedule parsing is required for true conference stats.")
print("\nRecommendation: Focus testing on D1 conference-only model instead.")
print("\nTo implement true D2 conference filtering:")
print("  1. Fetch game-by-game schedules from NCAA API")
print("  2. Identify conference vs non-conference games")
print("  3. Recalculate PPG, OPP PPG, FGA, etc. from conference games only")
print("\n" + "="*80 + "\n")

sys.exit(1)

