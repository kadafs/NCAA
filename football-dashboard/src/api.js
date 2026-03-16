const BASE = '/api'

export async function fetchDates() {
  const r = await fetch(`${BASE}/dates`)
  if (!r.ok) throw new Error('Failed to fetch dates')
  const d = await r.json()
  return d.dates   // string[]
}

export async function fetchFootball(date) {
  const r = await fetch(`${BASE}/football?date=${date}`)
  if (!r.ok) throw new Error(`No predictions for ${date}`)
  return r.json()  // { date, predictions: [] }
}
