import json
import os
import glob
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
        pattern = os.path.join(data_dir, 'universal_predictions_*.json')
        files   = sorted(glob.glob(pattern), reverse=True)
        result  = []
        for f in files:
            date = (os.path.basename(f)
                    .replace('universal_predictions_', '')
                    .replace('.json', ''))
            try:
                with open(f, encoding='utf-8') as fh:
                    payload = json.load(fh)
            except Exception:
                continue
            graded = payload.get('grade_summary') is not None
            scored_count = sum(
                1 for p in payload.get('predictions', [])
                if p.get('actual_result') is not None
            )
            result.append({
                'date':          date,
                'total':         payload.get('total_predictions', 0),
                'graded':        graded,
                'graded_count':  scored_count,
                'grade_summary': payload.get('grade_summary'),
            })

        body = json.dumps({'dates': result}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # silence access logs
