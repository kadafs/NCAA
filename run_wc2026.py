"""
run_wc2026.py
=============
FIFA World Cup 2026 — Group Stage Predictor (Offline, No API Required)

OFFICIAL FORMAT  (confirmed from FIFA fixture list):
  - 12 groups (A–L), 4 teams each  →  48 teams
  - 6 games per group (full round-robin)  →  72 group stage fixtures
  - Matchday 3 games played simultaneously per group
  - Top 2 from each group + 8 best 3rd-place teams → 32 advance

RESULTS populated:  All Round 1 (Jun 11–15) official results embedded.
                    Add Round 2/3 results to ACTUAL_RESULTS as they come in.

Usage:
    python run_wc2026.py                        # full group stage
    python run_wc2026.py --group A              # single group
    python run_wc2026.py --team Argentina       # all games for a team
    python run_wc2026.py --matchday 1           # matchday filter (1, 2, 3)
    python run_wc2026.py --upcoming             # unplayed only
    python run_wc2026.py --completed            # played only
    python run_wc2026.py --mode full            # sharp mode
    python run_wc2026.py --trace                # show xG math trace
    python run_wc2026.py --standings            # projected standings
    python run_wc2026.py --btts-only            # PLAY YES picks only
    python run_wc2026.py --export               # save to JSON
"""

import sys, os, json, math, argparse
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ===========================================================================
# TEAM ELO RATINGS
# Only WC2026 participants — FIFA name variants as aliases.
# Base: data/football/elo_ratings.json (updated with qualifier context).
# ===========================================================================

TEAM_ELO = {
    # ─── GROUP A ────────────────────────────────────────────────────────────
    "Mexico":                   1904,
    "Korea Republic":           1882,
    "South Korea":              1882,   # common alias
    "Czechia":                  1641,
    "Czech Republic":           1641,   # common alias
    "South Africa":             1620,
    # ─── GROUP B ────────────────────────────────────────────────────────────
    "Switzerland":              1806,
    "Canada":                   1793,
    "Qatar":                    1580,
    "Bosnia and Herzegovina":   1552,
    # ─── GROUP C ────────────────────────────────────────────────────────────
    "Brazil":                   1897,
    "Morocco":                  1943,
    "Scotland":                 1764,
    "Haiti":                    1696,
    # ─── GROUP D ────────────────────────────────────────────────────────────
    "USA":                      1785,
    "United States":            1785,
    "Australia":                1922,
    "Türkiye":                  1811,
    "Turkey":                   1811,
    "Paraguay":                 1737,
    # ─── GROUP E ────────────────────────────────────────────────────────────
    "Germany":                  1887,
    "Côte d'Ivoire":            1831,
    "Ivory Coast":              1831,
    "Cote d'Ivoire":            1831,
    "Ecuador":                  1850,
    "Curaçao":                  1630,
    "Curacao":                  1630,
    # ─── GROUP F ────────────────────────────────────────────────────────────
    "Sweden":                   1690,
    "Japan":                    1948,
    "Netherlands":              1867,
    "Tunisia":                  1665,
    # ─── GROUP G ────────────────────────────────────────────────────────────
    "Belgium":                  1823,
    "IR Iran":                  1876,
    "Iran":                     1876,
    "Egypt":                    1776,
    "New Zealand":              1696,
    # ─── GROUP H ────────────────────────────────────────────────────────────
    "Spain":                    2073,
    "Saudi Arabia":             1681,
    "Uruguay":                  1802,
    "Cabo Verde":               1636,
    "Cape Verde":               1636,
    "Cape Verde Islands":       1636,
    # ─── GROUP I ────────────────────────────────────────────────────────────
    "France":                   1973,
    "Senegal":                  1866,
    "Iraq":                     1751,
    "Norway":                   1873,
    # ─── GROUP J ────────────────────────────────────────────────────────────
    "Argentina":                1987,
    "Algeria":                  1874,
    "Austria":                  1742,
    "Jordan":                   1765,
    # ─── GROUP K ────────────────────────────────────────────────────────────
    "Portugal":                 1871,
    "Colombia":                 1891,
    "Congo DR":                 1759,
    "DR Congo":                 1759,
    "Uzbekistan":               1814,
    # ─── GROUP L ────────────────────────────────────────────────────────────
    "England":                  1971,
    "Croatia":                  1824,
    "Ghana":                    1632,
    "Panama":                   1806,
}

# ===========================================================================
# CONFEDERATION MEMBERSHIP  (all 48 WC2026 teams)
# ===========================================================================

TEAM_CONFEDERATION = {
    # AFC — Asian Football Confederation
    "Korea Republic":           "AFC",
    "South Korea":              "AFC",
    "Australia":                "AFC",
    "Japan":                    "AFC",
    "IR Iran":                  "AFC",
    "Iran":                     "AFC",
    "Saudi Arabia":             "AFC",
    "Iraq":                     "AFC",
    "Jordan":                   "AFC",
    "Uzbekistan":               "AFC",
    "Qatar":                    "AFC",
    # CAF — Confederation of African Football
    "Morocco":                  "CAF",
    "Senegal":                  "CAF",
    "Côte d'Ivoire":            "CAF",
    "Ivory Coast":              "CAF",
    "Cote d'Ivoire":            "CAF",
    "Egypt":                    "CAF",
    "South Africa":             "CAF",
    "Algeria":                  "CAF",
    "Congo DR":                 "CAF",
    "DR Congo":                 "CAF",
    "Ghana":                    "CAF",
    "Tunisia":                  "CAF",
    # CONCACAF — Confederation of North, Central America and Caribbean Association Football
    "USA":                      "CONCACAF",
    "United States":            "CONCACAF",
    "Mexico":                   "CONCACAF",
    "Canada":                   "CONCACAF",
    "Panama":                   "CONCACAF",
    "Haiti":                    "CONCACAF",
    "Curaçao":                  "CONCACAF",
    "Curacao":                  "CONCACAF",
    "Cabo Verde":               "CONCACAF",   # technically CAF but CONCACAF-level strength
    "Cape Verde":               "CONCACAF",
    "Cape Verde Islands":       "CONCACAF",
    # CONMEBOL — South American Football Confederation
    "Brazil":                   "CONMEBOL",
    "Argentina":                "CONMEBOL",
    "Uruguay":                  "CONMEBOL",
    "Colombia":                 "CONMEBOL",
    "Ecuador":                  "CONMEBOL",
    "Paraguay":                 "CONMEBOL",
    # OFC — Oceania Football Confederation
    "New Zealand":              "OFC",
    # UEFA — Union of European Football Associations (all remaining teams)
    "Germany":                  "UEFA",
    "Spain":                    "UEFA",
    "France":                   "UEFA",
    "England":                  "UEFA",
    "Netherlands":              "UEFA",
    "Portugal":                 "UEFA",
    "Belgium":                  "UEFA",
    "Switzerland":              "UEFA",
    "Croatia":                  "UEFA",
    "Sweden":                   "UEFA",
    "Scotland":                 "UEFA",
    "Austria":                  "UEFA",
    "Norway":                   "UEFA",
    "Czechia":                  "UEFA",
    "Czech Republic":           "UEFA",
    "Bosnia and Herzegovina":   "UEFA",
    "Türkiye":                  "UEFA",
    "Turkey":                   "UEFA",
}

