import requests
from bs4 import BeautifulSoup
import datetime
import concurrent.futures

# Map Yahoo Japan team names to standard english
TEAM_MAP = {
    'ヤクルト': 'Yakult Swallows',
    '東京ヤクルトスワローズ': 'Yakult Swallows',
    '巨人': 'Yomiuri Giants',
    '読売ジャイアンツ': 'Yomiuri Giants',
    '阪神': 'Hanshin Tigers',
    '阪神タイガース': 'Hanshin Tigers',
    '広島': 'Hiroshima Carp',
    '広島東洋カープ': 'Hiroshima Carp',
    '中日': 'Chunichi Dragons',
    '中日ドラゴンズ': 'Chunichi Dragons',
    'DeNA': 'Yokohama DeNA BayStars',
    '横浜DeNAベイスターズ': 'Yokohama DeNA BayStars',
    'オリックス': 'Orix Buffaloes',
    'オリックス・バファローズ': 'Orix Buffaloes',
    'ロッテ': 'Chiba Lotte Marines',
    '千葉ロッテマリーンズ': 'Chiba Lotte Marines',
    '楽天': 'Rakuten Golden Eagles',
    '東北楽天ゴールデンイーグルス': 'Rakuten Golden Eagles',
    'ソフトバンク': 'Fukuoka SoftBank Hawks',
    '福岡ソフトバンクホークス': 'Fukuoka SoftBank Hawks',
    '日本ハム': 'Nippon-Ham Fighters',
    '北海道日本ハムファイターズ': 'Nippon-Ham Fighters',
    '西武': 'Saitama Seibu Lions',
    '埼玉西武ライオンズ': 'Saitama Seibu Lions'
}

NPB_PARK_FACTORS = {
    '神宮': 1.15,
    '横浜スタジアム': 1.08,
    '東京ドーム': 1.05,
    'エスコンフィールド': 1.02,
    'マツダスタジアム': 1.00,
    'ベルーナドーム': 1.00,
    '楽天モバイル': 0.98,
    'ZOZOマリン': 0.95,
    'PayPayドーム': 0.95,
    '京セラドーム大阪': 0.92,
    '甲子園': 0.90,
    'バンテリンドーム': 0.85
}

NPB_WEATHER_COORDS = {
    '神宮': (35.6744, 139.7171),
    '横浜スタジアム': (35.4433, 139.6400),
    'マツダスタジアム': (34.3917, 132.4847),
    '甲子園': (34.7214, 135.3617),
    'ZOZOマリン': (35.6452, 140.0308),
    '楽天モバイル': (38.2564, 140.9026)
}

_cached_team_stats = None
_cached_form_factors = None

def _scrape_team_stats():
    global _cached_team_stats
    if _cached_team_stats is not None:
        return _cached_team_stats
        
    url = 'https://baseball.yahoo.co.jp/npb/standings/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    stats_dict = {}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tables = soup.find_all('table')
        if len(tables) < 2:
            return None
            
        total_runs = 0
        total_games = 0
        
        # Parse Central and Pacific Leagues
        for t_idx in [0, 1]:
            rows = tables[t_idx].find_all('tr')
            for row in rows[1:]: # Skip header
                cells = [td.text.strip() for td in row.find_all(['th', 'td'])]
                if len(cells) < 15:
                    continue
                    
                team_jp = cells[1]
                team_eng = TEAM_MAP.get(team_jp, team_jp)
                games = int(cells[2])
                runs = int(cells[9])
                era = float(cells[14])
                
                total_runs += runs
                total_games += games
                
                stats_dict[team_eng] = {
                    'games': games,
                    'runs': runs,
                    'era': era
                }
                
        if total_games > 0:
            league_avg_runs_per_game = total_runs / total_games
        else:
            league_avg_runs_per_game = 3.5 # Fallback
            
        for team, stats in stats_dict.items():
            team_rpg = stats['runs'] / stats['games'] if stats['games'] > 0 else league_avg_runs_per_game
            wrc_plus_proxy = (team_rpg / league_avg_runs_per_game) * 100
            stats['wrc_plus_proxy'] = round(wrc_plus_proxy, 2)
            
        _cached_team_stats = stats_dict
        return stats_dict
    except Exception as e:
        print(f"Error scraping NPB team stats: {e}")
        return None

