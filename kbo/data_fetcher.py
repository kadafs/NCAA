"""
kbo/data_fetcher.py
Provides team stats (wRC+, FIP) and park factors for the KBO League.
Since we lack a reliable free dynamic scraper, we use static mid-season 2026 statistics.
"""

KBO_PARK_FACTORS = {
    'Jamsil': 0.95,      # Doosan, LG
    'Gocheok': 0.99,     # Kiwoom
    'Munhak': 1.06,      # SSG
    'Changwon': 1.03,    # NC
    'Gwangju': 1.01,     # KIA
    'Sajik': 0.97,       # Lotte
    'Daegu': 1.07,       # Samsung
    'Daejeon': 1.00,     # Hanwha
    'Suwon': 1.04,       # KT
    'KBO Stadium': 1.00  # Default fallback
}

# Calculated from 2026 mid-season R/G and RA/G
# League average R/G is approx 4.8. 
STATIC_METRICS = {
    'Samsung Lions': {'wRC+': 114, 'FIP': 4.10, 'wOBA': .350},
    'Hanwha Eagles': {'wRC+': 113, 'FIP': 4.50, 'wOBA': .348},
    'KT Wiz': {'wRC+': 107, 'FIP': 4.55, 'wOBA': .340},
    'KIA Tigers': {'wRC+': 106, 'FIP': 4.36, 'wOBA': .338},
    'LG Twins': {'wRC+': 102, 'FIP': 4.33, 'wOBA': .330},
    'NC Dinos': {'wRC+': 101, 'FIP': 4.53, 'wOBA': .328},
    'SSG Landers': {'wRC+': 99, 'FIP': 5.86, 'wOBA': .325},
    'Doosan Bears': {'wRC+': 94, 'FIP': 4.12, 'wOBA': .315},
    'Lotte Giants': {'wRC+': 88, 'FIP': 4.54, 'wOBA': .305},
    'Kiwoom Heroes': {'wRC+': 69, 'FIP': 5.03, 'wOBA': .275},
}

def get_team_metrics(team_name: str) -> dict:
    """Returns dict with keys: wRC+, FIP, wOBA"""
    return STATIC_METRICS.get(team_name, {'wRC+': 100, 'FIP': 4.50, 'wOBA': .320})

def get_park_factor(venue: str) -> float:
    return KBO_PARK_FACTORS.get(venue, 1.0)
