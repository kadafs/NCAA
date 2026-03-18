"""
api/server.py
FastAPI backend — serves prediction JSON files as API endpoints.
"""
import os, json, glob
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Football Predictions API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _football_path(date: str) -> str:
    return os.path.join(DATA_DIR, "football", f"universal_predictions_{date}.json")


@app.get("/api/football")
def get_football(date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    path = _football_path(date)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No predictions for {date}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/leaderboard")
def get_leaderboard():
    path = os.path.join(DATA_DIR, "football", "league_leaderboard.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No leaderboard found")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/dates")
def get_dates():
    """Return sorted list of dates that have football prediction files,
    with a graded flag so the frontend can show the scorecard tab."""
    pattern = os.path.join(DATA_DIR, "football", "universal_predictions_*.json")
    files   = glob.glob(pattern)
    result  = []
    for f in sorted(files, reverse=True):
        date = (os.path.basename(f)
                .replace("universal_predictions_", "")
                .replace(".json", ""))
        with open(f, encoding="utf-8") as fh:
            payload = json.load(fh)
        graded = payload.get("grade_summary") is not None
        scored_count = sum(
            1 for p in payload.get("predictions", [])
            if p.get("actual_result") is not None
        )
        result.append({
            "date":         date,
            "total":        payload.get("total_predictions", 0),
            "graded":       graded,
            "graded_count": scored_count,
            "grade_summary": payload.get("grade_summary"),
        })
    return {"dates": result}
