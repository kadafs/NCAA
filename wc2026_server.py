"""
wc2026_server.py
================
Local dashboard server for the FIFA World Cup 2026 Prediction Dashboard.
Serves live data from run_wc2026.py at localhost:8000.

Usage:
    python wc2026_server.py           # starts server + opens browser
    python wc2026_server.py --port 8080
    python wc2026_server.py --no-browser
"""

import sys, os, json, importlib.util, threading, webbrowser, argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent / "wc2026_frontend"
WC_PATH      = Path(__file__).parent / "run_wc2026.py"


def load_wc_module():
    spec = importlib.util.spec_from_file_location("run_wc2026", WC_PATH)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_api_data():
    """Fresh predictions + standings on every request so results auto-update."""
    mod   = load_wc_module()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Compute tournament-adjusted Elo from actual results
    live_elo     = mod.compute_dynamic_elo()
    games_played = sum(1 for (h, a, *_) in mod.WC2026_FIXTURES if (h, a) in mod.ACTUAL_RESULTS)

    preds = [
        mod.predict(h, a, grp, dt, venue, md, live_elo=live_elo)
        for (h, a, dt, venue, grp, md) in mod.WC2026_FIXTURES
    ]

    standings = {g: mod.simulate_standings(g, preds) for g in mod.WC2026_GROUPS}

    btts_picks  = sorted([p for p in preds if "PLAY YES" in p["btts_decision"]],
                          key=lambda x: -x["btts_prob"])
    draw_picks  = sorted([p for p in preds if p["draw_value_flag"] and not p["is_completed"]],
                          key=lambda x: -x["draw_prob"])
    today_games = [p for p in preds if p["date"] == today]

    completed = sum(1 for p in preds if p["is_completed"])

    # Elo delta table — unpacks 7-tuple: (team, base, live, live_delta, conf, eff, conf_adj)
    elo_deltas = [
        {
            "team":      t,
            "base":      b,
            "live":      lv,
            "delta":     d,
            "conf":      conf,
            "effective": eff,
            "conf_adj":  cadj,
        }
        for (t, b, lv, d, conf, eff, cadj) in mod.elo_delta_report(live_elo)
    ]

    return {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "today":         today,
        "groups":        mod.WC2026_GROUPS,
        "predictions":   preds,
        "standings":     standings,
        "btts_picks":    btts_picks,
        "draw_picks":    draw_picks,
        "today_games":   today_games,
        "elo_deltas":    elo_deltas,
        "elo_games_in":  games_played,
        "stats": {
            "total":      len(preds),
            "completed":  completed,
            "upcoming":   len(preds) - completed,
            "btts_picks": len(btts_picks),
            "draw_picks": len(draw_picks),
            "today":      len(today_games),
        },
    }



class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {self.command} {self.path}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self.serve_file(FRONTEND_DIR / "index.html", "text/html")
        elif path == "/api/data":
            try:
                self.serve_json(build_api_data())
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")

    def serve_file(self, fpath, ctype):
        try:
            data = fpath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404, f"File not found: {fpath.name}")

    def serve_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    ap = argparse.ArgumentParser(description="WC2026 Dashboard Server")
    ap.add_argument("--port",       type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if not FRONTEND_DIR.exists():
        print(f"  ❌ Frontend not found: {FRONTEND_DIR}")
        print(f"     Run this script from the ncaa-api directory.")
        sys.exit(1)

    server  = HTTPServer(("localhost", args.port), DashboardHandler)
    url     = f"http://localhost:{args.port}"

    print()
    print("  FIFA WORLD CUP 2026 - Prediction Dashboard")
    print("  " + "-" * 44)
    print(f"  Dashboard : {url}")
    print(f"  Live data : {url}/api/data")
    print("  Auto-refresh every 30s  |  Ctrl+C to stop")
    print()

    if not args.no_browser:
        threading.Timer(0.9, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.\n")


if __name__ == "__main__":
    main()
