import sqlite3
import argparse
import datetime
import statsapi
import os
import concurrent.futures

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'mlb_history.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pitcher_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        date TEXT,
        team_id INTEGER,
        pitcher_id INTEGER,
        is_starter INTEGER,
        ip REAL,
        hr INTEGER,
        bb INTEGER,
        k INTEGER
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pitcher_date ON pitcher_logs(pitcher_id, date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_date ON pitcher_logs(team_id, date, is_starter)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_game ON pitcher_logs(game_id)')
    
    conn.commit()
    return conn

def parse_ip(ip_str):
    try:
        if not ip_str: return 0.0
        parts = str(ip_str).split('.')
        full = float(parts[0])
        if len(parts) > 1:
            partial = float(parts[1])
            if partial == 1: full += 0.333
            elif partial == 2: full += 0.667
        return full
    except Exception:
        return 0.0

def fetch_day_games(date_str):
    try:
        schedule = statsapi.schedule(date=date_str, sportId=1)
        games = []
        for game in schedule:
            if game['status'] in ('Final', 'Completed Early'):
                games.append((date_str, game['game_id'], game['away_id'], game['home_id']))
        return games
    except Exception:
        return []

def fetch_boxscore(game_data):
    try:
        box = statsapi.boxscore_data(game_data[1])
        return (game_data, box)
    except Exception:
        return (game_data, None)

def process_pitchers(cursor, gid, date_str, team_id, pitchers):
    for i, p in enumerate(pitchers):
        if i == 0 or p.get('personId') == 0: continue
        is_starter = 1 if i == 1 else 0
        ip = parse_ip(p.get('ip', '0.0'))
        hr = int(p.get('hr', 0))
        bb = int(p.get('bb', 0))
        k = int(p.get('k', 0))
        pid = p.get('personId', 0)
        if pid == 0: continue
        
        cursor.execute('''
        INSERT INTO pitcher_logs (game_id, date, team_id, pitcher_id, is_starter, ip, hr, bb, k)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (gid, date_str, team_id, pid, is_starter, ip, hr, bb, k))

def build_db(start_date_str, end_date_str):
    conn = init_db()
    cursor = conn.cursor()
    
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    current_date = start_date
    delta = datetime.timedelta(days=1)
    
    dates = []
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += delta
        
    print(f"Fetching schedule for {len(dates)} days...")
    all_games = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for r in executor.map(fetch_day_games, dates):
            all_games.extend(r)
            
    print(f"Found {len(all_games)} completed games.")
    
    games_to_fetch = []
    for g in all_games:
        cursor.execute('SELECT 1 FROM pitcher_logs WHERE game_id = ? LIMIT 1', (g[1],))
        if not cursor.fetchone():
            games_to_fetch.append(g)
            
    print(f"Downloading {len(games_to_fetch)} new boxscores...")
    
    count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for game_data, box in executor.map(fetch_boxscore, games_to_fetch):
            if not box: continue
            
            date_str, gid, away_id, home_id = game_data
            process_pitchers(cursor, gid, date_str, away_id, box.get('awayPitchers', []))
            process_pitchers(cursor, gid, date_str, home_id, box.get('homePitchers', []))
            
            count += 1
            if count % 50 == 0:
                print(f"  Processed {count}/{len(games_to_fetch)}...")
                conn.commit()
                
    conn.commit()
    conn.close()
    print("Database build complete!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', type=str, required=True)
    parser.add_argument('--end-date', type=str, required=True)
    args = parser.parse_args()
    build_db(args.start_date, args.end_date)
