import pybaseball
from pybaseball import pitching_stats, team_batting
from datetime import datetime

def get_pitching_siera(year=None):
    if not year:
        year = datetime.now().year
    print(f"Fetching pitching SIERA for {year}...")
    try:
        # qual=10 means minimum 10 innings pitched to filter out non-starters
        stats = pitching_stats(year, year, qual=10)
        # We need Name and SIERA, xFIP, K-BB%
        pitcher_metrics = stats[['Name', 'Team', 'IP', 'SIERA', 'xFIP', 'K-BB%']]
        return pitcher_metrics
    except Exception as e:
        print(f"Error fetching pitching stats: {e}")
        return None

def get_team_wrc_plus(year=None):
    """
    Get Team wRC+. For simplicity in V1, we use overall team batting stats. 
    """
    if not year:
        year = datetime.now().year
    print(f"Fetching team wRC+ for {year}...")
    try:
        stats = team_batting(year, year)
        # We need Team and wRC+
        team_metrics = stats[['Team', 'wRC+']]
        return team_metrics
    except Exception as e:
        print(f"Error fetching team batting stats: {e}")
        return None

if __name__ == "__main__":
    pitching = get_pitching_siera()
    if pitching is not None:
        print("\nTop 5 Pitchers by SIERA:")
        print(pitching.sort_values(by='SIERA').head(5))
        
    batting = get_team_wrc_plus()
    if batting is not None:
        print("\nTop 5 Teams by wRC+:")
        print(batting.sort_values(by='wRC+', ascending=False).head(5))
