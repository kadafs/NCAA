/**
 * api.js
 * Dev:  proxied via Vite → localhost:8080 (FastAPI)
 * Prod: static JSON files bundled in Vercel at /data/football/
 */

const isDev = import.meta.env.DEV
const API   = '/api'
const DATA  = '/data'

export async function fetchDates(sport = 'football') {
  if (isDev) {
    const r = await fetch(`${API}/dates?sport=${sport}`)
    if (!r.ok) throw new Error(`Failed to fetch ${sport} dates`)
    const d = await r.json()
    return d.dates
  }
  const r = await fetch(`${DATA}/${sport}/dates_index.json?t=${Date.now()}`)
  if (!r.ok) throw new Error(`Failed to fetch ${sport} dates index`)
  const d = await r.json()
  return d.dates
}

export async function fetchPredictions(date, sport = 'football') {
  if (isDev) {
    const r = await fetch(`${API}/${sport}?date=${date}`)
    if (!r.ok) throw new Error(`No ${sport} predictions for ${date}`)
    return r.json()
  }
  const r = await fetch(`${DATA}/${sport}/universal_predictions_${date}.json?t=${Date.now()}`)
  if (!r.ok) throw new Error(`No ${sport} predictions for ${date}`)
  return r.json()
}

export async function fetchLeaderboard(sport = 'football') {
  if (isDev) {
    const r = await fetch(`${API}/leaderboard?sport=${sport}`)
    if (!r.ok) return []
    const d = await r.json()
    return d.leaderboard || []
  }
  const r = await fetch(`${DATA}/${sport}/league_leaderboard.json?t=${Date.now()}`)
  if (!r.ok) return []
  const d = await r.json()
  return d.leaderboard || []
}
