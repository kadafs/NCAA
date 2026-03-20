"""
api/server.py
FastAPI backend — serves prediction JSON files as API endpoints.
"""
import os, json, glob
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Multi-Sport Predictions API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _get_path(sport: str, date: str) -> str:
    return os.path.join(DATA_DIR, sport, f"universal_predictions_{date}.json")


@app.get("/api/football")
def get_football(date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    path = _get_path("football", date)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No football predictions for {date}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/basketball")
def get_basketball(date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    path = _get_path("basketball", date)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No basketball predictions for {date}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/leaderboard")
def get_leaderboard(sport: str = "football"):
    path = os.path.join(DATA_DIR, sport, "league_leaderboard.json")
    if not os.path.exists(path):
        return {"leaderboard": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/dates")
def get_dates(sport: str = "football"):
    """Return sorted list of dates that have prediction files for the target sport."""
    pattern = os.path.join(DATA_DIR, sport, "universal_predictions_*.json")
    files   = glob.glob(pattern)
    result  = []
    for f in sorted(files, reverse=True):
        date = (os.path.basename(f)
                .replace("universal_predictions_", "")
                .replace(".json", ""))
        try:
            with open(f, encoding="utf-8") as fh:
                payload = json.load(fh)
            
            # Football uses btts_graded or grade_summary
            # Basketball might just have grade_summary or we check actual_result presence
            graded = payload.get("grade_summary") is not None
            scored_count = sum(
                1 for p in payload.get("predictions", [])
                if p.get("actual_result") is not None or p.get("actual_total_result") is not None
            )
            
            result.append({
                "date":         date,
                "total":        payload.get("total_predictions", 0),
                "graded":       graded or (scored_count > 0),
                "graded_count": scored_count,
                "grade_summary": payload.get("grade_summary"),
            })
        except Exception as e:
            print(f"Error parsing {f}: {e}")
            continue

    return {"dates": result}
