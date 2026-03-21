import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Navigate from football-dashboard/api/ → football-dashboard/ → repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR  = os.path.join(REPO_ROOT, 'data', 'basketball')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        date   = params.get('date', [datetime.now().strftime('%Y-%m-%d')])[0]

        path = os.path.join(DATA_DIR, f'universal_predictions_{date}.json')
        if not os.path.exists(path):
            msg = json.dumps({'error': f'No basketball predictions for {date}'}).encode()
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(msg)
            return

        with open(path, encoding='utf-8') as f:
            body = f.read().encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # silence access logs
