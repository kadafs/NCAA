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

export async function fetchTeamLeaderboard(sport = 'football') {
  if (sport === 'football') return [] // Football does not have team tracking yet
  
  if (isDev) {
    // Falls back to static fetch if dev API isn't built out for teams yet
    try {
      const r = await fetch(`${API}/team_leaderboard?sport=${sport}`)
      if (r.ok) {
        const d = await r.json()
        return d.leaderboard || []
      }
    } catch (e) {}
  }
  
  // Direct static fetch from the generated file we just created
  const r = await fetch(`${DATA}/${sport}/basketball_leaderboard.json?t=${Date.now()}`)
  if (!r.ok) return []
  const d = await r.json()
  return d.leaderboard || []
}