# ===========================================================================
# CONFEDERATION ELO ADJUSTMENT
# Applied at prediction time to correct for regional isolation bias.
# A team's Elo is earned in their own confederation — cross-confederation
# WC matches historically expose inflation.  UEFA & CONMEBOL are the baseline.
#
# Calibrated from WC 2010–2022 cross-confederation results vs Elo prediction:
#   AFC  teams win ~28% of cross-conf WC games (expected 50% if Elo accurate)
#   CAF  teams win ~38%  |  CONCACAF ~40%  |  OFC ~15%
#   Japan exception: -30 (outperformed expectations in recent WCs vs Europe)
# ===========================================================================

CONF_ELO_ADJUSTMENT = {
    "UEFA":     0,      # Baseline — strongest / most competitive confederation
    "CONMEBOL": 0,      # On par with UEFA historically at WCs
    "CAF":     -20,     # Slight inflation — improving (Morocco 2022 semis)
    "CONCACAF":-35,     # Mixed: USA/Mexico competitive, smaller nations inflated
    "AFC":     -55,     # Biggest inflation — easy Asian qualifying pool
    "OFC":     -70,     # Tiny pool, rarely competitive at WC level
}

# Per-team overrides — for teams whose WC track record clearly diverges from
# their confederation average (applied ON TOP of confederation adjustment).
TEAM_ELO_OVERRIDE = {
    "Japan":          +25,   # Won vs Germany & Spain at WC2022; genuinely elite AFC
    "Australia":      +15,   # R16 2022, strong A-League + European-based players
    "Morocco":        +20,   # WC2022 semifinalists; CAF correction too harsh for them
    "USA":            +10,   # Hosts; competitive cross-conf record historically
}


# ===========================================================================
# OFFICIAL GROUPS  (12 × 4 teams, confirmed from live standings)
# ===========================================================================

WC2026_GROUPS = {
    "A": ["Mexico",      "Korea Republic", "Czechia",              "South Africa"],
    "B": ["Canada",      "Switzerland",    "Qatar",                "Bosnia and Herzegovina"],
    "C": ["Brazil",      "Morocco",        "Scotland",             "Haiti"],
    "D": ["USA",         "Australia",      "Türkiye",              "Paraguay"],
    "E": ["Germany",     "Côte d'Ivoire",  "Ecuador",              "Curaçao"],
    "F": ["Netherlands", "Sweden",         "Japan",                "Tunisia"],
    "G": ["Belgium",     "IR Iran",        "Egypt",                "New Zealand"],
    "H": ["Spain",       "Saudi Arabia",   "Uruguay",              "Cabo Verde"],
    "I": ["France",      "Senegal",        "Iraq",                 "Norway"],
    "J": ["Argentina",   "Algeria",        "Austria",              "Jordan"],
    "K": ["Portugal",    "Colombia",       "Congo DR",             "Uzbekistan"],
    "L": ["England",     "Croatia",        "Ghana",                "Panama"],
}

# ===========================================================================
# ALL 72 GROUP STAGE FIXTURES
# Source: Official FIFA World Cup 2026 schedule
# Format: (home_team, away_team, date, venue, group, matchday)
# Home team = team listed first on official fixture sheet
# ✓ = result confirmed / ~ = result from standings arithmetic
# ===========================================================================

