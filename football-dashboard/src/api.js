/**
 * api.js — Production: fetches data/football JSON straight from GitHub raw CDN.
 * Dev: proxied locally via vite.config.js → localhost:8080
 */

const isDev = import.meta.env.DEV

// In dev, use the local FastAPI proxy; in prod, fetch from GitHub raw
const RAW  = 'https://raw.githubusercontent.com/kadafs/NCAA/master'
const DATA = `${RAW}/data/football`
const API  = '/api'   // vite proxy → localhost:8080 in dev

export async function fetchDates() {
  if (isDev) {
    const r = await fetch(`${API}/dates`)
    if (!r.ok) throw new Error('Failed to fetch dates')
    const d = await r.json()
    return d.dates
  }
  // Production: read the pre-generated index file committed to the repo
  const r = await fetch(`${DATA}/dates_index.json`, { cache: 'no-store' })
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
  // Production: fetch the daily JSON directly
  const r = await fetch(`${DATA}/universal_predictions_${date}.json`, { cache: 'no-store' })
  if (!r.ok) throw new Error(`No predictions for ${date}`)
  return r.json()
}