def _fetch_team_recent_games(team_tuple):
    team_name_eng, team_id_str = team_tuple
    url = f"https://baseball.yahoo.co.jp/npb/teams/{team_id_str}/schedule"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all cells that have "試合終了" (Game Over)
        game_cells = []
        for td in soup.find_all('td'):
            if '試合終了' in td.text:
                game_cells.append(td)
                
        # We want the last 10 games, but the calendar is ordered by day, so the last ones in the list are the most recent.
        recent_games = game_cells[-10:]
        runs_scored_list = []
        
        for cell in recent_games:
            is_home = 'bb-calendarTable__data--home' in cell.get('class', [])
            is_away = 'bb-calendarTable__data--away' in cell.get('class', [])
            
            home_span = cell.find('span', class_='bb-calendarTable__home')
            away_span = cell.find('span', class_='bb-calendarTable__away')
            
            if home_span and away_span:
                home_runs = int(home_span.text.strip() or 0)
                away_runs = int(away_span.text.strip() or 0)
                
                if is_home:
                    runs_scored_list.append(home_runs)
                elif is_away:
                    runs_scored_list.append(away_runs)
                    
        if runs_scored_list:
            avg_runs = sum(runs_scored_list) / len(runs_scored_list)
        else:
            avg_runs = 3.5
            
        return team_name_eng, avg_runs, len(runs_scored_list), runs_scored_list
        
    except Exception as e:
        return team_name_eng, 3.5, 0, []

def _scrape_form_factors():
    global _cached_form_factors
    if _cached_form_factors is not None:
        return _cached_form_factors
        
    url = 'https://baseball.yahoo.co.jp/npb/teams/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        team_tuples = []
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if '/npb/teams/' in href and '/top' in href:
                jp_name = a.text.strip()
                eng_name = TEAM_MAP.get(jp_name)
                if eng_name:
                    team_id = href.split('/')[3]
                    team_tuples.append((eng_name, team_id))
                    
        # Concurrently fetch schedules
        form_dict = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            results = executor.map(_fetch_team_recent_games, team_tuples)
            for eng_name, avg_runs, count, raw_runs in results:
                # Compare to their season average
                season_stats = _scrape_team_stats()
                season_rpg = 3.5
                if season_stats and eng_name in season_stats:
                    s = season_stats[eng_name]
                    if s['games'] > 0:
                        season_rpg = s['runs'] / s['games']
                
                factor = avg_runs / season_rpg if season_rpg > 0 else 1.0
                # Clamp factor
                factor = min(max(factor, 0.75), 1.25)
                
                form_dict[eng_name] = {
                    'factor': round(factor, 3),
                    'raw_avg': round(avg_runs, 2),
                    'games_used': count,
                    'games_raw': raw_runs
                }
                
        _cached_form_factors = form_dict
        return form_dict
        
    except Exception as e:
        print(f"Error scraping NPB form factors: {e}")
        return {}

