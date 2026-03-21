import json
import os
from http.server import BaseHTTPRequestHandler

from urllib.parse import urlparse, parse_qs

# Navigate from football-dashboard/api/ → football-dashboard/ → repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        sport  = params.get('sport', ['football'])[0]
        
        data_dir = os.path.join(REPO_ROOT, 'data', sport)
        path = os.path.join(data_dir, 'league_leaderboard.json')
        
        if not os.path.exists(path):
            msg = json.dumps({'error': f'No {sport} leaderboard found'}).encode()
            self.send_response(404)
        else:
            with open(path, encoding='utf-8') as f:
                msg = f.read().encode('utf-8')
            self.send_response(200)

        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    def log_message(self, *args):
        pass  # silence access logs