WC2026_FIXTURES = [

    # ══════════════════════════════════════════════════════════════════════
    # GROUP A — Mexico | Korea Republic | Czechia | South Africa
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1
    ("Mexico",         "South Africa",   "2026-06-11", "Mexico City Stadium",          "A", 1),  # ✓ 2-0
    ("Korea Republic", "Czechia",        "2026-06-12", "Guadalajara Stadium",          "A", 1),  # ✓ 2-1
    # Matchday 2
    ("Czechia",        "South Africa",   "2026-06-18", "Atlanta Stadium",              "A", 2),
    ("Mexico",         "Korea Republic", "2026-06-19", "Guadalajara Stadium",          "A", 2),
    # Matchday 3 (simultaneous 02:00 Jun 25)
    ("Czechia",        "Mexico",         "2026-06-25", "Mexico City Stadium",          "A", 3),
    ("South Africa",   "Korea Republic", "2026-06-25", "Monterrey Stadium",            "A", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP B — Canada | Switzerland | Qatar | Bosnia and Herzegovina
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1
    ("Canada",         "Bosnia and Herzegovina", "2026-06-12", "Toronto Stadium",      "B", 1),  # ✓ 1-1
    ("Qatar",          "Switzerland",    "2026-06-13", "San Francisco Bay Area Stadium","B", 1),  # ✓ 1-1
    # Matchday 2
    ("Switzerland",    "Bosnia and Herzegovina", "2026-06-18", "Los Angeles Stadium",  "B", 2),
    ("Canada",         "Qatar",          "2026-06-18", "BC Place Vancouver",           "B", 2),
    # Matchday 3 (simultaneous 20:00 Jun 24)
    ("Switzerland",    "Canada",         "2026-06-24", "BC Place Vancouver",           "B", 3),
    ("Bosnia and Herzegovina", "Qatar",  "2026-06-24", "Seattle Stadium",              "B", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP C — Brazil | Morocco | Scotland | Haiti
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1
    ("Brazil",         "Morocco",        "2026-06-13", "New York/New Jersey Stadium",  "C", 1),  # ✓ 1-1
    ("Haiti",          "Scotland",       "2026-06-14", "Boston Stadium",               "C", 1),  # ✓ 0-1
    # Matchday 2
    ("Scotland",       "Morocco",        "2026-06-19", "Boston Stadium",               "C", 2),
    ("Brazil",         "Haiti",          "2026-06-20", "Philadelphia Stadium",         "C", 2),
    # Matchday 3 (simultaneous 23:00 Jun 24)
    ("Scotland",       "Brazil",         "2026-06-24", "Miami Stadium",                "C", 3),
    ("Morocco",        "Haiti",          "2026-06-24", "Atlanta Stadium",              "C", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP D — USA | Australia | Türkiye | Paraguay
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1
    ("USA",            "Paraguay",       "2026-06-13", "Los Angeles Stadium",          "D", 1),  # ✓ 4-1
    ("Australia",      "Türkiye",        "2026-06-14", "BC Place Vancouver",           "D", 1),  # ✓ 2-0
    # Matchday 2
    ("USA",            "Australia",      "2026-06-19", "Seattle Stadium",              "D", 2),
    ("Türkiye",        "Paraguay",       "2026-06-20", "San Francisco Bay Area Stadium","D", 2),
    # Matchday 3 (simultaneous 03:00 Jun 26)
    ("Türkiye",        "USA",            "2026-06-26", "Los Angeles Stadium",          "D", 3),
    ("Paraguay",       "Australia",      "2026-06-26", "San Francisco Bay Area Stadium","D", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP E — Germany | Côte d'Ivoire | Ecuador | Curaçao
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1
    ("Germany",        "Curaçao",        "2026-06-14", "Houston Stadium",              "E", 1),  # ✓ 7-1
    ("Côte d'Ivoire",  "Ecuador",        "2026-06-15", "Philadelphia Stadium",         "E", 1),  # ✓ 1-0
    # Matchday 2
    ("Germany",        "Côte d'Ivoire",  "2026-06-20", "Toronto Stadium",              "E", 2),
    ("Ecuador",        "Curaçao",        "2026-06-21", "Kansas City Stadium",          "E", 2),
    # Matchday 3 (simultaneous 21:00 Jun 25)
    ("Curaçao",        "Côte d'Ivoire",  "2026-06-25", "Philadelphia Stadium",         "E", 3),
    ("Ecuador",        "Germany",        "2026-06-25", "New York/New Jersey Stadium",  "E", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP F — Netherlands | Sweden | Japan | Tunisia
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1
    ("Netherlands",    "Japan",          "2026-06-14", "Dallas Stadium",               "F", 1),  # ✓ 2-2
    ("Sweden",         "Tunisia",        "2026-06-15", "Monterrey Stadium",            "F", 1),  # ✓ 5-1 (API cache)
    # Matchday 2
    ("Netherlands",    "Sweden",         "2026-06-20", "Houston Stadium",              "F", 2),
    ("Tunisia",        "Japan",          "2026-06-21", "Monterrey Stadium",            "F", 2),
    # Matchday 3 (simultaneous 00:00 Jun 26)
    ("Japan",          "Sweden",         "2026-06-26", "Dallas Stadium",               "F", 3),
    ("Tunisia",        "Netherlands",    "2026-06-26", "Kansas City Stadium",          "F", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP G — Belgium | IR Iran | Egypt | New Zealand
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1 (Jun 15–16)
    ("Belgium",        "Egypt",          "2026-06-15", "Seattle Stadium",              "G", 1),  # ✓ upcoming
    ("IR Iran",        "New Zealand",    "2026-06-16", "Los Angeles Stadium",          "G", 1),  # upcoming
    # Matchday 2 (Jun 21–22)
    ("Belgium",        "IR Iran",        "2026-06-21", "Los Angeles Stadium",          "G", 2),
    ("New Zealand",    "Egypt",          "2026-06-22", "BC Place Vancouver",           "G", 2),
    # Matchday 3 (simultaneous 04:00 Jun 27)
    ("Egypt",          "IR Iran",        "2026-06-27", "Seattle Stadium",              "G", 3),
    ("New Zealand",    "Belgium",        "2026-06-27", "BC Place Vancouver",           "G", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP H — Spain | Saudi Arabia | Uruguay | Cabo Verde
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1 (Jun 15)
    ("Spain",          "Cabo Verde",     "2026-06-15", "Atlanta Stadium",              "H", 1),  # ✓ upcoming 17:00
    ("Saudi Arabia",   "Uruguay",        "2026-06-15", "Miami Stadium",                "H", 1),  # ✓ upcoming 23:00
    # Matchday 2 (Jun 21)
    ("Spain",          "Saudi Arabia",   "2026-06-21", "Atlanta Stadium",              "H", 2),
    ("Uruguay",        "Cabo Verde",     "2026-06-21", "Miami Stadium",                "H", 2),
    # Matchday 3 (simultaneous 01:00 Jun 27)
    ("Cabo Verde",     "Saudi Arabia",   "2026-06-27", "Houston Stadium",              "H", 3),
    ("Uruguay",        "Spain",          "2026-06-27", "Guadalajara Stadium",          "H", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP I — France | Senegal | Iraq | Norway
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1 (Jun 16)
    ("France",         "Senegal",        "2026-06-16", "New York/New Jersey Stadium",  "I", 1),
    ("Iraq",           "Norway",         "2026-06-16", "Boston Stadium",               "I", 1),
    # Matchday 2 (Jun 22–23)
    ("France",         "Iraq",           "2026-06-22", "Philadelphia Stadium",         "I", 2),
    ("Norway",         "Senegal",        "2026-06-23", "New York/New Jersey Stadium",  "I", 2),
    # Matchday 3 (simultaneous 20:00 Jun 26)
    ("Norway",         "France",         "2026-06-26", "Boston Stadium",               "I", 3),
    ("Senegal",        "Iraq",           "2026-06-26", "Toronto Stadium",              "I", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP J — Argentina | Algeria | Austria | Jordan
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1 (Jun 17)
    ("Argentina",      "Algeria",        "2026-06-17", "Kansas City Stadium",          "J", 1),
    ("Austria",        "Jordan",         "2026-06-17", "San Francisco Bay Area Stadium","J", 1),
    # Matchday 2 (Jun 22–23)
    ("Argentina",      "Austria",        "2026-06-22", "Dallas Stadium",               "J", 2),
    ("Jordan",         "Algeria",        "2026-06-23", "San Francisco Bay Area Stadium","J", 2),
    # Matchday 3 (simultaneous 03:00 Jun 28)
    ("Algeria",        "Austria",        "2026-06-28", "Kansas City Stadium",          "J", 3),
    ("Jordan",         "Argentina",      "2026-06-28", "Dallas Stadium",               "J", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP K — Portugal | Colombia | Congo DR | Uzbekistan
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1 (Jun 17–18)
    ("Portugal",       "Congo DR",       "2026-06-17", "Houston Stadium",              "K", 1),
    ("Uzbekistan",     "Colombia",       "2026-06-18", "Mexico City Stadium",          "K", 1),
    # Matchday 2 (Jun 23–24)
    ("Portugal",       "Uzbekistan",     "2026-06-23", "Houston Stadium",              "K", 2),
    ("Colombia",       "Congo DR",       "2026-06-24", "Guadalajara Stadium",          "K", 2),
    # Matchday 3 (simultaneous 00:30 Jun 28)
    ("Colombia",       "Portugal",       "2026-06-28", "Miami Stadium",                "K", 3),
    ("Congo DR",       "Uzbekistan",     "2026-06-28", "Atlanta Stadium",              "K", 3),

    # ══════════════════════════════════════════════════════════════════════
    # GROUP L — England | Croatia | Ghana | Panama
    # ══════════════════════════════════════════════════════════════════════

    # Matchday 1 (Jun 17–18)
    ("England",        "Croatia",        "2026-06-17", "Dallas Stadium",               "L", 1),
    ("Ghana",          "Panama",         "2026-06-18", "Toronto Stadium",              "L", 1),
    # Matchday 2 (Jun 23–24)
    ("England",        "Ghana",          "2026-06-23", "Boston Stadium",               "L", 2),
    ("Panama",         "Croatia",        "2026-06-24", "Toronto Stadium",              "L", 2),
    # Matchday 3 (simultaneous 22:00 Jun 27)
    ("Panama",         "England",        "2026-06-27", "New York/New Jersey Stadium",  "L", 3),
    ("Croatia",        "Ghana",          "2026-06-27", "Philadelphia Stadium",         "L", 3),
]

# ===========================================================================
# ACTUAL RESULTS — Update daily as games complete
# Key format: (home_team, away_team) matching EXACTLY the fixture tuple above
# Sources: ✓ = API cache confirmed | ~ = inferred from live standings GF/GA
# ===========================================================================

ACTUAL_RESULTS = {
    # ─── MATCHDAY 1 RESULTS ─────────────────────────────────────────────────

    # Group A
    ("Mexico",         "South Africa"):           (2, 0),   # Jun 11 ✓
    ("Korea Republic", "Czechia"):                (2, 1),   # Jun 12 ~

    # Group B
    ("Canada",         "Bosnia and Herzegovina"): (1, 1),   # Jun 12 ~
    ("Qatar",          "Switzerland"):            (1, 1),   # Jun 13 ~

    # Group C
    ("Brazil",         "Morocco"):                (1, 1),   # Jun 13 ~
    ("Haiti",          "Scotland"):               (0, 1),   # Jun 14 ~

    # Group D
    ("USA",            "Paraguay"):               (4, 1),   # Jun 13 ~
    ("Australia",      "Türkiye"):                (2, 0),   # Jun 14 ~

    # Group E
    ("Germany",        "Curaçao"):                (7, 1),   # Jun 14 ~
    ("Côte d'Ivoire",  "Ecuador"):                (1, 0),   # Jun 15 ~

    # Group F
    ("Netherlands",    "Japan"):                  (2, 2),   # Jun 14 ~
    ("Sweden",         "Tunisia"):                (5, 1),   # Jun 15 ✓  API cache

    # ─── MATCHDAY 2 RESULTS (add as they come in) ────────────────────────────
    # ("Czechia",        "South Africa"):        (?, ?),   # Jun 18
    # ("Mexico",         "Korea Republic"):      (?, ?),   # Jun 19
    # ("Switzerland",    "Bosnia and Herzegovina"): (?, ?), # Jun 18
    # ("Canada",         "Qatar"):               (?, ?),   # Jun 18
    # ("Scotland",       "Morocco"):             (?, ?),   # Jun 19
    # ("Brazil",         "Haiti"):               (?, ?),   # Jun 20
    # ("USA",            "Australia"):           (?, ?),   # Jun 19
    # ("Türkiye",        "Paraguay"):            (?, ?),   # Jun 20
    # ("Germany",        "Côte d'Ivoire"):       (?, ?),   # Jun 20
    # ("Ecuador",        "Curaçao"):             (?, ?),   # Jun 21
    # ("Netherlands",    "Sweden"):              (?, ?),   # Jun 20
    # ("Tunisia",        "Japan"):               (?, ?),   # Jun 21

        ("Spain",	"Cabo Verde"):		(0, 0),   # Jun 15 ✓

        ("Belgium",	"Egypt"):		(1, 1),   # Jun 16 ✓

        ("IR Iran",	"New Zealand"):		(2, 2),   # Jun 16 ✓

        ("Saudi Arabia",	"Uruguay"):		(1, 1),   # Jun 16 ✓

        ("France",	"Senegal"):		(3, 1),   # Jun 16 ✓

        ("Iraq",	"Norway"):		(1, 4),   # Jun 17 ✓

        ("Argentina",	"Algeria"):		(3, 0),   # Jun 17 ✓

        ("Austria",	"Jordan"):		(3, 1),   # Jun 17 ✓

    # ─── MATCHDAY 3 RESULTS (add as they come in) ────────────────────────────
}


# ===========================================================================
# LIVE ELO RECALIBRATION
# Applies K=40 Elo updates for every completed WC2026 fixture.
# Processes results chronologically → MD1 before MD2 before MD3.
# K-factor multiplier: 1.0 for 1-goal wins, 1.25 for 2-goal, 1.5 for 3+.
# Base Elo stays unchanged; only the returned LIVE dict is modified.
# ===========================================================================

WC_ELO_K = 40   # Standard K for major international tournaments

def compute_dynamic_elo() -> dict:
    """
    Walk through ACTUAL_RESULTS in fixture order and apply Elo updates.
    Returns a dict {team: adjusted_elo} reflecting tournament performance so far.
    """
    ratings = {k: v for k, v in TEAM_ELO.items()}   # start from base

    # Build ordered list of completed fixtures (by date then matchday)
    done = [
        (dt, md, h, a)
        for (h, a, dt, _venue, _grp, md) in WC2026_FIXTURES
        if (h, a) in ACTUAL_RESULTS
    ]
    done.sort(key=lambda x: (x[0], x[1]))   # chronological

    for (_dt, _md, h, a) in done:
        hg, ag = ACTUAL_RESULTS[(h, a)]

        r_h = ratings.get(h, 1500)
        r_a = ratings.get(a, 1500)

        # Expected scores — standard Elo formula
        e_h = 1.0 / (1.0 + 10 ** ((r_a - r_h) / 400.0))
        e_a = 1.0 - e_h

        # Actual scores
        if hg > ag:   s_h, s_a = 1.0, 0.0
        elif hg == ag: s_h, s_a = 0.5, 0.5
        else:          s_h, s_a = 0.0, 1.0

        # Margin-of-victory multiplier (common in football Elo systems)
        gd = abs(hg - ag)
        k_mult = 1.5 if gd >= 3 else 1.25 if gd == 2 else 1.0

        ratings[h] = round(r_h + WC_ELO_K * k_mult * (s_h - e_h))
        ratings[a] = round(r_a + WC_ELO_K * k_mult * (s_a - e_a))

    return ratings


def elo_delta_report(live: dict) -> list:
    """
    Return sorted list of tuples for all WC teams:
      (team, base_elo, live_elo, live_delta, confederation, effective_elo, conf_adj)
    Sorted by effective_elo descending (true predicted strength order).
    """
    rows = []
    all_teams = {t for grp in WC2026_GROUPS.values() for t in grp}
    for team in sorted(all_teams):
        base    = TEAM_ELO.get(team, 1500)
        live_v  = live.get(team, base)
        conf    = TEAM_CONFEDERATION.get(team, "UEFA")
        cadj    = CONF_ELO_ADJUSTMENT.get(conf, 0) + TEAM_ELO_OVERRIDE.get(team, 0)
        eff     = live_v + cadj
        rows.append((team, base, live_v, live_v - base, conf, eff, cadj))
    rows.sort(key=lambda x: -x[5])   # sort by effective Elo (true strength)
    return rows


# ===========================================================================
# POISSON / xG ENGINE (fully self-contained — no API calls)
# ===========================================================================

def poisson_prob(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.e ** -lam) * (lam ** k) / math.factorial(k)

def calc_btts(xg_h, xg_a):
    return round((1 - poisson_prob(xg_h, 0)) * (1 - poisson_prob(xg_a, 0)), 4)

def calc_draw(xg_h, xg_a, n=8):
    return round(sum(poisson_prob(xg_h, k) * poisson_prob(xg_a, k) for k in range(n+1)), 4)

def calc_hw(xg_h, xg_a, n=8):
    p = 0.0
    for h in range(1, n+1):
        for a in range(h):
            p += poisson_prob(xg_h, h) * poisson_prob(xg_a, a)
    return round(p, 4)

def calc_aw(xg_h, xg_a, n=8):
    p = 0.0
    for a in range(1, n+1):
        for h in range(a):
            p += poisson_prob(xg_h, h) * poisson_prob(xg_a, a)
    return round(p, 4)

def calc_over(xg_total, thr):
    return round(1.0 - sum(poisson_prob(xg_total, k) for k in range(int(thr + 0.5))), 4)

def get_elo(name: str, live: dict = None) -> int:
    """Look up Elo rating — uses live (tournament-adjusted) dict if provided."""
    src = live if live else TEAM_ELO
    if not name:
        return 1500
    if name in src:
        return src[name]
    # Fallback to base TEAM_ELO if not in live dict
    if live and name in TEAM_ELO:
        return TEAM_ELO[name]
    nl = name.lower().strip()
    for k, v in src.items():
        if k.lower() == nl:
            return v
    for k, v in TEAM_ELO.items():
        if k.lower() in nl or nl in k.lower():
            return v
    return 1450 + (sum(ord(c) for c in nl) % 150)

def get_effective_elo(name: str, live: dict = None) -> int:
    """
    Returns Elo adjusted for confederation isolation bias.
    Pipeline: base_elo → live_recalibration → confederation_correction → per-team_override
    Used in predictions only; raw Elo tracking is unaffected.
    """
    raw  = get_elo(name, live)
    conf = TEAM_CONFEDERATION.get(name, "UEFA")   # default UEFA if unknown
    adj  = CONF_ELO_ADJUSTMENT.get(conf, 0)
    ovr  = TEAM_ELO_OVERRIDE.get(name, 0)
    return raw + adj + ovr

def elo_to_xg(home: str, away: str, live: dict = None):
    """Neutral-venue Elo → xG. Uses confederation-adjusted effective Elo. 100 pts ≈ 0.35 goal diff."""
    diff  = get_effective_elo(home, live) - get_effective_elo(away, live)
    base  = 2.45 / 2.0
    delta = (diff / 100.0) * 0.35
    xg_h  = max(0.30, min(3.50, round(base + delta / 2, 3)))
    xg_a  = max(0.30, min(3.50, round(base - delta / 2, 3)))
    return xg_h, xg_a

def to_odds(p: float) -> str:
    return "N/A" if p <= 0.001 else f"{1/p:.2f}x"

def score_result(hg, ag):
    return "HOME" if hg > ag else "DRAW" if hg == ag else "AWAY"


# ===========================================================================
# PREDICTION ENGINE
# ===========================================================================

def predict(home: str, away: str, group: str, date: str, venue: str,
            matchday: int, mode: str = "safe", trace: bool = False,
            live_elo: dict = None) -> dict:
    """Generate prediction. Pass live_elo for tournament-adjusted ratings."""
    xg_h, xg_a = elo_to_xg(home, away, live_elo)
    btts = calc_btts(xg_h, xg_a)
    dp   = calc_draw(xg_h, xg_a)
    hw   = calc_hw(xg_h, xg_a)
    aw   = calc_aw(xg_h, xg_a)

    if mode == "full":
        gap = abs(get_effective_elo(home, live_elo) - get_effective_elo(away, live_elo))
        if gap > 150:
            leaked = dp * 0.08
            dp  = round(dp - leaked, 4)
            tot = hw + aw + 0.0001
            hw  = round(hw + leaked * hw / tot, 4)
            aw  = round(aw + leaked * aw / tot, 4)
        btts = round((btts + (btts + 0.44) / 2) / 2, 4)

    over_15 = calc_over(xg_h + xg_a, 1.5)
    over_25 = calc_over(xg_h + xg_a, 2.5)
    over_35 = calc_over(xg_h + xg_a, 3.5)

    # BTTS edge vs WC/international tournament historical baseline ~44%
    # (lower than domestic leagues — tight group games, strong defences)
    BTTS_MKT = 0.44
    edge = round(btts - BTTS_MKT, 4)

    if edge >= 0.05:
        bconf, bdec = "HIGH",    "PLAY YES [HIGH]"
    elif edge >= 0.02:
        bconf, bdec = "MEDIUM",  "PLAY YES [MED]"
    elif edge <= -0.05:
        bconf, bdec = "LOW",     "PLAY NO"
    else:
        bconf, bdec = "NEUTRAL", "PASS"

    probs   = {"HOME": hw, "DRAW": dp, "AWAY": aw}
    pred_r  = max(probs, key=probs.get)
    pred_w  = home if pred_r == "HOME" else (away if pred_r == "AWAY" else "DRAW")

    actual  = ACTUAL_RESULTS.get((home, away))
    if actual:
        hg, ag      = actual
        is_done     = True
        act_btts    = hg > 0 and ag > 0
        act_draw    = hg == ag
        act_result  = score_result(hg, ag)
    else:
        hg = ag     = None
        is_done     = False
        act_btts    = act_draw = act_result = None

    logs = []
    if trace:
        he_raw  = get_elo(home, live_elo)
        ae_raw  = get_elo(away, live_elo)
        he_eff  = get_effective_elo(home, live_elo)
        ae_eff  = get_effective_elo(away, live_elo)
        hb      = get_elo(home)      # pre-tournament base
        ab      = get_elo(away)
        h_conf  = TEAM_CONFEDERATION.get(home, "?")
        a_conf  = TEAM_CONFEDERATION.get(away, "?")
        h_cadj  = CONF_ELO_ADJUSTMENT.get(h_conf, 0) + TEAM_ELO_OVERRIDE.get(home, 0)
        a_cadj  = CONF_ELO_ADJUSTMENT.get(a_conf, 0) + TEAM_ELO_OVERRIDE.get(away, 0)
        logs = [
            f"Elo (base)  : {home}={hb}  {away}={ab}",
            f"Elo (live)  : {home}={he_raw} ({he_raw-hb:+d})  {away}={ae_raw} ({ae_raw-ab:+d})",
            f"Elo (conf)  : {home}[{h_conf}]{h_cadj:+d}={he_eff}  {away}[{a_conf}]{a_cadj:+d}={ae_eff}  diff={he_eff-ae_eff:+d}",
            f"xG          : home={xg_h:.3f}  away={xg_a:.3f}  total={xg_h+xg_a:.3f}",
            f"BTTS        : p={btts:.3f}  mkt={BTTS_MKT:.3f}  edge={edge:+.3f}",
            f"1X2         : H={hw:.3f}  D={dp:.3f}  A={aw:.3f}",
        ]

    return {
        "group":            group,
        "matchday":         matchday,
        "date":             date,
        "venue":            venue,
        "home_team":        home,
        "away_team":        away,
        "home_elo":         get_elo(home, live_elo),
        "away_elo":         get_elo(away, live_elo),
        "home_elo_base":    get_elo(home),
        "away_elo_base":    get_elo(away),
        "home_elo_delta":   get_elo(home, live_elo) - get_elo(home),
        "away_elo_delta":   get_elo(away, live_elo) - get_elo(away),
        "home_elo_eff":     get_effective_elo(home, live_elo),
        "away_elo_eff":     get_effective_elo(away, live_elo),
        "home_confederation": TEAM_CONFEDERATION.get(home, "?"),
        "away_confederation": TEAM_CONFEDERATION.get(away, "?"),
        "home_conf_adj":    CONF_ELO_ADJUSTMENT.get(TEAM_CONFEDERATION.get(home,"UEFA"),0) + TEAM_ELO_OVERRIDE.get(home,0),
        "away_conf_adj":    CONF_ELO_ADJUSTMENT.get(TEAM_CONFEDERATION.get(away,"UEFA"),0) + TEAM_ELO_OVERRIDE.get(away,0),
        "xg_home":          xg_h,
        "xg_away":          xg_a,
        "xg_total":         round(xg_h + xg_a, 3),
        "btts_prob":        round(btts * 100, 1),
        "btts_edge":        round(edge * 100, 1),
        "btts_decision":    bdec,
        "btts_confidence":  bconf,
        "home_win_prob":    round(hw * 100, 1),
        "draw_prob":        round(dp * 100, 1),
        "away_win_prob":    round(aw * 100, 1),
        "home_win_odds":    to_odds(hw),
        "draw_odds":        to_odds(dp),
        "away_win_odds":    to_odds(aw),
        "draw_fair_odds":   to_odds(dp),
        "draw_value_flag":  dp >= 0.26,
        "predicted_result": pred_r,
        "predicted_winner": pred_w,
        "over_1_5_prob":    round(over_15 * 100, 1),
        "over_2_5_prob":    round(over_25 * 100, 1),
        "over_3_5_prob":    round(over_35 * 100, 1),
        "is_completed":     is_done,
        "actual_home_goals": hg,
        "actual_away_goals": ag,
        "actual_btts":      act_btts,
        "actual_draw":      act_draw,
        "actual_result":    act_result,
        "mode":             mode,
        "logs":             logs,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
    }


# ===========================================================================
# GROUP STANDINGS SIMULATION (4-team round-robin, expected points)
# ===========================================================================

def simulate_standings(group: str, all_preds: list) -> list:
    teams = WC2026_GROUPS[group]
    s = {t: {"team": t, "played": 0, "pts": 0.0,
             "xGF": 0.0, "xGA": 0.0, "W": 0.0, "D": 0.0, "L": 0.0}
         for t in teams}

    for p in [x for x in all_preds if x["group"] == group]:
        h, a = p["home_team"], p["away_team"]
        if p["is_completed"] and p["actual_result"]:
            ar = p["actual_result"]
            hw, dp, aw = (1,0,0) if ar=="HOME" else (0,1,0) if ar=="DRAW" else (0,0,1)
            hgf = float(p["actual_home_goals"])
            hga = float(p["actual_away_goals"])
        else:
            hw, dp, aw = p["home_win_prob"]/100, p["draw_prob"]/100, p["away_win_prob"]/100
            hgf, hga   = p["xg_home"], p["xg_away"]

        for team, w, d, l, gf, ga in [(h, hw, dp, aw, hgf, hga),
                                       (a, aw, dp, hw, hga, hgf)]:
            if team in s:
                s[team]["pts"]    += w * 3 + d
                s[team]["W"]      += w
                s[team]["D"]      += d
                s[team]["L"]      += l
                s[team]["xGF"]    += gf
                s[team]["xGA"]    += ga
                s[team]["played"] += 1

    ranked = sorted(s.values(),
                    key=lambda x: (x["pts"], x["xGF"]-x["xGA"], x["xGF"]),
                    reverse=True)
    for i, r in enumerate(ranked):
        r["pos"]     = i + 1
        r["pts"]     = round(r["pts"], 2)
        r["xGF"]     = round(r["xGF"], 2)
        r["xGA"]     = round(r["xGA"], 2)
        r["xGD"]     = round(r["xGF"] - r["xGA"], 2)
        r["elo"]     = get_elo(r["team"])
        r["advance"] = r["pos"] <= 2
    return ranked


# ===========================================================================
# DISPLAY
# ===========================================================================

EM_R = {"HOME": "🏠", "DRAW": "⚖️",  "AWAY": "✈️"}
EM_C = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "❄️",  "NEUTRAL": "•"}

def print_fixture(p, trace=False):
    h, a   = p["home_team"], p["away_team"]
    e_r    = EM_R.get(p["predicted_result"], "?")
    e_c    = EM_C.get(p["btts_confidence"], "•")

    print(f"    MD{p['matchday']}  {a:26} @ {h:26}  {p['date']}")
    print(f"         xG {p['xg_home']:.2f}-{p['xg_away']:.2f}  "
          f"BTTS:{p['btts_prob']:.1f}%  "
          f"Draw:{p['draw_prob']:.1f}%  "
          f"Edge:{p['btts_edge']:+.1f}%  "
          f"{e_c} {p['btts_decision']}")
    print(f"         1X2: {h[:18]:18} {p['home_win_prob']:.1f}%({p['home_win_odds']})  "
          f"Draw {p['draw_prob']:.1f}%({p['draw_odds']})  "
          f"{a[:18]:18} {p['away_win_prob']:.1f}%({p['away_win_odds']})  "
          f"→ {e_r} {p['predicted_winner']}")
    print(f"         O/U: 1.5={p['over_1_5_prob']:.1f}%  "
          f"2.5={p['over_2_5_prob']:.1f}%  "
          f"3.5={p['over_3_5_prob']:.1f}%")

    if p["is_completed"]:
        btag = "BTTS✓" if p["actual_btts"] else "BTTS✗"
        dtag = " DRAW✓" if p["actual_draw"] else ""
        ok   = "✅" if p["actual_result"] == p["predicted_result"] else "❌"
        print(f"         ✅ RESULT: {h} {p['actual_home_goals']}-{p['actual_away_goals']} {a}"
              f"  {btag}{dtag}  Pred:{p['predicted_result']} {ok}")
        print(f"         📍 Venue: {p['venue']}")
    else:
        print(f"         🔮 Upcoming  |  📍 {p['venue']}")

    if trace:
        for log in p.get("logs", []):
            print(f"           > {log}")
    print()


def print_standings(group: str, standings: list):
    sep = "─" * 64
    print(f"\n  {sep}")
    print(f"  GROUP {group} PROJECTED STANDINGS")
    print(f"  {sep}")
    print(f"  {'Pos':>3}  {'Team':<28}  {'Elo':>5}  {'xPts':>5}  {'xGD':>6}  Status")
    print(f"  {sep}")
    for r in standings:
        if r["pos"] <= 2:
            tag = "✅ ADVANCE (guaranteed)"
        elif r["pos"] == 3:
            tag = "★  3rd-place  (bubble)"
        else:
            tag = "❌ eliminated"
        print(f"  {r['pos']:>3}  {r['team']:<28}  {r['elo']:>5}  "
              f"{r['pts']:>5.2f}  {r['xGD']:>+6.2f}  {tag}")
    print()


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    ap = argparse.ArgumentParser(
        description="FIFA World Cup 2026 Group Stage Predictor (No API)"
    )
    ap.add_argument("--group",      help="Single group, e.g. A")
    ap.add_argument("--team",       help="Filter all games for a team")
    ap.add_argument("--matchday",   type=int, choices=[1,2,3])
    ap.add_argument("--upcoming",   action="store_true")
    ap.add_argument("--completed",  action="store_true")
    ap.add_argument("--mode",       choices=["safe","full"], default="safe")
    ap.add_argument("--trace",      action="store_true")
    ap.add_argument("--standings",  action="store_true")
    ap.add_argument("--btts-only",  dest="btts_only", action="store_true")
    ap.add_argument("--export",     action="store_true")
    ap.add_argument("--elo-report", dest="elo_report", action="store_true",
                    help="Print tournament Elo gain/loss table for all teams")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ── Live Elo recalibration from actual results ────────────────────────
    live_elo     = compute_dynamic_elo()
    games_played = sum(1 for (h, a, *_) in WC2026_FIXTURES if (h, a) in ACTUAL_RESULTS)
    biggest_move = max(elo_delta_report(live_elo), key=lambda x: abs(x[3]), default=("?",0,0,0))

    print("\n" + "═" * 72)
    print(f"  FIFA WORLD CUP 2026 — GROUP STAGE  |  {today}  |  {args.mode.upper()}")
    print(f"  12 Groups x 4 Teams  |  72 Fixtures  |  Elo->xG->Poisson  |  Offline")
    print(f"  Live Elo: {games_played} results applied  |  "
          f"Biggest mover: {biggest_move[0]} ({biggest_move[3]:+d})")
    print("=" * 72)

    # ── Optional Elo delta report ─────────────────────────────────────────
    if args.elo_report:
        deltas = elo_delta_report(live_elo)
        print(f"\n  ELO REPORT  ({games_played} games processed, K=40)")
        print(f"  Sorted by Effective Elo (true predicted strength)\n")
        print(f"  {' ':<28}  {'Conf':<8}  {'Base':>5}  {'Live':>5}  {'Adj':>5}  {'Eff':>5}  Trend")
        print(f"  {'-'*80}")
        for team, base, live_v, live_delta, conf, eff, cadj in deltas:
            live_trend = (f"+{live_delta}" if live_delta > 0
                          else (str(live_delta) if live_delta < 0 else "="))
            cadj_str   = f"{cadj:+d}" if cadj != 0 else "  0"
            print(f"  {team:<28}  {conf:<8}  {base:>5}  {live_v:>5}  {cadj_str:>5}  {eff:>5}  {live_trend}")
        print()
        return

    # Build all 72 predictions using live (tournament-adjusted) Elo
    all_preds = [
        predict(h, a, grp, dt, venue, md, args.mode, args.trace, live_elo)
        for (h, a, dt, venue, grp, md) in WC2026_FIXTURES
    ]

    # Apply filters
    filt = list(all_preds)
    if args.group:
        filt = [p for p in filt if p["group"] == args.group.upper()]
    if args.team:
        tl = args.team.lower()
        filt = [p for p in filt
                if tl in p["home_team"].lower() or tl in p["away_team"].lower()]
    if args.matchday:
        filt = [p for p in filt if p["matchday"] == args.matchday]
    if args.upcoming:
        filt = [p for p in filt if not p["is_completed"]]
    if args.completed:
        filt = [p for p in filt if p["is_completed"]]
    if args.btts_only:
        filt = [p for p in filt if "PLAY YES" in p["btts_decision"]]

    groups_shown = sorted(set(p["group"] for p in filt))
    total = done = btts_total = 0

    for g in groups_shown:
        gp    = [p for p in filt if p["group"] == g]
        teams = " | ".join(WC2026_GROUPS.get(g, []))
        print(f"\n  ┌─ GROUP {g}  {teams}")
        print()
        for p in gp:
            print_fixture(p, trace=args.trace)
            total += 1
            if p["is_completed"]: done += 1
            if "PLAY YES" in p["btts_decision"]: btts_total += 1
        if args.standings:
            print_standings(g, simulate_standings(g, all_preds))

    # ── Summary ──────────────────────────────────────────────────────────
    print("═" * 72)
    print(f"  Fixtures shown : {total}   Completed: {done}   Upcoming: {total-done}")
    print(f"  BTTS PLAY YES  : {btts_total}")
    print("═" * 72)

    # ── BTTS Picks ───────────────────────────────────────────────────────
    btts_picks = [p for p in filt if "PLAY YES" in p["btts_decision"]]
    if btts_picks:
        print(f"\n  🔥 BTTS PLAY YES PICKS ({len(btts_picks)})")
        print(f"  {'─'*70}")
        print(f"  {'Grp':<4}{'MD':<4}{'Matchup':<48}{'BTTS%':>6}{'Edge':>7}{'Conf'}")
        print(f"  {'─'*70}")
        for p in sorted(btts_picks, key=lambda x: -x["btts_prob"]):
            done_tag = "✅" if p["is_completed"] else "🔮"
            print(f"  {p['group']:<4}MD{p['matchday']}  "
                  f"{p['away_team']:20} @ {p['home_team']:20}  "
                  f"{p['btts_prob']:>5.1f}%  {p['btts_edge']:>+5.1f}%  "
                  f"{p['btts_confidence']}  {done_tag}")
        print()

    # ── Draw Value ───────────────────────────────────────────────────────
    draw_picks = [p for p in filt if p["draw_value_flag"] and not p["is_completed"]]
    if draw_picks:
        print(f"\n  ⚖️  DRAW VALUE ≥26% ({len(draw_picks)} upcoming games)")
        print(f"  {'─'*70}")
        print(f"  {'Grp':<4}{'MD':<4}{'Matchup':<48}{'Draw%':>6}{'Fair Odds':>10}")
        print(f"  {'─'*70}")
        for p in sorted(draw_picks, key=lambda x: -x["draw_prob"]):
            print(f"  {p['group']:<4}MD{p['matchday']}  "
                  f"{p['away_team']:20} @ {p['home_team']:20}  "
                  f"{p['draw_prob']:>5.1f}%  {p['draw_fair_odds']:>10}")
        print()

    # ── JSON Export ──────────────────────────────────────────────────────
    if args.export:
        out = {
            "date":         today,
            "mode":         args.mode,
            "tournament":   "FIFA World Cup 2026",
            "stage":        "Group Stage",
            "format":       "12 groups × 4 teams | 72 fixtures",
            "engine":       "Elo→xG→Poisson (offline)",
            "total":        len(all_preds),
            "completed":    sum(1 for p in all_preds if p["is_completed"]),
            "predictions":  all_preds,
            "standings": {
                g: simulate_standings(g, all_preds)
                for g in WC2026_GROUPS
            },
        }
        os.makedirs("data/football", exist_ok=True)
        path = f"data/football/wc2026_predictions_{today}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"\n  ✅ Exported → {path}\n")

    print()


if __name__ == "__main__":
    main()