def _get_pitcher_urls(game_url):
    """Fetches a game page and extracts the away and home starting pitcher profile URLs."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        url = f"https://baseball.yahoo.co.jp{game_url}" if game_url.startswith('/') else game_url
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pitcher_links = []
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if '/npb/player/' in href and '/top' in href:
                if href not in pitcher_links:
                    pitcher_links.append(href)
                    
        away_url = pitcher_links[0] if len(pitcher_links) > 0 else None
        home_url = pitcher_links[1] if len(pitcher_links) > 1 else None
        return away_url, home_url
    except Exception as e:
        print(f"Error fetching pitcher urls from game page: {e}")
        return None, None

def get_today_games(date_str=None):
    """
    Scrapes today's schedule from Yahoo Japan Baseball.
    Returns a list of game dictionaries compatible with the MLB engine.
    """
    if not date_str:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    date_formatted = date_str.replace('-', '')
        
    url = f'https://baseball.yahoo.co.jp/npb/schedule/?date={date_formatted}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching NPB schedule: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    games = []
    
    items = soup.find_all('li', class_='bb-score__item')
    for item in items:
        try:
            a_tag = item.find('a', class_='bb-score__content')
            game_url = a_tag['href'] if a_tag else None
            
            home_team_tag = item.find('p', class_=lambda c: c and 'bb-score__homeLogo' in c)
            away_team_tag = item.find('p', class_=lambda c: c and 'bb-score__awayLogo' in c)
            
            if not home_team_tag or not away_team_tag:
                continue
                
            home_team_jp = home_team_tag.text.strip()
            away_team_jp = away_team_tag.text.strip()
            
            home_team = TEAM_MAP.get(home_team_jp, home_team_jp)
            away_team = TEAM_MAP.get(away_team_jp, away_team_jp)
            
            venue_tag = item.find('span', class_='bb-score__venue')
            venue = venue_tag.text.strip() if venue_tag else 'Unknown Venue'
            
            # Map the venue to a park factor
            park_factor = 1.0
            for key_venue, pf in NPB_PARK_FACTORS.items():
                if key_venue in venue:
                    park_factor = pf
                    break
            
            time_tag = item.find('time', class_='bb-score__status')
            game_time = time_tag.text.strip() if time_tag else 'TBD'
            
            home_pitcher = 'TBD'
            home_pitcher_tag = item.find('ul', class_='bb-score__home')
            if home_pitcher_tag:
                li = home_pitcher_tag.find('li', class_='bb-score__player')
                if li:
                    home_pitcher = li.text.strip().replace('(予)', '').strip()
                    
            away_pitcher = 'TBD'
            away_pitcher_tag = item.find('ul', class_='bb-score__away')
            if away_pitcher_tag:
                li = away_pitcher_tag.find('li', class_='bb-score__player')
                if li:
                    away_pitcher = li.text.strip().replace('(予)', '').strip()
            
            away_url, home_url = _get_pitcher_urls(game_url) if game_url else (None, None)
                    
            home_id = hash(home_team) % 10000
            away_id = hash(away_team) % 10000
            hp_id = hash(home_pitcher) % 10000 if home_pitcher != 'TBD' else 0
            ap_id = hash(away_pitcher) % 10000 if away_pitcher != 'TBD' else 0
            
            games.append({
                'game_id': f"{away_id}_{home_id}_{date_formatted}",
                'away_team': away_team,
                'home_team': home_team,
                'away_pitcher': away_pitcher,
                'home_pitcher': home_pitcher,
                'away_pitcher_url': away_url,
                'home_pitcher_url': home_url,
                'venue_name': venue,
                'park_factor': park_factor,
                'game_time': game_time,
                'away_abbr': away_team[:3].upper(),
                'home_abbr': home_team[:3].upper(),
                'away_id': away_id,
                'home_id': home_id,
                'away_pitcher_id': ap_id,
                'home_pitcher_id': hp_id
            })
        except Exception as e:
            print(f"Error parsing an NPB game: {e}")
            
    return games

def get_pitcher_stats(pitcher_name, player_url=None):
    """
    Scrape pitcher ERA, IP, HR, BB, K to calculate an NPB FIP.
    """
    default_stats = {
        'era': 3.15,
        'ip': 120.0,
        'projected_ip': 5.0,
        'hand': 'R',
        'hr': 10,
        'bb': 35,
        'k': 100,
        'fip': 3.15,
        'siera': 3.20,
        'xfip': 3.20
    }
    
    if not player_url:
        return default_stats
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        url = f"https://baseball.yahoo.co.jp{player_url}" if player_url.startswith('/') else player_url
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        hand = 'R'
        for dd in soup.find_all('dd'):
            text = dd.text
            if '右投' in text:
                hand = 'R'
                break
            elif '左投' in text:
                hand = 'L'
                break
        
        tables = soup.find_all('table')
        if not tables:
            return default_stats
            
        p_table = tables[0]
        rows = p_table.find_all('tr')
        if len(rows) < 4:
            return default_stats
            
        r1_cells = [td.text.strip() for td in rows[1].find_all('td')]
        if len(r1_cells) < 15:
            return default_stats
            
        era_str = r1_cells[0].replace('-', '0')
        ip_str = r1_cells[14].replace('-', '0')
        
        r2_cells = [td.text.strip() for td in rows[3].find_all('td')]
        if len(r2_cells) < 11:
            return default_stats
            
        hr_str = r2_cells[2].replace('-', '0')
        k_str = r2_cells[3].replace('-', '0')
        bb_str = r2_cells[5].replace('-', '0')
        hbp_str = r2_cells[6].replace('-', '0')
        
        era = float(era_str) if era_str else 3.15
        ip = float(ip_str) if ip_str else 0.1
        hr = float(hr_str) if hr_str else 0.0
        k = float(k_str) if k_str else 0.0
        bb = float(bb_str) if bb_str else 0.0
        hbp = float(hbp_str) if hbp_str else 0.0
        
        if ip <= 0:
            return default_stats
            
        fip = ((13 * hr) + (3 * (bb + hbp)) - (2 * k)) / ip + 3.15
        
        projected_ip = 5.0
        try:
            starts_str = r1_cells[2].replace('-', '0')
            starts = float(starts_str)
            if starts > 0:
                projected_ip = ip / starts
            elif ip > 0:
                projected_ip = 2.0
            else:
                projected_ip = 5.0
            projected_ip = min(max(projected_ip, 1.0), 9.0)
        except Exception:
            pass
        
        return {
            'era': era,
            'ip': ip,
            'projected_ip': round(projected_ip, 1),
            'hand': hand,
            'hr': hr,
            'bb': bb,
            'k': k,
            'fip': round(fip, 2),
            'siera': round(fip + 0.05, 2),
            'xfip': round(fip + 0.02, 2)
        }
        
    except Exception as e:
        print(f"Error scraping pitcher stats for {pitcher_name}: {e}")
        return default_stats

def get_team_stats(team_name, opposing_pitcher_hand=None):
    stats = _scrape_team_stats()
    wrc_proxy = 100
    if stats and team_name in stats:
        wrc_proxy = stats[team_name]['wrc_plus_proxy']
        
    vs_R = wrc_proxy
    vs_L = wrc_proxy
    
    if opposing_pitcher_hand == 'L':
        vs_L = round(wrc_proxy * 0.97, 1) # Standard 3% penalty against lefties
    elif opposing_pitcher_hand == 'R':
        vs_R = round(wrc_proxy * 1.01, 1) # Slight boost against righties
        
    return {
        'wrc_plus': wrc_proxy,
        'vs_R': vs_R,
        'vs_L': vs_L
    }

def get_team_bullpen_fip(team_name):
    stats = _scrape_team_stats()
    if stats and team_name in stats:
        return stats[team_name]['era']
    return 3.15

def get_team_f5_form_factor(team_name):
    form_data = _scrape_form_factors()
    if form_data and team_name in form_data:
        return form_data[team_name]
    return {'factor': 1.0, 'raw_avg': 1.8, 'games_used': 10, 'games_raw': []}

def get_weather_multiplier(venue_name):
    """
    Returns the calculated temperature multiplier for open-air NPB stadiums.
    Returns 1.0 for domes or if the API fails.
    """
    coords = None
    for key_venue, latlon in NPB_WEATHER_COORDS.items():
        if key_venue in venue_name:
            coords = latlon
            break
            
    if not coords:
        return 1.0 # Domed stadium or unknown
        
    lat, lon = coords
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&temperature_unit=fahrenheit"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        temp = data.get('current', {}).get('temperature_2m')
        
        if temp is not None:
            # Standard MLB temperature scalar: +0.3% runs per degree above 72F
            multiplier = 1.0 + ((temp - 72) * 0.003)
            # Clamp extreme outliers
            return round(min(max(multiplier, 0.85), 1.15), 3)
    except Exception as e:
        print(f"Error fetching weather for {venue_name}: {e}")
        
    return 1.0

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    games = get_today_games()
    print(f"Found {len(games)} NPB games today.")
    for g in games:
        print(f"--- {g['away_team']} vs {g['home_team']} @ {g['venue_name']} (PF: {g['park_factor']}) ---")
        ap_stats = get_pitcher_stats(g['away_pitcher'], g.get('away_pitcher_url'))
        hp_stats = get_pitcher_stats(g['home_pitcher'], g.get('home_pitcher_url'))
        
        away_team_data = get_team_stats(g['away_team'], opposing_pitcher_hand=hp_stats['hand'])
        home_team_data = get_team_stats(g['home_team'], opposing_pitcher_hand=ap_stats['hand'])
        away_bp = get_team_bullpen_fip(g['away_team'])
        home_bp = get_team_bullpen_fip(g['home_team'])
        
        away_form = get_team_f5_form_factor(g['away_team'])
        home_form = get_team_f5_form_factor(g['home_team'])
        
        print(f"Away Pitcher ({g['away_pitcher']}, Hand: {ap_stats['hand']}) FIP: {ap_stats['fip']}")
        print(f"Home Pitcher ({g['home_pitcher']}, Hand: {hp_stats['hand']}) FIP: {hp_stats['fip']}")
        print(f"{g['away_team']} wRC+ vs L: {away_team_data['vs_L']}, vs R: {away_team_data['vs_R']}")
        print(f"{g['home_team']} wRC+ vs L: {home_team_data['vs_L']}, vs R: {home_team_data['vs_R']}")
        print(f"{g['away_team']} Form Factor: {away_form['factor']} (Raw Avg: {away_form['raw_avg']} runs)")
        print(f"{g['home_team']} Form Factor: {home_form['factor']} (Raw Avg: {home_form['raw_avg']} runs)")
