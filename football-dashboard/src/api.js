/**
 * api.js
 * Dev:  proxied via Vite → localhost:8080 (FastAPI)
 * Prod: static JSON files bundled in Vercel at /data/football/
 */

const isDev = import.meta.env.DEV
const API   = '/api'          // vite proxy in dev
const DATA  = '/data/football' // static public/ files in prod

export async function fetchDates() {
  if (isDev) {
    const r = await fetch(`${API}/dates`)
    if (!r.ok) throw new Error('Failed to fetch dates')
    const d = await r.json()
    return d.dates
  }
  const r = await fetch(`${DATA}/dates_index.json?t=${Date.now()}`)
  if (!r.ok) throw new Error('Failed to fetch dates index')
  const d = await r.json()
  return d.dates   // [{ date, total, graded, graded_count, grade_summary }]
}

export async function fetchFootball(date) {
  if (isDev) {
    const r = await fetch(`${API}/football?date=${date}`)
    if (!r.ok) throw new Error(`No predictions for ${date}`)
    return r.json()
  }
  const r = await fetch(`${DATA}/universal_predictions_${date}.json?t=${Date.now()}`)
  if (!r.ok) throw new Error(`No predictions for ${date}`)
  return r.json()
}
